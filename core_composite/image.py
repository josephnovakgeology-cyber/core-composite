# -*- coding: utf-8 -*-
"""
Created on Mon May  4 13:33:52 2026

@author: joseph novak 

CorePhotoDigitizer and supporting functions
"""

import os
import re
import pymupdf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector, RadioButtons, Button
from matplotlib.patches import Rectangle
from skimage import io, transform, color
from scipy.ndimage import maximum_filter1d, minimum_filter1d
from scipy.signal import savgol_filter
import warnings
from scipy.interpolate import interp1d
import glob
import textwrap
from pathlib import Path
import sys
import colour

class CorePhotoDigitizer:
    """
    CorePhotoDigitizer and the trailing supporting functions facilitiate extraction of L*, a*, and b* values from 
    DSDP/ODP/IODP core photos. These scripts require section summaries to map the extracted pixel-level data to 
    depth mbsf. 
    """
    def __init__(self, image_path, section_summary_csv, leg, site, hole, core, core_type, disp_downscale_factor = 0.5, 
                 target_white_L=95.0, target_black_L=20.0, section=None, show_diagnostics=False):
        self.image_path = image_path
        self.summary_csv = section_summary_csv
        self.leg = leg
        self.site = site
        self.hole = hole
        self.core = core
        self.core_type = core_type
        self.section = section
        
        self.show_diagnostics = show_diagnostics
        
        self.rectangles = []
        self.saved_coords = []
        
        self.void_rectangles = []
        self.saved_void_coords = []
        
        # Color checker calibration defaults (1.0 slope, 0.0 offset = no change)
        self.calib_m_L = 1.0
        self.calib_c_L = 0.0
        self.calib_c_a = 0.0
        self.calib_c_b = 0.0
        
        # Background calibration defaults
        self.bg_curve_white = None
        self.bg_curve_black = None
        
        self.target_white_L = target_white_L
        self.target_black_L = target_black_L
        
        self.bg_coords = None
        
        # Need to include these because python is an angry god
        self.disp_downscale_factor = disp_downscale_factor
        self.scale_multiplier = int(1 / disp_downscale_factor)
        
    def _run_gui(self):
        print(f"Loading {self.image_path} for interactive processing...")
    
        self.raw_image = io.imread(self.image_path)
        # Downscale for display purposes so it fits on normal monitors
        self.display_image = transform.rescale(self.raw_image, self.disp_downscale_factor, channel_axis=-1, anti_aliasing=True)
    
        self.fig, self.ax = plt.subplots(figsize=(14, 8))
        self.ax.imshow(self.display_image)
    
        # Compress core photo area to leave margin on right side
        plt.subplots_adjust(left=0.08, right=0.68) 
    
        # Render section summary table on the right
        self._display_section_summary()

        # Start the background lighting correction
        self._start_background_calibration()
    
        # Halt the script and wait for the user to draw boxes
        plt.show(block=True)
        
    def _start_background_calibration(self):
        plt.subplots_adjust(left=0.1)
        self.ax.set_title(
            "BACKGROUND 1: VERTICAL\n"
            "1. Draw one box down the center white track.\n"
            "2. Make sure the box goes past the core sections.\n"
            "3. Press 'Enter' when done.",
            fontsize=12, fontweight='bold', color='blue'
        )
        self.fig.canvas.draw()

        self.temp_bg_coords = None
        self.bg_coords_y = None
        self.bg_coords_x = None
        self.bg_step = 1

        def on_bg_select(eclick, erelease):
            x1, y1 = int(min(eclick.xdata, erelease.xdata)), int(min(eclick.ydata, erelease.ydata))
            x2, y2 = int(max(eclick.xdata, erelease.xdata)), int(max(eclick.ydata, erelease.ydata))
            self.temp_bg_coords = (x1*self.scale_multiplier, y1*self.scale_multiplier, x2*self.scale_multiplier, y2*self.scale_multiplier)

        self.bg_selector = RectangleSelector(
            self.ax, on_bg_select, useblit=True, button=[1],
            minspanx=5, minspany=5, interactive=True
        )

        def on_bg_enter(event):
            if event.key == 'enter' and self.temp_bg_coords:
                
                if self.bg_step == 1:
                    # Save the vertical box
                    self.bg_coords_y = self.temp_bg_coords
                    self.temp_bg_coords = None
                    self.bg_step = 2
                    
                    # Update instructions for the horizontal box
                    self.ax.set_title(
                        "BACKGROUND 2: HORIZONTAL\n"
                        "1. Draw one horizontal box across all cores and tracks.\n"
                        "2. Press 'Enter' when done.",
                        fontsize=12, fontweight='bold', color='red'
                    )
                    self.fig.canvas.draw()
                    
                elif self.bg_step == 2:
                    # Save the horizontal box and process
                    self.bg_coords_x = self.temp_bg_coords
                    self.fig.canvas.mpl_disconnect(self.bg_cid)
                    self.bg_selector.set_active(False)
                    
                    self.bg_selector.set_visible(False)
                    self.bg_selector.clear()
                    self.fig.canvas.draw()
                    
                    self._process_background_curves()

        # User needs to hit the enter key
        self.bg_cid = self.fig.canvas.mpl_connect('key_press_event', on_bg_enter)

        
    def _process_background_curves(self):
        print("Calculating the lighting corrections...")

        # Vertical background
        x1_y, y1_y, x2_y, y2_y = self.bg_coords_y
        bg_crop_y = self.raw_image[y1_y:y2_y, x1_y:x2_y]
        if bg_crop_y.shape[-1] == 4: bg_crop_y = bg_crop_y[:, :, :3]
        
        lab_bg = color.rgb2lab(bg_crop_y)
        L_channel_y = lab_bg[:, :, 0]
        a_channel_y = lab_bg[:, :, 1]
        b_channel_y = lab_bg[:, :, 2]
        
        raw_white_y = np.percentile(L_channel_y, 95, axis=1)
        raw_black_y = np.percentile(L_channel_y, 5, axis=1)
        raw_a_y = np.median(a_channel_y, axis=1)
        raw_b_y = np.median(b_channel_y, axis=1)
        
        connected_white_y = maximum_filter1d(raw_white_y, size=300) 
        connected_black_y = minimum_filter1d(raw_black_y, size=300) 
        
        smoothed_white_y = savgol_filter(connected_white_y, window_length=301, polyorder=3)
        smoothed_black_y = savgol_filter(connected_black_y, window_length=301, polyorder=3)
        smoothed_a_y = savgol_filter(raw_a_y, window_length=301, polyorder=3)
        smoothed_b_y = savgol_filter(raw_b_y, window_length=301, polyorder=3)
        
        y_coords_box = np.arange(y1_y, y2_y)
        y_coords_full = np.arange(self.raw_image.shape[0])
        
        self.bg_curve_white = np.interp(y_coords_full, y_coords_box, smoothed_white_y)
        self.bg_curve_black = np.interp(y_coords_full, y_coords_box, smoothed_black_y)
        self.bg_curve_a = np.interp(y_coords_full, y_coords_box, smoothed_a_y)
        self.bg_curve_b = np.interp(y_coords_full, y_coords_box, smoothed_b_y)
        
        center_y = len(y_coords_full) // 2
        baseline_a = self.bg_curve_a[center_y]
        baseline_b = self.bg_curve_b[center_y]
        
        self.color_shift_a = self.bg_curve_a - baseline_a
        self.color_shift_b = self.bg_curve_b - baseline_b
        
        self.bg_ref_x = int((x1_y + x2_y) / 2)

        # Horizontal background
        x1_x, y1_x, x2_x, y2_x = self.bg_coords_x
        bg_crop_x = self.raw_image[y1_x:y2_x, x1_x:x2_x]
        if bg_crop_x.shape[-1] == 4: bg_crop_x = bg_crop_x[:, :, :3]
        
        L_channel_x = color.rgb2lab(bg_crop_x)[:, :, 0]
        
        raw_white_x = np.percentile(L_channel_x, 95, axis=0)
        connected_white_x = maximum_filter1d(raw_white_x, size=1500) 
        
        window_size = min(1501, len(connected_white_x))
        if window_size % 2 == 0: window_size -= 1
        if window_size >= 5:
            smoothed_white_x = savgol_filter(connected_white_x, window_length=window_size, polyorder=3)
        else:
            smoothed_white_x = connected_white_x
            
        x_coords_box = np.arange(x1_x, x2_x)
        x_coords_full = np.arange(self.raw_image.shape[1])
        
        self.bg_curve_white_x = np.interp(x_coords_full, x_coords_box, smoothed_white_x)

        print("Background lighting and color artifacts modelled")
        
        if self.show_diagnostics:
            fig_bg_v, ax_bg_v = plt.subplots(figsize=(8, 5))
            ax_bg_v.set_title("Diagnostic: Vertical Lighting Artifacts", fontweight='bold')
            ax_bg_v.plot(y_coords_full, self.bg_curve_white, color='orange', linewidth=2, label='White Tracking Curve (95th %)')
            ax_bg_v.plot(y_coords_full, self.bg_curve_black, color='blue', linewidth=2, label='Black Shadow Curve (5th %)')
            ax_bg_v.set_xlabel("Pixel Row (Top of Image -> Bottom of Image)")
            ax_bg_v.set_ylabel("Lightness (L*)")
            ax_bg_v.invert_xaxis() 
            ax_bg_v.legend()
            fig_bg_v.tight_layout()
            
            fig_color, ax_color = plt.subplots(figsize=(8, 5))
            ax_color.set_title("Diagnostic Plot: Vertical Color Shift", fontweight='bold')
            ax_color.plot(y_coords_full, self.color_shift_a, color='red', linewidth=2, label='a* (Red/Green) Shift')
            ax_color.plot(y_coords_full, self.color_shift_b, color='gold', linewidth=2, label='b* (Yellow/Blue) Shift')
            ax_color.axhline(0, color='black', linestyle='--', linewidth=1)
            ax_color.set_xlabel("Pixel Row")
            ax_color.set_ylabel("Shift Magnitude")
            ax_color.invert_xaxis() 
            ax_color.legend()
            fig_color.tight_layout()
            
            fig_bg_h, ax_bg_h = plt.subplots(figsize=(8, 5))
            ax_bg_h.set_title("Diagnostic Plot: Horizontal Room Lighting", fontweight='bold')
            ax_bg_h.plot(x_coords_full, self.bg_curve_white_x, color='green', linewidth=3, label='Macro Horizontal Light Surface')
            ax_bg_h.set_xlabel("Pixel Column (Left Edge -> Right Edge of Image)")
            ax_bg_h.set_ylabel("Lightness (L*)")
            ax_bg_h.legend()
            fig_bg_h.tight_layout()
        
        self._start_calibration_checkpoint_gui()
        
    def _start_calibration_checkpoint_gui(self):
        plt.subplots_adjust(left=0.3) 
        self.ax.set_title("Step 3: (Optional) Color Checker Correction", fontsize=14, fontweight='bold')
        self.fig.canvas.draw()
        
        self.ax_anch = plt.axes([0.05, 0.6, 0.2, 0.15], facecolor='lightgray')
        self.radio_anchor = RadioButtons(self.ax_anch, (
            'Skip (Use Model Basis)', 
            'Use Color Checker (Black & White)'
        ))
        
        self.ax_anch_proceed = plt.axes([0.05, 0.5, 0.2, 0.05])
        self.btn_anch_proceed = Button(self.ax_anch_proceed, 'Confirm', color='lightblue', hovercolor='0.975')
        
        self.anchoring_choice = 'Skip (Use Model Basis)'
        
        def anchorfunc(label):
            self.anchoring_choice = label
            
        self.radio_anchor.on_clicked(anchorfunc)
        
        def anchor_proceed_clicked(event):
            self.ax_anch.set_visible(False)
            self.ax_anch_proceed.set_visible(False)
            
            if self.anchoring_choice == 'Skip (Use Model Basis)':
                print("\nAnchoring skipped. Digital values will be basis-scaled (White Liner=95 L*)...")
                self.calib_m_L = 1.0
                self.calib_c_L = 0.0
                self.calib_c_a = 0.0
                self.calib_c_b = 0.0
                self._start_cropping_phase()
                
            elif self.anchoring_choice == 'Use Color Checker (Black & White)':
                self._start_2point_anchor_calibration()
                
        self.btn_anch_proceed.on_clicked(anchor_proceed_clicked)
        self.fig.canvas.draw()
        
    def _start_2point_anchor_calibration(self):
        self.calib_pts = []
        self.ax.set_title(
            "Color Checker: Click Two Squares\n"
            "1. Click the absolute White square.\n"
            "2. Click the absolute Black square.\n",
            fontsize=12, fontweight='bold', color='green'
        )
        self.fig.canvas.draw()
        self.calib_cid = self.fig.canvas.mpl_connect('button_press_event', self._on_calib_click)

    def _on_calib_click(self, event):
        if not event.inaxes == self.ax: return
        self.calib_pts.append((event.xdata, event.ydata))
        
        colors = ['green', 'red']
        current_idx = len(self.calib_pts) - 1
        self.ax.plot(event.xdata, event.ydata, marker='+', color=colors[current_idx], markersize=12, markeredgewidth=2)
        self.fig.canvas.draw()

        if len(self.calib_pts) == 2:
            self.fig.canvas.mpl_disconnect(self.calib_cid)
            self._calculate_2point_anchor_math()

    def _calculate_2point_anchor_math(self):
        try:
            print("\nCalculating Color Checker-Based Correction...", flush=True)
            w_x_disp, w_y_disp = int(self.calib_pts[0][0]), int(self.calib_pts[0][1])
            b_x_disp, b_y_disp = int(self.calib_pts[1][0]), int(self.calib_pts[1][1])
            
            w_x, w_y = w_x_disp*self.scale_multiplier, w_y_disp*self.scale_multiplier
            b_x, b_y = b_x_disp*self.scale_multiplier, b_y_disp*self.scale_multiplier
            H, W = self.raw_image.shape[:2]
            w_x, w_y = np.clip(w_x, 1, W-2), np.clip(w_y, 1, H-2)
            b_x, b_y = np.clip(b_x, 1, W-2), np.clip(b_y, 1, H-2)
            
            w_patch = self.raw_image[w_y-1:w_y+2, w_x-1:w_x+2]
            b_patch = self.raw_image[b_y-1:b_y+2, b_x-1:b_x+2]
            
            if w_patch.shape[-1] == 4: w_patch = w_patch[:, :, :3]
            if b_patch.shape[-1] == 4: b_patch = b_patch[:, :, :3]
            w_lab = color.rgb2lab(w_patch); b_lab = color.rgb2lab(b_patch)
            
            meas_w_L = np.mean(w_lab[:, :, 0]); meas_w_a = np.mean(w_lab[:, :, 1]); meas_w_b = np.mean(w_lab[:, :, 2])
            meas_b_L = np.mean(b_lab[:, :, 0])
            
            if hasattr(self, 'bg_curve_white') and self.bg_curve_white is not None:
                y_shadow_w = self.bg_curve_white[w_y]
                y_shadow_b = self.bg_curve_white[b_y]
                
                meas_w_L_flattened = meas_w_L + (self.target_white_L - y_shadow_w)
                meas_b_L_flattened = meas_b_L + (self.target_white_L - y_shadow_b)
                
                if hasattr(self, 'bg_curve_white_x') and self.bg_curve_white_x is not None:
                    macro_x_shadow_w = self.bg_curve_white_x[w_x] - self.bg_curve_white_x[self.bg_ref_x]
                    macro_x_shadow_b = self.bg_curve_white_x[b_x] - self.bg_curve_white_x[self.bg_ref_x]
                    
                    meas_w_L_flattened -= macro_x_shadow_w
                    meas_b_L_flattened -= macro_x_shadow_b
                
                meas_w_L = meas_w_L_flattened
                meas_b_L = meas_b_L_flattened
            
            true_w_L, true_b_L = self.target_white_L, self.target_black_L
            
            if meas_w_L != meas_b_L: 
                self.calib_m_L = (true_w_L - true_b_L) / (meas_w_L - meas_b_L)
                self.calib_c_L = true_w_L - (self.calib_m_L * meas_w_L)
            
            self.calib_c_a = 0.0 - meas_w_a
            self.calib_c_b = 0.0 - meas_w_b
            
            print(f" Best-Fit L* Slope: {self.calib_m_L:.2f}, Offset: {self.calib_c_L:.2f}", flush=True)
            self._start_cropping_phase()
            
        except Exception as e:
            print(f"!!YIKES!! Critical Error in Color Checker calculation: {e}\n", flush=True)
            self.calib_m_L, self.calib_c_L, self.calib_c_a, self.calib_c_b = 1.0, 0.0, 0.0, 0.0
            self._start_cropping_phase()

    def _start_cropping_phase(self):
        plt.subplots_adjust(left=0.1)
        
        self.ax.set_title(
            f"Digitizing {self.site}{self.hole}-{self.core}{self.core_type}\n"
            "1. Drag boxes over sediment.\n2. Press 'v' to convert last box to void. \n3. Use Arrow Keys to edit position of last box.\n4 Close window when done.", 
            fontsize=12, fontweight='bold', color='black'
        )
        self.fig.canvas.draw()
        
        self.selector = RectangleSelector(
            self.ax, self.on_select, useblit=True, button=[1],
            minspanx=5, minspany=5, spancoords='pixels', interactive=True
        )
        
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

    def on_select(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        
        rect = Rectangle((min(x1, x2), min(y1, y2)), np.abs(x1 - x2), np.abs(y1 - y2),
                         linewidth=3, edgecolor='magenta', facecolor='none')
        self.ax.add_patch(rect)
        self.rectangles.append(rect)
        
        self.saved_coords.append({
            'x1': int(min(x1, x2) * self.scale_multiplier),
            'y1': int(min(y1, y2) * self.scale_multiplier),
            'x2': int(max(x1, x2) * self.scale_multiplier),
            'y2': int(max(y1, y2) * self.scale_multiplier)
        })
        self.fig.canvas.draw()

    def on_key(self, event):
        if not self.rectangles and not self.void_rectangles: 
            return 

        if event.key == 'd':
            # Delete the most recently added box
            if self.void_rectangles:
                rect = self.void_rectangles.pop()
                rect.remove()
                if self.saved_void_coords:
                    self.saved_void_coords.pop()
            elif self.rectangles:
                rect = self.rectangles.pop()
                rect.remove()
                if self.saved_coords:
                    self.saved_coords.pop()

            self.fig.canvas.draw()

        elif event.key == 'v':
            if self.rectangles:
                rect = self.rectangles.pop()
                coords = self.saved_coords.pop()
                rect.set_edgecolor('yellow')
                rect.set_linestyle('--')
                self.void_rectangles.append(rect)
                self.saved_void_coords.append(coords)
                self.fig.canvas.draw()

        elif event.key in ['up', 'down', 'left', 'right']:
            if self.rectangles:
                rect = self.rectangles[-1]
                coords = self.saved_coords[-1]
            elif self.void_rectangles:
                rect = self.void_rectangles[-1]
                coords = self.saved_void_coords[-1]
            else:
                return

            x, y = rect.get_xy()
            if event.key == 'up':
                rect.set_y(y - 1); coords['y1'] -= self.scale_multiplier; coords['y2'] -= self.scale_multiplier
            elif event.key == 'down':
                rect.set_y(y + 1); coords['y1'] += self.scale_multiplier; coords['y2'] += self.scale_multiplier
            elif event.key == 'left':
                rect.set_x(x - 1); coords['x1'] -= self.scale_multiplier; coords['x2'] -= self.scale_multiplier
            elif event.key == 'right':
                rect.set_x(x + 1); coords['x1'] += self.scale_multiplier; coords['x2'] += self.scale_multiplier
            self.fig.canvas.draw()

    def process_and_export(self, output_filename):
        self._run_gui()
        
        if not self.saved_coords:
            print("No boxes drawn. Exiting...")
            return None
            
        sorted_coords = sorted(self.saved_coords, key=lambda box: box['x1'])
        
        print(" Loading section metadata and extracting data...")
        summary_df = pd.read_csv(self.summary_csv, sep=None, engine='python')
        summary_df.columns = summary_df.columns.str.strip()
        
        col_site = 'Site'
        col_hole = 'Hole' if 'Hole' in summary_df.columns else 'H'
        col_core = 'Core' if 'Core' in summary_df.columns else 'Cor'
        self.col_sec = 'Sect' if 'Sect' in summary_df.columns else 'Sc' 
        
        if 'Top depth CSF-A (m)' in summary_df.columns:
            self.col_top = 'Top depth CSF-A (m)'
        elif 'Top(mbsf)' in summary_df.columns:
            self.col_top = 'Top(mbsf)'
        else:
            print("Error: Could not find a valid top depth column.")
            return None
            
        # Preference is for curated length, but will use liner length if that is not listed
        if 'CL(m)' in summary_df.columns:
            self.col_length = 'CL(m)'
        elif 'Curated length (m)' in summary_df.columns:
            self.col_length = 'Curated length (m)'
        elif 'LL(m)' in summary_df.columns:
            self.col_length = 'LL(m)'
        elif 'Length (m)' in summary_df.columns:
            self.col_length = 'Length (m)'
        else:
            print("Error: Could not find a valid length column.")
            return None
        
        csv_sites = summary_df[col_site].astype(str).str.replace('U', '', regex=False)
        target_site = str(self.site).replace('U', '')
        
        core_df = summary_df[
            (csv_sites == target_site) & 
            (summary_df[col_hole].astype(str) == str(self.hole)) & 
            (summary_df[col_core].astype(str) == str(self.core))
        ].copy()
        
        if self.section is not None:
            core_df = core_df[core_df[self.col_sec].astype(str).str.strip() == str(self.section)].copy()
            
        if core_df.empty:
            print(f"Error: Could not find metadata for Site {self.site}{self.hole} Core {self.core} Section {self.section}!")
            return None
            
        core_df['_sort_val'] = pd.to_numeric(core_df[self.col_top], errors='coerce')
        core_df = core_df.sort_values('_sort_val', na_position='last').drop(columns=['_sort_val']).reset_index(drop=True)
        
        all_data = []
        
        for i, box in enumerate(sorted_coords):
            if self.section is None:
                if i >= len(core_df): 
                    break 
                section_row = core_df.iloc[i]
            else:
                section_row = core_df.iloc[0]
                
            sec_name = str(section_row[self.col_sec]).strip()
            raw_top = str(section_row[self.col_top]).strip()
            raw_length = str(section_row[self.col_length]).strip()

            top_mbsf = float(raw_top) if raw_top else float('nan')
            length_m = float(raw_length) if raw_length else float('nan')

            if not raw_top or not raw_length:
                print(f"  Warning: Missing depth/length metadata for Section {sec_name}. Output depths will be NaN.")
            
            print(f"Processing Section {sec_name}...")
            
            y1_raw = box['y1']
            y2_raw = box['y2']
            
            if box['x1'] >= box['x2'] or y1_raw >= y2_raw:
                print(f"  Warning: Skipping invalid box for Section {sec_name}. (Accidental click?)")
                continue
                
            original_height = y2_raw - y1_raw
            
            # Use nominal slot span (1.5m) if length_m missing or standard full section slot
            span_m = length_m if (length_m and length_m > 0) else 1.5
            pixels_per_cm = original_height / (span_m * 100)
            
            trim_cm = 1.5 
            trim_px = int(pixels_per_cm * trim_cm)
            
            if span_m > 0.05:
                y1_trim = y1_raw + trim_px
                y2_trim = y2_raw - trim_px
            else:
                y1_trim = y1_raw
                y2_trim = y2_raw
                trim_px = 0
                
            cropped_rgb = self.raw_image[y1_trim:y2_trim, box['x1']:box['x2']]
            
            if cropped_rgb.shape[-1] == 4:
                cropped_rgb = cropped_rgb[:, :, :3]
            
            
            # Identify long series of saturated RGB values (0 or 255)
            is_saturated = (cropped_rgb <= 0) | (cropped_rgb >= 254)# 254 deals with rounding weirdness 
            
            # 63 pixels = 50 cm; is there is 50 cm span that is all saturated pixels?
            saturated_strings = minimum_filter1d(is_saturated.astype(int), size=63, axis=0)
            has_saturated_strings = np.any(saturated_strings == 1)

            # Convert RGB to CIELAB (L*, a*, b*)
            lab_core = color.rgb2lab(cropped_rgb)
            
            # Screen for L* values that are likely to indicate a* or b* data loss 
            is_dark = lab_core[:, :, 0] < 10
            
            # Is there a 50 cm span of all very dark pixels?
            dark_strings = minimum_filter1d(is_dark.astype(int), size=63, axis=0)
            has_dark_lstar = np.any(dark_strings == 1)
            
            if has_saturated_strings or has_dark_lstar:
                print(f"  *** WARNING: Section {sec_name} shows signs of color information loss: ***")
                if has_saturated_strings:
                    print("      -> Detected long series of saturated RGB values (0 or 255).")
                if has_dark_lstar:
                    print("      -> Detected very dark L* values (< 10).")
                    print('If your sediments are not super dark,')
                    print('You may have a large void you forgot to mask')
                    print('OR you accidently included the core liner in your drawn box.')
            
            
            # Apply void mask
            for v_box in self.saved_void_coords:
                y_overlap = max(y1_trim, v_box['y1']) < min(y2_trim, v_box['y2'])
                x_overlap = max(box['x1'], v_box['x1']) < min(box['x2'], v_box['x2'])
                
                if y_overlap and x_overlap:
                    vy1 = max(0, v_box['y1'] - y1_trim)
                    vy2 = min(y2_trim - y1_trim, v_box['y2'] - y1_trim)
                    
                    # Entire row goes to NaN
                    lab_core[vy1:vy2, :, :] = np.nan

            # Horizontal shadow profile model
            L_box = lab_core[:, :, 0]
            box_width = L_box.shape[1]
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                x_profile = np.nanmean(L_box, axis=0) 
            
            if np.isnan(x_profile).any():
                valid_mean = np.nanmean(x_profile)
                if np.isnan(valid_mean):
                    valid_mean = 50.0
                x_profile = pd.Series(x_profile).fillna(valid_mean).to_numpy()

            x_coords = np.arange(box_width)
            poly_coeffs = np.polyfit(x_coords, x_profile, 2)
            x_curve = np.polyval(poly_coeffs, x_coords)
            
            baseline_mean = np.mean(x_curve)
            lab_core[:, :, 0] = L_box - x_curve + baseline_mean
            lab_core[:, :, 0] = np.clip(lab_core[:, :, 0], 0, 100)
            
            # Compute line-by-line medians ignoring NaN void pixels
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                L_raw = np.nanpercentile(lab_core[:, :, 0], 50, axis=1) 
                a_raw = np.nanpercentile(lab_core[:, :, 1], 50, axis=1) 
                b_raw = np.nanpercentile(lab_core[:, :, 2], 50, axis=1)
            
            is_void_section = False
            
            if np.isnan(L_raw).all():
                is_void_section = True
            
            if not is_void_section:
                if self.show_diagnostics and i in [0, 1]:
                    print(f"Generating Horizontal Diagnostic Plot for Box {i+1}...")
                    fig_horiz, ax_horiz = plt.subplots(figsize=(8, 5))
                    ax_horiz.set_title(f"Diagnostic: Horizontal Shadows (Box {i+1})", fontweight='bold')
                    ax_horiz.plot(x_coords, x_profile, color='gray', alpha=0.7, label='Raw Horizontal Profile')
                    ax_horiz.plot(x_coords, x_curve, color='red', linewidth=3, label='Polynomial Lighting Model')
                    ax_horiz.set_xlabel("Pixel Column (Left Edge -> Right Edge of Box)")
                    ax_horiz.set_ylabel("Lightness (L*)")
                    ax_horiz.legend()
                    fig_horiz.tight_layout()
                
                if self.bg_curve_white is not None:
                    w_curve_slice = self.bg_curve_white[y1_trim:y2_trim].copy()
                    b_curve_slice = np.zeros_like(w_curve_slice)
                    
                    if hasattr(self, 'bg_curve_black') and self.bg_curve_black is not None:
                        b_curve_slice = self.bg_curve_black[y1_trim:y2_trim].copy()
                    
                    if hasattr(self, 'bg_curve_white_x') and self.bg_curve_white_x is not None:
                        box_center_x = int((box['x1'] + box['x2']) / 2)
                        macro_x_offset = self.bg_curve_white_x[box_center_x] - self.bg_curve_white_x[self.bg_ref_x]
                        w_curve_slice += macro_x_offset
                    
                    dynamic_range_local = w_curve_slice - b_curve_slice
                    dynamic_range_local[dynamic_range_local <= 0] = 1.0
                    
                    baseline_white = 95
                    baseline_black = 20
                    baseline_range = baseline_white - baseline_black
                    
                    L_raw = L_raw - b_curve_slice
                    ff_multiplier = baseline_range / dynamic_range_local
                    L_raw = (L_raw * ff_multiplier) + baseline_black
                    L_raw = np.clip(L_raw, 0, 100)
                    
                    if hasattr(self, 'color_shift_a') and hasattr(self, 'color_shift_b'):
                        a_shift_slice = self.color_shift_a[y1_trim:y2_trim]
                        b_shift_slice = self.color_shift_b[y1_trim:y2_trim]
                        a_raw = a_raw - a_shift_slice
                        b_raw = b_raw - b_shift_slice

                L_raw = (L_raw * self.calib_m_L) + self.calib_c_L
                a_raw = a_raw + self.calib_c_a
                b_raw = b_raw + self.calib_c_b
                
                L_raw = np.clip(L_raw, 0, 100)
                
                window_px = int(pixels_per_cm * 1.5) 
                if window_px % 2 == 0: window_px += 1
                if window_px < 5: window_px = 5
                    
                rolling_median_L = pd.Series(L_raw).rolling(window=window_px, center=True, min_periods=1).median().values
                crack_threshold = 6.0 
                crack_mask = L_raw < (rolling_median_L - crack_threshold)
                
                L_clean = np.copy(L_raw)
                L_clean[crack_mask] = rolling_median_L[crack_mask]
                
                # Identify voids/NaNs
                L_s = pd.Series(L_clean).replace([np.inf, -np.inf], np.nan)
                a_s = pd.Series(a_raw).replace([np.inf, -np.inf], np.nan)
                b_s = pd.Series(b_raw).replace([np.inf, -np.inf], np.nan)

                if L_s.isna().all():
                    is_void_section = True
                else:
                    # Create masks to group contiguous segments of sediment
                    valid_mask = L_s.notna()
                    groups = valid_mask.ne(valid_mask.shift()).cumsum()
                    
                    # Initialize empty arrays filled with NaNs
                    L_mean = np.full_like(L_clean, np.nan, dtype=float)
                    a_mean = np.full_like(a_raw, np.nan, dtype=float)
                    b_mean = np.full_like(b_raw, np.nan, dtype=float)
                    
                    # Apply Savitzky-Golay only to valid segments of data independently
                    # This makes the lithological contacts much sharper than preivous implementation
                    for _, group_idx in L_s[valid_mask].groupby(groups).groups.items():
                        actual_window = min(window_px, len(group_idx))
                        if actual_window % 2 == 0: actual_window -= 1
                        
                        idx = group_idx.values
                        if actual_window < 3:
                            L_mean[idx] = L_s.loc[idx]
                            a_mean[idx] = a_s.loc[idx]
                            b_mean[idx] = b_s.loc[idx]
                        else:
                            poly_order = min(3, actual_window - 1)
                            L_mean[idx] = savgol_filter(L_s.loc[idx], window_length=actual_window, polyorder=poly_order)
                            a_mean[idx] = savgol_filter(a_s.loc[idx], window_length=actual_window, polyorder=poly_order)
                            b_mean[idx] = savgol_filter(b_s.loc[idx], window_length=actual_window, polyorder=poly_order)
            
            # If the section was completely void, generate NaN arrays to track the depth interval
            if is_void_section:
                num_pixels = len(L_raw)
                L_mean = np.full(num_pixels, np.nan)
                a_mean = np.full(num_pixels, np.nan)
                b_mean = np.full(num_pixels, np.nan)
                
            L_mean = np.clip(L_mean, 0, 100)
            a_mean = np.clip(a_mean, -128, 127) 
            b_mean = np.clip(b_mean, -128, 127)
                
            num_pixels = len(L_mean)
            
            pixels_trimmed_top = y1_trim - box['y1']
            trim_offset_m = (pixels_trimmed_top / pixels_per_cm) / 100.0
            actual_start_depth_mbsf = top_mbsf + trim_offset_m
            
            mbsf_depths = actual_start_depth_mbsf + (np.arange(num_pixels) / pixels_per_cm) / 100.0
            
            for j in range(num_pixels):
                all_data.append({
                    'Leg': self.leg,
                    'Site': self.site,
                    'H': self.hole,
                    'Cor': self.core,
                    'T': self.core_type,
                    'Sc': sec_name,
                    'Top(cm)': round((mbsf_depths[j] - top_mbsf) * 100, 2), 
                    'Depth (mbsf)': round(mbsf_depths[j], 4),
                    'L*': round(L_mean[j], 3) if not np.isnan(L_mean[j]) else np.nan,
                    'a*': round(a_mean[j], 3) if not np.isnan(a_mean[j]) else np.nan,
                    'b*': round(b_mean[j], 3) if not np.isnan(b_mean[j]) else np.nan
                })
                
        final_df = pd.DataFrame(all_data)
        final_df.to_csv(output_filename, index=False)
        print(f" L*a*b* mapped and saved to: {output_filename}")
        
        coords_filename = output_filename.replace('.csv', '_boxes.txt')
        with open(coords_filename, 'w') as f:
            f.write("Type,x1,y1,x2,y2\n")
            for box in sorted_coords:
                f.write(f"Section,{box['x1']},{box['y1']},{box['x2']},{box['y2']}\n")
            for box in self.saved_void_coords:
                f.write(f"Void,{box['x1']},{box['y1']},{box['x2']},{box['y2']}\n")
        print(f" Saved bounding boxes & void coordinates to: {coords_filename}")
        
        if self.show_diagnostics:
            plt.show()
            
        calib_filename = output_filename.replace('.csv', '_calib.npz')
        np.savez(calib_filename, bg_curve_white=self.bg_curve_white, bg_curve_black=self.bg_curve_black)
        
        return final_df
    
    def _display_section_summary(self):
        """Filters section summary CSV for current core and displays a dynamically sized table."""
        if not hasattr(self, 'summary_csv') or not self.summary_csv or not os.path.exists(self.summary_csv):
            return

        try:
            df = pd.read_csv(self.summary_csv, sep=None, engine='python')
            df.columns = df.columns.str.strip()

            # Handle standard ODP/IODP column name variations
            col_site = 'Site'
            col_hole = 'Hole' if 'Hole' in df.columns else 'H'
            col_core = 'Core' if 'Core' in df.columns else 'Cor'

            # Match site (stripping 'U' prefix if present)
            csv_sites = df[col_site].astype(str).str.replace('U', '', regex=False)
            target_site = str(self.site).replace('U', '')

            # Filter for current Hole and Core
            core_df = df[
                (csv_sites == target_site) & 
                (df[col_hole].astype(str) == str(self.hole)) & 
                (df[col_core].astype(str) == str(self.core))
                ].copy()

            if core_df.empty:
                return

            # Sort by depth
            col_top = 'Top depth CSF-A (m)' if 'Top depth CSF-A (m)' in core_df.columns else ('Top(mbsf)' if 'Top(mbsf)' in core_df.columns else None)
            if col_top:
                core_df['_sort'] = pd.to_numeric(core_df[col_top], errors='coerce')
                core_df = core_df.sort_values('_sort', na_position='last').drop(columns=['_sort'])

            preferred_cols = ['Sc', 'Sect', 'LL(m)', 'CL(m)', 'Top depth CSF-A (m)', 'Top(mbsf)', 'Comment']
            disp_cols = [c for c in preferred_cols if c in core_df.columns]
            if not disp_cols:
                disp_cols = core_df.columns[:5].tolist()

            # Format table cell values & wrap long text
            raw_data = core_df[disp_cols].fillna('').astype(str)
            formatted_table_data = []
            for _, row in raw_data.iterrows():
                formatted_row = []
                for col in disp_cols:
                    val = str(row[col])
                    if len(val) > 20:
                        val = '\n'.join(textwrap.wrap(val, width=20))
                    formatted_row.append(val)  
                formatted_table_data.append(formatted_row)  

            # Calculate column widths
            max_col_chars = []
            for col_idx, col_name in enumerate(disp_cols):
                max_len = len(col_name)
                for row in formatted_table_data:
                    lines = row[col_idx].split('\n')
                    for line in lines:
                        if len(line) > max_len:
                            max_len = len(line)
                max_col_chars.append(max(max_len, 6))

            total_chars = sum(max_col_chars)
            col_widths = [w / total_chars for w in max_col_chars]

            # Right-hand panel axis
            ax_table = self.fig.add_axes([0.70, 0.15, 0.28, 0.70])
            ax_table.axis('off')
            ax_table.set_title(
                f"Section Summary\n(Site {self.site}{self.hole} - Core {self.core}{self.core_type})", 
                fontsize=10, fontweight='bold', pad=12, y = 0.75
                )
            
            # Render Table
            table = ax_table.table(
                cellText=formatted_table_data,
                colLabels=disp_cols,
                colWidths=col_widths,
                loc='center',
                cellLoc='center'
                )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1.0, 1.8)

            # Table styling
            for (row, col), cell in table.get_celld().items():
                if row == 0:
                    cell.set_facecolor('#2c3e50')
                    cell.set_text_props(color='white', fontweight='bold')
                else:
                    cell.set_facecolor('#f2f4f4' if row % 2 == 0 else '#ffffff')

        except Exception as e:
            print(f"Note: Could not render section summary table: {e}")

