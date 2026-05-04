# -*- coding: utf-8 -*-
"""
Created on Mon May  4 13:33:52 2026

@author: joseph novak 

CorePhotoDigitizer and supporting functions
"""

import os
import re
import fitz  # PyMuPDF
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

class CorePhotoDigitizer:
    """
    CorePhotoDigitizer and the trailing supporting functions facilitiate extraction of L*, a*, and b* values from 
    DSDP/ODP/IODP core photos. These scripts require section summaries to map the extracted pixel-level data to 
    depth mbsf. 
    """
    def __init__(self, image_path, section_summary_csv, leg, site, hole, core, core_type, section=None, show_diagnostics=False):
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
        
        # Calibration defaults (1.0 slope, 0.0 offset = no change)
        self.calib_m_L = 1.0
        self.calib_c_L = 0.0
        self.calib_c_a = 0.0
        self.calib_c_b = 0.0
        
        # Background calibration defaults
        self.bg_curve_white = None
        self.bg_curve_black = None
        
        self.bg_coords = None
        
    def _run_gui(self):
        print(f"Loading {self.image_path} for interactive processing...")
        
        self.raw_image = io.imread(self.image_path)
        # Downscale for display purposes so it fits on normal monitors
        self.display_image = transform.rescale(self.raw_image, 0.25, channel_axis=-1, anti_aliasing=True)
        
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.ax.imshow(self.display_image)
        plt.subplots_adjust(left=0.1) 
        
        # Start immediately with mandatory Background Calibration
        self._start_background_calibration()
        
        # Halt the script and wait for the user to draw boxes
        plt.show(block=True)
        
    def _start_background_calibration(self):
        plt.subplots_adjust(left=0.1)
        self.ax.set_title(
            "BACKGROUND 1: VERTICAL\n"
            "1. Draw one box down any white track.\n"
            "2. Press 'Enter' when done.",
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
            self.temp_bg_coords = (x1*4, y1*4, x2*4, y2*4)

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
                    self._process_background_curves()

        # User needs to hit the enter key
        self.bg_cid = self.fig.canvas.mpl_connect('key_press_event', on_bg_enter)

        
    def _process_background_curves(self):
        print("\nExtracting 2D Lighting Surface and Color Temperature Gradients...")

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
        self.ax.set_title("STEP 3: Optional Color Checker", fontsize=14, fontweight='bold')
        self.fig.canvas.draw()
        
        self.ax_anch = plt.axes([0.05, 0.6, 0.2, 0.15], facecolor='lightgray')
        self.radio_anchor = RadioButtons(self.ax_anch, (
            'Skip (Use Model Basis)', 
            'Use Kodak Checker (Black & White)'
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
                
            elif self.anchoring_choice == 'Use Kodak Checker (Black & White)':
                self._start_2point_anchor_calibration()
                
        self.btn_anch_proceed.on_clicked(anchor_proceed_clicked)
        self.fig.canvas.draw()
        
    def _start_2point_anchor_calibration(self):
        self.calib_pts = []
        self.ax.set_title(
            "KODAK ANCHOR: CLICK 2 POINTS\n"
            "1. Click the absolute White.\n"
            "2. Click the absolute Black.\n",
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
            print("\nCalculating Shadow-Corrected Kodak Anchor Offsets...", flush=True)
            w_x_disp, w_y_disp = int(self.calib_pts[0][0]), int(self.calib_pts[0][1])
            b_x_disp, b_y_disp = int(self.calib_pts[1][0]), int(self.calib_pts[1][1])
            
            w_x, w_y = w_x_disp*4, w_y_disp*4
            b_x, b_y = b_x_disp*4, b_y_disp*4
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
                
                meas_w_L_flattened = meas_w_L + (95.0 - y_shadow_w)
                meas_b_L_flattened = meas_b_L + (95.0 - y_shadow_b)
                
                if hasattr(self, 'bg_curve_white_x') and self.bg_curve_white_x is not None:
                    macro_x_shadow_w = self.bg_curve_white_x[w_x] - self.bg_curve_white_x[self.bg_ref_x]
                    macro_x_shadow_b = self.bg_curve_white_x[b_x] - self.bg_curve_white_x[self.bg_ref_x]
                    
                    meas_w_L_flattened -= macro_x_shadow_w
                    meas_b_L_flattened -= macro_x_shadow_b
                
                meas_w_L = meas_w_L_flattened
                meas_b_L = meas_b_L_flattened
            
            true_w_L, true_b_L = 95.0, 20.0
            
            if meas_w_L != meas_b_L: 
                self.calib_m_L = (true_w_L - true_b_L) / (meas_w_L - meas_b_L)
                self.calib_c_L = true_w_L - (self.calib_m_L * meas_w_L)
            
            self.calib_c_a = 0.0 - meas_w_a
            self.calib_c_b = 0.0 - meas_w_b
            
            print(f" -> Best-Fit L* Slope: {self.calib_m_L:.2f}, Offset: {self.calib_c_L:.2f}", flush=True)
            self._start_cropping_phase()
            
        except Exception as e:
            print(f"\nCRITICAL ERROR in anchor calculation: {e}\n", flush=True)
            self.calib_m_L, self.calib_c_L, self.calib_c_a, self.calib_c_b = 1.0, 0.0, 0.0, 0.0
            self._start_cropping_phase()

    def _start_cropping_phase(self):
        plt.subplots_adjust(left=0.1)
        
        self.ax.set_title(
            f"Digitizing {self.site}{self.hole}-{self.core}{self.core_type}\n"
            "1. Drag boxes over sediment.\n2. Use Arrow Keys to nudge.\n3. Close window to extract.", 
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
            'x1': int(min(x1, x2) * 4),
            'y1': int(min(y1, y2) * 4),
            'x2': int(max(x1, x2) * 4),
            'y2': int(max(y1, y2) * 4)
        })
        self.fig.canvas.draw()

    def on_key(self, event):
        if not self.rectangles: return 
        if event.key == 'd':
            self.rectangles.pop().remove()
            self.saved_coords.pop()
            self.fig.canvas.draw()
        elif event.key in ['up', 'down', 'left', 'right']:
            rect = self.rectangles[-1]
            coords = self.saved_coords[-1]
            x, y = rect.get_xy()
            if event.key == 'up':
                rect.set_y(y - 1); coords['y1'] -= 4; coords['y2'] -= 4
            elif event.key == 'down':
                rect.set_y(y + 1); coords['y1'] += 4; coords['y2'] += 4
            elif event.key == 'left':
                rect.set_x(x - 1); coords['x1'] -= 4; coords['x2'] -= 4
            elif event.key == 'right':
                rect.set_x(x + 1); coords['x1'] += 4; coords['x2'] += 4
            self.fig.canvas.draw()

    def process_and_export(self, output_filename):
        self._run_gui()
        
        if not self.saved_coords:
            print("No boxes drawn. Exiting...")
            return None
            
        sorted_coords = sorted(self.saved_coords, key=lambda box: box['x1'])
        
        print("\nLoading section metadata and extracting data...")
        summary_df = pd.read_csv(self.summary_csv)
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
            print("ERROR: Could not find a valid top depth column.")
            return None
            
        if 'Length (m)' in summary_df.columns:
            self.col_length = 'Length (m)'
        elif 'CL(m)' in summary_df.columns:
            self.col_length = 'CL(m)'
        elif 'Curated length (m)' in summary_df.columns:
            self.col_length = 'Curated length (m)'
        else:
            print("ERROR: Could not find a valid length column.")
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
            print(f"ERROR: Could not find metadata for Site {self.site}{self.hole} Core {self.core} Section {self.section}!")
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
                print(f"  -> WARNING: Missing depth/length metadata for Section {sec_name}. Output depths will be NaN.")
            
            print(f"Processing Section {sec_name}...")
            
            y1_raw = box['y1']
            y2_raw = box['y2']
            
            if box['x1'] >= box['x2'] or y1_raw >= y2_raw:
                print(f"  -> WARNING: Skipping invalid box for Section {sec_name}. (Accidental click?)")
                continue
                
            original_height = y2_raw - y1_raw
            pixels_per_cm = original_height / (length_m * 100) if length_m > 0 else 1
            
            trim_cm = 1.5 
            trim_px = int(pixels_per_cm * trim_cm)
            
            if length_m > 0.05:
                y1_trim = y1_raw + trim_px
                y2_trim = y2_raw - trim_px
            else:
                y1_trim = y1_raw
                y2_trim = y2_raw
                trim_px = 0
                
            cropped_rgb = self.raw_image[y1_trim:y2_trim, box['x1']:box['x2']]
            
            if cropped_rgb.shape[-1] == 4:
                cropped_rgb = cropped_rgb[:, :, :3]
            
            lab_core = color.rgb2lab(cropped_rgb)
            L_box = lab_core[:, :, 0]
            box_width = L_box.shape[1]
            
            x_profile = np.mean(L_box, axis=0) 
            x_coords = np.arange(box_width)
            poly_coeffs = np.polyfit(x_coords, x_profile, 2)
            x_curve = np.polyval(poly_coeffs, x_coords)
            
            baseline_mean = np.mean(x_curve)
            lab_core[:, :, 0] = L_box - x_curve + baseline_mean
            lab_core[:, :, 0] = np.clip(lab_core[:, :, 0], 0, 100)
            
            if self.show_diagnostics and i in [0, 1]:
                print(f"Generating Horizontal Cylinder Diagnostic Plot for Box {i+1}...")
                fig_horiz, ax_horiz = plt.subplots(figsize=(8, 5))
                ax_horiz.set_title(f"Diagnostic: Horizontal Cylinder Shadows (Box {i+1})", fontweight='bold')
                ax_horiz.plot(x_coords, x_profile, color='gray', alpha=0.7, label='Raw Horizontal Profile')
                ax_horiz.plot(x_coords, x_curve, color='red', linewidth=3, label='Polynomial Lighting Model')
                ax_horiz.set_xlabel("Pixel Column (Left Edge -> Right Edge of Box)")
                ax_horiz.set_ylabel("Lightness (L*)")
                ax_horiz.legend()
                fig_horiz.tight_layout()
                
            L_raw = np.percentile(lab_core[:, :, 0], 50, axis=1) 
            a_raw = np.percentile(lab_core[:, :, 1], 50, axis=1) 
            b_raw = np.percentile(lab_core[:, :, 2], 50, axis=1) 
            
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
                
                baseline_white = np.mean(w_curve_slice)
                baseline_black = np.mean(b_curve_slice)
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
            
            L_mean = savgol_filter(L_clean, window_length=window_px, polyorder=3)
            a_mean = savgol_filter(a_raw, window_length=window_px, polyorder=3)
            b_mean = savgol_filter(b_raw, window_length=window_px, polyorder=3)
            
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
                    'Depth (mbsf)': round(mbsf_depths[j], 3),
                    'L*': round(L_mean[j], 3),
                    'a*': round(a_mean[j], 3),
                    'b*': round(b_mean[j], 3)
                })
                
        final_df = pd.DataFrame(all_data)
        final_df.to_csv(output_filename, index=False)
        print(f"\nSUCCESS! High-res L*a*b* mapped and saved to: {output_filename}")
        
        if self.show_diagnostics:
            plt.show()
        
        return final_df

def extract_image_from_pdf(pdf_path, output_jpg_path):
    """
    Extracts the first page of a core image PDF as a high-resolution JPG.
    """
    print(f"Opening {pdf_path}...")
    
    # Open the PDF document
    pdf_document = fitz.open(pdf_path)
    
    # Load the first page (index 0)
    page = pdf_document.load_page(0)
    
    # Render page to a high-res image (300 DPI)
    zoom = 300 / 72  # 72 is standard PDF DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Save the image
    pix.save(output_jpg_path)
    print(f"-> Saved high-res image to {output_jpg_path}")


def parse_odp_filename(filepath):
    """
    Flexibly extracts Site, Hole, Core, Type, and (optionally) Section.
    Uses sequential logic to separate Modern IODP files from Legacy files.
    """
    filename = os.path.basename(filepath)
    
    # Clean the filename first: strip extensions and "_converted" suffix
    clean_name = re.sub(r"(_converted)?\.(png|jpg|jpeg|tif|tiff|pdf)$", "", filename, flags=re.IGNORECASE)
    
    # Modern IODP (Requires a "U" in the Site name)
    # Example: "346U1426A1", "321U1338A1", "Exp342-U1426A-1H"
    
    pattern_modern = r"^(?:Exp\.|Exp)?(\d{2,4})?[-_]?([Uu]\d{3,4})([A-Za-z\*]?)[-_\.]?(\d{1,3})([A-Za-z]?)[-_\.]?(\d{1,2}|CC)?$"
    match_modern = re.match(pattern_modern, clean_name)
    
    if match_modern:
        # match_modern.group(1) is the Expedition (e.g., 346), which we skip returning
        site = match_modern.group(2).upper()
        hole = match_modern.group(3).upper() if match_modern.group(3) else "*"
        core = int(match_modern.group(4))
        core_type = match_modern.group(5).upper() if match_modern.group(5) else ""
        section = match_modern.group(6).upper() if match_modern.group(6) else None
        return site, hole, core, core_type, section

    # Legacy ODP/DSDP or Shorthand (No "U" in the Site name)
    # Example: "925B1H", "374.5R"
    pattern_legacy = r"^(\d{3,4})([A-Za-z\*]?)[-_\.]?(\d{1,3})([A-Za-z]?)[-_\.]?(\d{1,2}|CC)?$"
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
    groups the extracted data by Hole, and exports separate master CSVs for each Hole.
    Also applies chromatic ensemble detrending.
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
        # Auto-detect metadata
        site, hole, core, core_type, section = parse_odp_filename(img_path)
        
        if not site:
            print(f"Skipping {img_path}: Could not auto-detect metadata.")
            continue
            
        # Dynamic print statement
        print(f"\n{'='*50}")
        if section:
            print(f"LAUNCHING DIGITIZER: Site {site}{hole}, Core {core}{core_type}, Section {section}")
        else:
            print(f"LAUNCHING DIGITIZER: Site {site}{hole}, Core {core}{core_type} (Whole Core Composite)")
        print(f"{'='*50}")
        
        # Initialize the tool
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
        
        # Run the GUI
        safe_hole = hole.replace('*', '')
        individual_csv_name = f"{site}{safe_hole}_{core}{core_type}_Color_Data.csv"
        df = digitizer.process_and_export(individual_csv_name)
        
        # Save the data to our master list
        if df is not None and not df.empty:
            if hole not in extracted_data_by_hole:
                extracted_data_by_hole[hole] = [] 
            extracted_data_by_hole[hole].append(df)

    # Post-processing: combine and export datasets
    print("\nCombining processed cores into Hole-specific datasets...")
    master_dfs = {}
    
    for hole, dfs in extracted_data_by_hole.items():
        if not dfs:
            continue
            
        master_df = pd.concat(dfs, ignore_index=True)
        
        core_col = next((c for c in ['Cor', 'Core', 'CORE', 'core'] if c in master_df.columns), 'Cor')
        sec_col  = next((c for c in ['Sc', 'Sec', 'Sect', 'Section', 'SECTION', 'sec'] if c in master_df.columns), 'Sc')
        top_col  = next((c for c in ['Top(cm)', 'Top', 'top', 'Depth_cm', 'Top_cm'] if c in master_df.columns), 'Top(cm)')
        
        master_df = master_df.sort_values(by=[core_col, 'Depth (mbsf)']).reset_index(drop=True)
        
        # chromatic ensemble detrending for tint effects in a* and b*

        print(f"Applying Chromatic (a*/b*) Ensemble Artifact Correction to Hole {hole}...")
        
        # Normalize depth based on the absolute 150 cm camera track
        master_df['norm_depth'] = master_df[top_col] / 150.0
        master_df['norm_depth'] = np.clip(master_df['norm_depth'], 0.0, 1.0)
        
        standard_grid = np.linspace(0, 1, 300)
        
        # Loop through only the chromatic channels
        for channel in ['a*', 'b*']:
            if channel not in master_df.columns: continue
            
            stacked_data = []
            for (c, s), group in master_df.groupby([core_col, sec_col]):
                # Only use relatively complete sections
                if len(group) > 10:
                    f = interp1d(group['norm_depth'], group[channel], bounds_error=False, fill_value=np.nan)
                    stacked_data.append(f(standard_grid))
                    
            if stacked_data:
                stacked_data = np.array(stacked_data)
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    master_dome = np.nanmedian(stacked_data, axis=0)
                    
                valid_mask = ~np.isnan(master_dome)
                if np.sum(valid_mask) > 3:
                    poly_coeffs = np.polyfit(standard_grid[valid_mask], master_dome[valid_mask], 2)
                    
                    # Apply the mathematically mapped frown based on true coordinates
                    section_artifact = np.polyval(poly_coeffs, master_df['norm_depth'])
                    baseline = np.mean(np.polyval(poly_coeffs, standard_grid))
                    
                    # Additively remove the tint effect
                    master_df[channel] = master_df[channel] - section_artifact + baseline
                    
        # Clean up the temporary column
        master_df.drop(['norm_depth'], axis=1, inplace=True, errors='ignore')
        
        safe_hole = hole.replace('*', '')
        final_output_csv = f"{output_prefix}_Hole_{safe_hole}_Color_Reflectance.csv"
        
        try:
            master_df.to_csv(final_output_csv, index=False)
            print(f"\n{'='*50}")
            print(f"Success! Master dataset for Hole {hole} saved to: {final_output_csv}")
        except PermissionError:
            backup_name = f"{output_prefix}_Hole_{safe_hole}_Color_Reflectance_BACKUP.csv"
            master_df.to_csv(backup_name, index=False)
            print(f"\n{'='*50}")
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
    print(f"\nCompiling Dataset for {site_hole}")
    
    # Find all exported CSVs matching the Hole
    search_pattern = os.path.join(directory_path, f"*{site_hole}*.csv")
    all_csvs = glob.glob(search_pattern)
    
    valid_csvs = []
    for f in all_csvs:
        # Ignore files that are already master files, splice tables, or mapped subsamples
        if "Master" in f or "Splice" in f or "Mapped" in f:
            continue
        valid_csvs.append(f)
        
    if not valid_csvs:
        print(f"ERROR: No individual core CSVs found for '{site_hole}' in {directory_path}.")
        return None
        
    print(f"Found {len(valid_csvs)} core files. Stitching together...")
    
    # Load and Concatenate
    df_list = []
    for csv in valid_csvs:
        try:
            df_list.append(pd.read_csv(csv))
        except Exception as e:
            print(f"  -> Skipping {os.path.basename(csv)}: {e}")
            
    if not df_list:
        print("ERROR: No valid data could be loaded.")
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