def extract_image_from_pdf(pdf_path, output_jpg_path):
    """
    Extracts the first page of a core image PDF as a high-resolution JPG.
    
    Note that some core photos have multiple pages in the .pdf. I have no idea why.
    """
    print(f"Opening {pdf_path}...")
    
    # Open the .pdf
    pdf_document = pymupdf.open(pdf_path)
    
    # Load the first page (index 0)
    page = pdf_document.load_page(0)
    
    # Render page to a high-res image (300 DPI)
    zoom = 300 / 72  # 72 is standard PDF DPI
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Save the image
    pix.save(output_jpg_path)
    print(f"-> Saved high-res image to {output_jpg_path}")


def parse_odp_filename(filepath):
    """
    Flexibly extracts Site, Hole, Core, Type, and Section.
    Uses sequential logic to separate Modern IODP files from Legacy files.
    """
    filename = os.path.basename(filepath)
    
    # Clean the filename first: strip extensions and "_converted" suffix
    clean_name = re.sub(r"(_converted)?\.(png|jpg|jpeg|tif|tiff|pdf)$", "", filename, flags=re.IGNORECASE)
    
    
    pattern_modern = r"^(?:Exp\.|Exp)?(\d{2,4})?[-_]?([Uu]\d{3,4})([A-Za-z\*]?)[-_\.]?(\d{1,3})([A-Za-z]?)[-_\.]?(\d{1,2}|CC)?$" # just imagine how much I enjoyed figuring this out :(
    match_modern = re.match(pattern_modern, clean_name)
    
    if match_modern:
        # match_modern.group(1) is the Expedition (e.g., 346), which we skip returning
        site = match_modern.group(2).upper()
        hole = match_modern.group(3).upper() if match_modern.group(3) else "*"
        core = int(match_modern.group(4))
        core_type = match_modern.group(5).upper() if match_modern.group(5) else ""
        section = match_modern.group(6).upper() if match_modern.group(6) else None
        return site, hole, core, core_type, section

    # ODP/DSDP or Shorthand (No "U" in the Site name)
    # Example: "925B1H", "374.5R"
    pattern_legacy = r"^(\d{3,4})([A-Za-z\*]?)[-_\.]?(\d{1,3})([A-Za-z]?)[-_\.]?(\d{1,2}|CC)?$" # just imagine how much I enjoyed figuring this out :(
    match_legacy = re.match(pattern_legacy, clean_name)
    
    if match_legacy:
        site = match_legacy.group(1).upper()
        hole = match_legacy.group(2).upper() if match_legacy.group(2) else "*"
        core = int(match_legacy.group(3))
        core_type = match_legacy.group(4).upper() if match_legacy.group(4) else ""
        section = match_legacy.group(5).upper() if match_legacy.group(5) else None
        return site, hole, core, core_type, section
        
    # If neither pattern matches, return Nones
    return None, None, None, None, None

def run_batch_digitization(image_paths, section_summary_csv, leg, output_prefix="Site_Master", show_diagnostics=False):
    """
    Loops through a list of images, opens the GUI for each one sequentially, 
    groups the extracted data by Hole, exports separate master CSVs for each Hole,
    and saves the ensemble detrending coefficients for image correction.
    """
    
    # Sort the images numerically by Hole, Core, and Section
    def get_sort_key(path):
        site, hole, core, core_type, section = parse_odp_filename(path)
        
        safe_site = site if site else ""
        safe_hole = hole if hole else ""
        safe_core = core if core is not None else 9999
        
        if section is None:
            safe_sec = -1  
        elif section == 'CC':
            safe_sec = 99  
        else:
            try:
                safe_sec = int(section)
            except ValueError:
                safe_sec = 50
                
        return (safe_site, safe_hole, safe_core, safe_sec)

    sorted_image_paths = sorted(image_paths, key=get_sort_key)
    
    extracted_data_by_hole = {}
    
    for img_path in sorted_image_paths:
        site, hole, core, core_type, section = parse_odp_filename(img_path)
        
        if not site:
            print(f"Skipping {img_path}: Could not auto-detect metadata.")
            continue
            
        if section:
            print(f"Running Digitizer: Site {site}{hole}, Core {core}{core_type}, Section {section}")
        else:
            print(f"Running Digitizer: Site {site}{hole}, Core {core}{core_type} (Whole Core Composite)")
        
        digitizer = CorePhotoDigitizer(
            image_path=img_path,
            section_summary_csv=section_summary_csv,
            leg=leg,
            site=site,
            hole=hole,
            core=core,
            core_type=core_type,
            section=section, 
            show_diagnostics=show_diagnostics 
        )
        
        safe_hole = hole.replace('*', '')
        individual_csv_name = f"{site}{safe_hole}_{core}{core_type}_Color_Data.csv"
        df = digitizer.process_and_export(individual_csv_name)
        
        if df is not None and not df.empty:
            if hole not in extracted_data_by_hole:
                extracted_data_by_hole[hole] = [] 
            extracted_data_by_hole[hole].append(df)

    print("Combining processed cores into datasets for each hole...")
    master_dfs = {}
    
    for hole, dfs in extracted_data_by_hole.items():
        if not dfs:
            continue
            
        master_df = pd.concat(dfs, ignore_index=True)
        
        core_col = next((c for c in ['Cor', 'Core', 'CORE', 'core'] if c in master_df.columns), 'Cor')
        sec_col  = next((c for c in ['Sc', 'Sec', 'Sect', 'Section', 'SECTION', 'sec'] if c in master_df.columns), 'Sc')
        top_col  = next((c for c in ['Top(cm)', 'Top', 'top', 'Depth_cm', 'Top_cm'] if c in master_df.columns), 'Top(cm)')
        
        master_df = master_df.sort_values(by=[core_col, 'Depth (mbsf)']).reset_index(drop=True)
        
        print(f"Applying Chromatic & Lightness Ensemble Artifact Correction to Hole {hole}...")
        
        sec_length_lookup = {}
        try:
            summary_df = pd.read_csv(section_summary_csv, sep=None, engine='python')
            summary_df.columns = summary_df.columns.str.strip()
            
            c_sum_col = next((c for c in ['Core', 'Cor'] if c in summary_df.columns), None)
            h_sum_col = next((c for c in ['Hole', 'H'] if c in summary_df.columns), None)
            s_sum_col = next((c for c in ['Sect', 'Sc', 'Section'] if c in summary_df.columns), None)
            l_sum_col = next((c for c in ['LL(m)', 'Length (m)', 'Curated length (m)', 'CL(m)'] if c in summary_df.columns), None)
            
            if h_sum_col:
                clean_target_hole = str(hole).replace('*', '').strip()
                summary_df = summary_df[summary_df[h_sum_col].astype(str).str.strip() == clean_target_hole]

            if c_sum_col and s_sum_col and l_sum_col:
                for _, r in summary_df.iterrows():
                    c_key = str(r[c_sum_col]).strip()
                    s_key = str(r[s_sum_col]).strip()
                    try:
                        val = float(r[l_sum_col])
                        if val > 0:
                            sec_length_lookup[(c_key, s_key)] = val
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"  Something is wrong: Could not build section length lookup from summary: {e}")

        def get_normalized_depth(row):
            c_key = str(row[core_col]).strip()
            s_key = str(row[sec_col]).strip()
            sec_len_m = sec_length_lookup.get((c_key, s_key), 1.5)
            norm = row[top_col] / (sec_len_m * 100.0)
            return np.clip(norm, 0.0, 1.0)

        master_df['norm_depth'] = master_df.apply(get_normalized_depth, axis=1)
        standard_grid = np.linspace(0, 1, 300)

        hole_ensemble_data = {}

        for channel in ['L*', 'a*', 'b*']:
            if channel not in master_df.columns: 
                continue
            
            stacked_data = []
            for (c, s), group in master_df.groupby([core_col, sec_col]):
                if len(group) > 10:
                    f = interp1d(group['norm_depth'], group[channel], bounds_error=False, fill_value=np.nan)
                    stacked_data.append(f(standard_grid))
                    
            if stacked_data:
                stacked_data = np.array(stacked_data)
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    master_dome = np.nanmedian(stacked_data, axis=0)
                    
                valid_mask = ~np.isnan(master_dome)
                if np.sum(valid_mask) > 5:
                    poly_coeffs = np.polyfit(standard_grid[valid_mask], master_dome[valid_mask], 4)
                    
                    section_artifact = np.polyval(poly_coeffs, master_df['norm_depth'])
                    baseline = np.mean(np.polyval(poly_coeffs, standard_grid))
                    
                    master_df[channel] = master_df[channel] - section_artifact + baseline
                    
                    hole_ensemble_data[f'{channel}_coeffs'] = poly_coeffs
                    hole_ensemble_data[f'{channel}_baseline'] = baseline
                    
        # L* cannot be below zero - add small offset if this happens
        if 'L*' in master_df.columns:
            min_L_master = master_df['L*'].min()
            if min_L_master < 0:
                master_df['L*'] = master_df['L*'] + abs(min_L_master)

        master_df.drop(columns=['norm_depth'], inplace=True, errors='ignore')
        
        safe_hole = hole.replace('*', '')
        
        # Save the polynomial coefficients for image processing
        if hole_ensemble_data:
            ensemble_file = f"{output_prefix}_Hole_{safe_hole}_Ensemble.npz"
            np.savez(ensemble_file, **hole_ensemble_data)
            print(f" Saved ensemble coefficients to: {ensemble_file}")
            
        final_output_csv = f"{output_prefix}_Hole_{safe_hole}_Color.csv"
        
        try:
            master_df.to_csv(final_output_csv, index=False)
            print(f" Master dataset for Hole {hole} saved to: {final_output_csv}")
        except PermissionError:
            backup_name = f"{output_prefix}_Hole_{safe_hole}_Color_BACKUP.csv"
            master_df.to_csv(backup_name, index=False)
            print(f" Could not save to {final_output_csv} (is it open in Excel?)")
            print(f" Master dataset for Hole {hole} saved as {backup_name} instead!")
            
        master_dfs[hole] = master_df
            
    return master_dfs

def compile_hole(directory_path, site_hole, output_filename=None):
    """
    Searches a directory for all individual core CSVs generated by CorePhotoDigitizer 
    for a specific hole (e.g., '969A'). Combines them, sorts them by depth, 
    and exports a final master CSV. This allows the user to analyze photos in batches
    rather than all at once. 
    """
    print(f"Compiling Dataset for {site_hole}")
    
    # Find all exported .csv files matching the Hole
    search_pattern = os.path.join(directory_path, f"*{site_hole}*.csv")
    all_csvs = glob.glob(search_pattern)
    
    valid_csvs = []
    for f in all_csvs:
        # Ignore files that are already master files, splice tables, or mapped subsamples
        if "Master" in f or "Splice" in f or "Mapped" in f:
            continue
        valid_csvs.append(f)
        
    if not valid_csvs:
        print(f"Error: No individual core CSVs found for '{site_hole}' in {directory_path}.")
        print('Are you in the correct directory?')
        return None
        
    print(f"Found {len(valid_csvs)} core files. Stitching together...")
    
    # Load and Concatenate
    df_list = []
    for csv in valid_csvs:
        try:
            df_list.append(pd.read_csv(csv))
        except Exception as e:
            print(f" Skipping {os.path.basename(csv)}: {e}")
            
    if not df_list:
        print("Error: No valid data could be loaded.")
        return None
        
    master_df = pd.concat(df_list, ignore_index=True)
    
    # Sort by depth [mbsf]
    print("Sorting stratigraphic sequence...")
    # Using the exact column names generated by your process_and_export function
    master_df['_sort_core'] = pd.to_numeric(master_df['Cor'], errors='coerce')
    master_df = master_df.sort_values(by=['_sort_core', 'Depth (mbsf)']).drop(columns=['_sort_core']).reset_index(drop=True)
    
    # Export
    if not output_filename:
        output_filename = os.path.join(directory_path, f"Site{site_hole}_Master_Color_Data.csv")
        
    master_df.to_csv(output_filename, index=False)
    print(f"BOOYAH! Master hole dataset saved to: {output_filename}")
    print(f"Total Measurements: {len(master_df)}")
    
    return master_df

def get_reflectance(lstar_array):
    """
    Converts L* values to % Reflectance (relative luminance Y in CIE Lab parlance).
    """
    lstar = np.asarray(lstar_array)
    fy = (lstar + 16.0) / 116.0
    reflectance = np.where(
        lstar > 8.0, 
        np.power(fy, 3) * 100.0, 
        (lstar / 903.296296) * 100.0
    )
    return reflectance


def assemble_core_photo(image_path, coords_txt_path, output_image_path, calib_npz_path=None, ensemble_npz_path=None):
    """
    Reads bounding boxes, crops sections, applies L* background lighting corrections, 
    applies chromatic ensemble detrending if coefficients are provided, applies void masks, 
    and stacks sections vertically.
    """
    print(f"Assembling vertical core photo for {image_path}...")
    raw_image = io.imread(image_path)
    
    bg_curve_white, bg_curve_black = None, None
    if calib_npz_path and os.path.exists(calib_npz_path):
        calib_data = np.load(calib_npz_path)
        bg_curve_white = calib_data.get('bg_curve_white')
        bg_curve_black = calib_data.get('bg_curve_black')
        
    ensemble_data = None
    if ensemble_npz_path and os.path.exists(ensemble_npz_path):
        ensemble_data = np.load(ensemble_npz_path)

    sections = []
    voids = []
    
    with open(coords_txt_path, 'r') as f:
        next(f)  
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 5: continue
            box = {'x1': int(parts[1]), 'y1': int(parts[2]), 'x2': int(parts[3]), 'y2': int(parts[4])}
            if parts[0] == 'Section': sections.append(box)
            elif parts[0] == 'Void': voids.append(box)
                
    if not sections:
        return

    x_spread = max(s['x1'] for s in sections) - min(s['x1'] for s in sections)
    y_spread = max(s['y1'] for s in sections) - min(s['y1'] for s in sections)
    sections = sorted(sections, key=lambda b: b['y1']) if y_spread > x_spread else sorted(sections, key=lambda b: b['x1'])
    
    cropped_sections = []
    max_width = 0
    
    for sec in sections:
        crop = np.copy(raw_image[sec['y1']:sec['y2'], sec['x1']:sec['x2']])
        
        if (bg_curve_white is not None and bg_curve_black is not None) or ensemble_data is not None:
            if crop.shape[-1] == 4:
                rgb_view = crop[:, :, :3]
            else:
                rgb_view = crop
                
            lab_crop = color.rgb2lab(rgb_view)
            
            # Lightness correction
            if bg_curve_white is not None and bg_curve_black is not None:
                L_channel = lab_crop[:, :, 0]
                
                w_curve_slice = bg_curve_white[sec['y1']:sec['y2']]
                b_curve_slice = bg_curve_black[sec['y1']:sec['y2']]
                
                dynamic_range_local = w_curve_slice - b_curve_slice
                dynamic_range_local[dynamic_range_local <= 0] = 1.0
                
                baseline_white = 95
                baseline_black = 20
                baseline_range = baseline_white - baseline_black
                
                b_curve_2d = b_curve_slice[:, np.newaxis]
                dyn_range_2d = dynamic_range_local[:, np.newaxis]
                
                L_corrected = L_channel - b_curve_2d
                ff_multiplier = baseline_range / dyn_range_2d
                L_corrected = (L_corrected * ff_multiplier) + baseline_black
                
                lab_crop[:, :, 0] = np.clip(L_corrected, 0, 100)
                
            # Ensemble detrending 
            if ensemble_data is not None:
                num_rows = lab_crop.shape[0]
                norm_depth_grid = np.linspace(0.0, 1.0, num_rows)
                
                channel_map = {'L*': 0, 'a*': 1, 'b*': 2}
                for chan, idx in channel_map.items():
                    coeffs_key = f'{chan}_coeffs'
                    base_key = f'{chan}_baseline'
                    
                    if coeffs_key in ensemble_data and base_key in ensemble_data:
                        poly_coeffs = ensemble_data[coeffs_key]
                        baseline = ensemble_data[base_key]
                        
                        artifact_curve = np.polyval(poly_coeffs, norm_depth_grid)
                        artifact_2d = artifact_curve[:, np.newaxis]
                        
                        lab_crop[:, :, idx] = lab_crop[:, :, idx] - artifact_2d + baseline
                
                lab_crop[:, :, 0] = np.clip(lab_crop[:, :, 0], 0, 100)

            corrected_rgb = color.lab2rgb(lab_crop) * 255.0
            rgb_view[:] = corrected_rgb.astype(np.uint8)

        if crop.ndim == 3 and crop.shape[2] == 3:
            alpha = np.full((crop.shape[0], crop.shape[1], 1), 255, dtype=crop.dtype)
            crop = np.concatenate((crop, alpha), axis=2)
        elif crop.ndim == 2:
            crop = np.stack([crop]*3 + [np.full_like(crop, 255)], axis=-1)
        
        if crop.shape[1] > crop.shape[0]:
            crop = np.rot90(crop, -1) 
            
        for v_box in voids:
            y_overlap = max(sec['y1'], v_box['y1']) < min(sec['y2'], v_box['y2'])
            x_overlap = max(sec['x1'], v_box['x1']) < min(sec['x2'], v_box['x2'])
            
            if y_overlap and x_overlap:
                vy1 = max(0, v_box['y1'] - sec['y1'])
                vy2 = min(sec['y2'] - sec['y1'], v_box['y2'] - sec['y1'])
                crop[vy1:vy2, :, :] = 0 
                
        if crop.shape[1] > max_width: max_width = crop.shape[1]
        cropped_sections.append(crop)
        
    padded_sections = []
    for crop in cropped_sections:
        pad_width = max_width - crop.shape[1]
        if pad_width > 0:
            padded = np.pad(crop, ((0, 0), (pad_width // 2, pad_width - (pad_width // 2)), (0, 0)), mode='constant', constant_values=0)
            padded_sections.append(padded)
        else:
            padded_sections.append(crop)
            
    vertical_core_photo = np.vstack(padded_sections)
    if not output_image_path.lower().endswith('.png'): output_image_path = os.path.splitext(output_image_path)[0] + '.png'
    io.imsave(output_image_path, vertical_core_photo)
    print(f"Vertical core photo saved to: {output_image_path}")


def assemble_hole_photo(hole, photos_dir, output_image_path, dpi=300, meters_per_cm=0.79, fig_width_cm=1.9):
    """
    Assembles vertical core photos for an entire Hole into a depth-proportional
    vertical composite PDF image with depth axis markers.
    """
    if not hole.cores:
        print(f"Error: Hole '{hole.hole_name}' has no core objects loaded.")
        return

    min_depth = min(core.drilled_top for core in hole.cores)
    max_depth = max(core.drilled_bottom for core in hole.cores)
    total_depth_m = max_depth - min_depth

    if total_depth_m <= 0:
        print("Error: Invalid depth range for hole.")
        return

    fig_width_inches = fig_width_cm / 2.54
    fig_height_cm = total_depth_m / meters_per_cm
    fig_height_inches = fig_height_cm / 2.54
    
    fig, ax = plt.subplots(figsize=(fig_width_inches, fig_height_inches))
    
    photo_files = glob.glob(os.path.join(photos_dir, "*_vertical.png"))
    print(f"\nAssembling vertical profile for Hole '{hole.hole_name}'...")
    print(f"Depth Interval: {min_depth:.2f} mbsf -> {max_depth:.2f} mbsf")

    for core in hole.cores:
        matched_file = None
        target_id = re.sub(r'[\W_]+', '', f"{hole.hole_name}{core.core_id}").upper()

        for pfile in photo_files:
            fname = os.path.basename(pfile)
            clean_fname = fname.lower().replace("_vertical.png", "")
            clean_fname = re.sub(r'[\W_]+', '', clean_fname).upper()
            
            if clean_fname == target_id:
                matched_file = pfile
                break

        if not matched_file:
            print(f"  [GAP] Photo for Core {core.core_id} not found. Preserving blank interval ({core.drilled_top:.2f}–{core.drilled_bottom:.2f} mbsf).")
            continue

        try:
            core_img = io.imread(matched_file)
            
            h, w = core_img.shape[:2]
            margin = int(w * 0.20)
            core_img_cropped = core_img[:, margin : w - margin]
            
            ax.imshow(
                core_img_cropped, 
                extent=[0, 1, core.drilled_bottom, core.drilled_top],
                aspect='auto'
            )
            print(f"  -> Placed Core {core.core_id} @ {core.drilled_top:.2f}–{core.drilled_bottom:.2f} mbsf")
        except Exception as e:
            print(f"  Error reading {matched_file}: {e}")

    ax.set_ylim(max_depth, min_depth)
    ax.set_xlim(0, 1)
    ax.set_ylabel('Depth (mbsf)', fontsize=12, fontweight='bold')
    ax.set_xticks([])  
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    
    ax.minorticks_on()
    ax.tick_params(axis='y', which='major', length=7, width=1.5)
    ax.tick_params(axis='y', which='minor', length=4, width=1)

    output_pdf_path = os.path.splitext(output_image_path)[0] + '.pdf'

    plt.savefig(output_pdf_path, format='pdf', bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    
    print(f"\nSUCCESS: Assembled hole profile saved to: {output_pdf_path}")
    
def stack_photos(summary_csv_path, master_datasets, run_cores=True, run_holes=True, work_dir="."):
    """
    Executes the entire core and hole assembly pipeline in a single call.
    """
    from core_composite.models import Hole, Core

    def normalize_name(filename):
        base = os.path.basename(filename)
        base = base.replace("_converted.jpg", "").replace("_Color_Data_boxes.txt", "")
        base = re.sub(r'^Site', '', base, flags=re.IGNORECASE)
        return re.sub(r'[\W_]+', '', base).upper()

    # Core assembly loop
    if run_cores:
        print("Starting Core Assembly...")
        all_core_photos = glob.glob(os.path.join(work_dir, "*_converted.jpg"))
        all_coord_files = glob.glob(os.path.join(work_dir, "*Color_Data_boxes.txt"))
        coord_map = {normalize_name(txt): txt for txt in all_coord_files}

        for img_path in all_core_photos:
            pure_id = normalize_name(img_path)
            if pure_id in coord_map:
                coords_txt_path = coord_map[pure_id]
                output_image_path = os.path.join(work_dir, f"{pure_id}_vertical.png")
                assemble_core_photo(img_path, coords_txt_path, output_image_path)

    # Hole assembly loop
    if run_holes:
        print("Starting Hole Assembly...")
        summary_df = pd.read_csv(summary_csv_path, sep=None, engine='python')
        data_df = pd.concat(master_datasets.values(), ignore_index=True) if isinstance(master_datasets, dict) else master_datasets

        vertical_photos = glob.glob(os.path.join(work_dir, "*_vertical.png"))
        hole_groups = {}
        
        for photo in vertical_photos:
            base_id = os.path.basename(photo).replace("_vertical.png", "")
            match = re.search(r'^(.*?)[\.\-\_]?(\d+[A-Za-z])$', base_id, re.IGNORECASE)
            hole_id = match.group(1).upper() if match else base_id.split('_')[0]
            hole_groups.setdefault(hole_id, []).append(photo)

        for df in [data_df, summary_df]:
            site_c = next((c for c in df.columns if c.lower() == 'site'), None)
            hole_c = next((c for c in df.columns if c.lower() in ['hole', 'h']), None)
            core_c = next((c for c in df.columns if c.lower() in ['core', 'cor']), None)
            type_c = next((c for c in df.columns if c.lower() in ['type', 't']), None)

            if site_c and hole_c:
                clean_site = df[site_c].astype(str).str.replace(r'^site', '', flags=re.IGNORECASE, regex=True)
                df['Target_Hole'] = clean_site + df[hole_c].astype(str)
            elif hole_c:
                df['Target_Hole'] = df[hole_c].astype(str)

            if core_c and type_c:
                df['Target_Core'] = df[core_c].astype(str) + df[type_c].fillna('').astype(str)
            elif core_c:
                df['Target_Core'] = df[core_c].astype(str)

        for hole_name, photos in hole_groups.items():
            output_pdf_path = os.path.join(work_dir, f"{hole_name}_compiled.pdf")
            hole_obj = Hole(hole_name) 
            
            hole_summary = summary_df[summary_df['Target_Hole'].str.upper() == hole_name.upper()]
            hole_data = data_df[data_df['Target_Hole'].str.upper() == hole_name.upper()]

            if not hole_summary.empty and not hole_data.empty:
                for core_id, core_group in hole_data.groupby('Target_Core'):
                    core_csv_data = hole_summary[hole_summary['Target_Core'].astype(str) == str(core_id)]
                    if core_csv_data.empty: continue
                    
                    drilled_top = core_csv_data['Top(mbsf)'].min()
                    drilled_bottom = (core_csv_data['Top(mbsf)'] + core_csv_data['CL(m)']).max()
                    recovered_length = core_csv_data['CL(m)'].sum()
                    
                    core_obj = Core(hole_name=hole_name, core_id=core_id, core_df=core_group, 
                                    drilled_top=drilled_top, drilled_bottom=drilled_bottom, 
                                    recovered_length=recovered_length,
                                    proxy_keywords=['L*', 'a*', 'b*'])
                    hole_obj.cores.append(core_obj)

            if hole_obj.cores:
                assemble_hole_photo(hole=hole_obj, photos_dir=work_dir, output_image_path=output_pdf_path)
                
def convert_pdfs_to_images(work_dir="."):
    """
    Finds all PDFs in the specified directory and extracts them to JPGs.
    """
    import os
    import glob

    print("\n--- Step 1: .pdf to .jpg conversion ---")
    pdf_files = sorted(glob.glob(os.path.join(work_dir, "*.pdf")))

    if not pdf_files:
        print("No .pdf files found. Skipping conversion step.")
        return

    for pdf_path in pdf_files:
        base_name = os.path.splitext(pdf_path)[0]
        jpg_path = f"{base_name}_converted.jpg"

        if os.path.exists(jpg_path):
            print(f"Skipping {pdf_path}: {jpg_path} already exists.")
        else:
            print(f"Converting {pdf_path}.")
            extract_image_from_pdf(pdf_path, jpg_path)


def digitize_core_photos(summary_csv_path, leg, output_prefix, work_dir="."):
    """
    Finds all valid core photos and runs the interactive batch digitizer.
    Returns the compiled master datasets.
    """
    import os
    import glob

    print("\n--- Step 2: Core photo batch digitization ---")
    search_patterns = ["*_converted.jpg", "*.png", "*.jpg", "*.jpeg"]
    all_core_photos = []

    for pattern in search_patterns:
        matched_files = glob.glob(os.path.join(work_dir, pattern))
        for f in matched_files:
            if not f.endswith("_vertical.png"):
                all_core_photos.append(f)

    all_core_photos = sorted(list(set(all_core_photos)))

    if not all_core_photos:
        print("Could not find any valid core photos in this folder.")
        return None

    print(f"Found {len(all_core_photos)} image files to check.")
    
    master_datasets = run_batch_digitization(
        image_paths=all_core_photos,
        section_summary_csv=summary_csv_path,
        leg=leg,
        output_prefix=output_prefix
    )
    
    return master_datasets

def evaluate_exposure(image_path, dark_thresh=5, bright_thresh=250, tolerance=0.05, 
                      plot_diagnostics=False, figure_filename='core_photo.pdf'):
    """
    Evaluates image exposure and diagnoses which specific color channels 
    (Red, Green, Blue) are suffering from information loss.
    """
    image = io.imread(image_path)
    if image.shape[-1] == 4:
        image = image[:, :, :3]
        
    total_pixels = image.shape[0] * image.shape[1]
    
    # Split into individual channels
    r_channel, g_channel, b_channel = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    
    # Calculate clipping ratios per channel
    diagnostics = {
        "Red": {
            "Dark": np.sum(r_channel <= dark_thresh) / total_pixels,
            "Bright": np.sum(r_channel >= bright_thresh) / total_pixels
        },
        "Green": {
            "Dark": np.sum(g_channel <= dark_thresh) / total_pixels,
            "Bright": np.sum(g_channel >= bright_thresh) / total_pixels
        },
        "Blue": {
            "Dark": np.sum(b_channel <= dark_thresh) / total_pixels,
            "Bright": np.sum(b_channel >= bright_thresh) / total_pixels
        }
    }
    
    # Identify channels losing information
    crushed_channels = [channel_name for channel_name, channel_stats in diagnostics.items() if channel_stats["Dark"] > tolerance]
    blown_channels = [channel_name for channel_name, channel_stats in diagnostics.items() if channel_stats["Bright"] > tolerance]
    
    if plot_diagnostics:
        # plots of each of the color channels
        fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(12, 4), sharey=True)
        
        # reds
        axes[0].hist(r_channel.ravel(), bins=256, edgecolor='none', color='#CC79A7')
        axes[0].set_title('Reds Histogram')
        axes[0].set_xlabel('Red Pixel Values')
        axes[0].set_ylabel('Frequency')
        
        # blues
        axes[1].hist(b_channel.ravel(), bins=256, edgecolor='none', color='#0072B2')
        axes[1].set_title('Blues Histogram')
        axes[1].set_xlabel('Blue Pixel Values')
        
        # green
        axes[2].hist(g_channel.ravel(), bins=256, edgecolor='none', color='#009E73')
        axes[2].set_title('Greens Histogram')
        axes[2].set_xlabel('Green Pixel Values')
        
        plt.tight_layout()
        plt.savefig(figure_filename)
        plt.show()
    
    # Print numerical breakdown
    print(f"--- Exposure Diagnostics for {image_path} ---")
    for channel_name, channel_stats in diagnostics.items():
        print(f"{channel_name} Channel -> Crushed Shadows: {channel_stats['Dark']:.2%}, Blown Highlights: {channel_stats['Bright']:.2%}")
        
    # Formulate final status and warning
    status = "Well Exposed"
    warnings = []
    
    if crushed_channels or blown_channels:
        if crushed_channels and blown_channels:
            status = "High Contrast / Both Over & Under Exposed"
        elif crushed_channels:
            status = "Underexposed"
        elif blown_channels:
            status = "Overexposed"
            
        if crushed_channels:
            warnings.append(f"Loss of {', '.join(crushed_channels)} data in shadows.")
        if blown_channels:
            warnings.append(f"Loss of {', '.join(blown_channels)} data in highlights.")
            
    print(f"Overall Status: {status}")
    for warning in warnings:
        print(f"*** WARNING: {warning} ***")
        
    return status, warnings, diagnostics


def check_photo_quality(directory_path=".", file_extension="*.jpg"):
    """
    Scans a directory, evaluates exposure without plotting, 
    and prints a quantitative summary table to the console.
    """
    folder = Path(directory_path)
    image_files = list(folder.glob(file_extension))
    
    original_stdout = sys.stdout 
    
    results = []
    for img_path in image_files:
        sys.stdout = open(os.devnull, 'w') # Block inner print statements
        try:
            status, warnings, diagnostics = evaluate_exposure(
                str(img_path), 
                plot_diagnostics=False
            )
        finally:
            sys.stdout = original_stdout # Restore printing
            
        crushed_str = (f"R:{diagnostics['Red']['Dark']:.1%} | "
                       f"G:{diagnostics['Green']['Dark']:.1%} | "
                       f"B:{diagnostics['Blue']['Dark']:.1%}")
                       
        blown_str = (f"R:{diagnostics['Red']['Bright']:.1%} | "
                     f"G:{diagnostics['Green']['Bright']:.1%} | "
                     f"B:{diagnostics['Blue']['Bright']:.1%}")
        
        results.append({
            "Image Name": img_path.name,
            "Quality": status,
            "Crushed Shadows": crushed_str,
            "Blown Highlights": blown_str
        })
        
    # Generate and print the table to the console
    df = pd.DataFrame(results)
    print("\n--- Batch Exposure Report ---")
    print(df.to_string(index=False))
    
    return df

def Munsell_CIELAB_converter(Munsell_csv, output_csv = "Munsell_converted.csv"):
    colors = pd.read_csv(Munsell_csv)
    munsell = colors['Munsell']
    xyY = colour.munsell_colour_to_xyY(munsell)
    xyz = colour.xyY_to_XYZ(xyY)
    munsell_converted_to_LAB = colour.XYZ_to_Lab(xyz)
    
    colors[['L*', 'a*', 'b*']] = munsell_converted_to_LAB
    colors.to_csv(output_csv, index = False)
    
    print('Munsell color data from f{Munsell_csv} converted to CIELAB')
    print('and saved to f{output_csv}')
    return 