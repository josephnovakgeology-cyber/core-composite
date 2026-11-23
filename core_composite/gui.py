# -*- coding: utf-8 -*-
"""
Created on Fri May  1 07:18:57 2026

@author: joseph novak

the GUIs for handling stratigraphic data
"""
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons, CheckButtons, Button, TextBox
import numpy as np
import pandas as pd
import itertools
import copy
from .io import export_project_data

class ReviewGUI:
    """
    ReviewGUI gives the user the opportunity to do the following:
        1). Inspect the quality of the automatic alignment of off-splice core sections
        2). Manually provide tiepoints for semi-automatic alignment of entirely off-splice cores
    """
    def __init__(self, builder, proxy=None):
        self.builder = builder
        self.history = []
        self.view_min = None
        self.view_max = None
        
        # Gather all available proxies dynamically from the data
        self.all_proxies = []
        for h in self.builder.holes.values():
            for c in h.cores:
                for p in getattr(c, 'active_proxies', []): 
                    if p not in self.all_proxies:
                        self.all_proxies.append(p)
                        
        if not self.all_proxies:
            self.all_proxies = ['No Data']
            
        self.proxy = proxy if proxy in self.all_proxies else self.all_proxies[0]
        
        # Build UI
        self.fig, self.ax = plt.subplots(figsize=(15, 8))
        self.fig.canvas.manager.set_window_title('Multi-Track Alignment')
        plt.subplots_adjust(left=0.18, bottom=0.15)
        
        # UI Element: Depth Window Controls (TextBoxes)
        ax_min = plt.axes([0.42, 0.05, 0.08, 0.05])
        self.txt_min = TextBox(ax_min, 'Min: ', initial='')
        self.txt_min.on_submit(self.submit_min)

        ax_max = plt.axes([0.55, 0.05, 0.08, 0.05])
        self.txt_max = TextBox(ax_max, 'Max: ', initial='')
        self.txt_max.on_submit(self.submit_max)
        
        # UI Element: Proxy Selector Buttons
        ax_radio_proxy = plt.axes([0.02, 0.65, 0.12, 0.15])
        ax_radio_proxy.set_title('Proxy', fontweight='bold')
        self.radio_proxy = RadioButtons(ax_radio_proxy, self.all_proxies, active=self.all_proxies.index(self.proxy))
        self.radio_proxy.on_clicked(self.switch_proxy)
        
        # UI Element: Hole Selector Buttons
        self.hole_names = list(self.builder.holes.keys())
        initial_states = [True] * len(self.hole_names) 
        self.active_holes = set(self.hole_names)
        
        ax_check_hole = plt.axes([0.02, 0.40, 0.12, 0.20])
        ax_check_hole.set_title('Display Holes', fontweight='bold')
        self.check_buttons = CheckButtons(ax_check_hole, self.hole_names, initial_states)
        self.check_buttons.on_clicked(self.toggle_hole)
        
       # UI Element: Y-Axis Offset Textbox
        self.custom_offset = None # Initialize empty custom offset
        ax_offset = plt.axes([0.02, 0.30, 0.12, 0.05])
        ax_offset.set_title('Y-Axis Offset', fontweight='bold', fontsize=10, pad=4)
        self.txt_offset = TextBox(ax_offset, '', initial='') 
        self.txt_offset.on_submit(self.submit_offset)
        
        # UI Element: Tiepoint Tool
        self.show_floating_cores = False 
        ax_anchor = plt.axes([0.20, 0.05, 0.18, 0.05])
        self.btn_anchor = Button(ax_anchor, 'Tiepoint for off-splice core', hovercolor='0.975')
        self.btn_anchor.on_clicked(self.on_anchor_clicked)

        # UI Element: Nudge Tool
        ax_nudge = plt.axes([0.65, 0.05, 0.1, 0.05])
        self.btn_nudge = Button(ax_nudge, 'Manual Nudge')
        self.btn_nudge.on_clicked(self.apply_nudge)
        
        # UI Element: Export & Save Button
        ax_export = plt.axes([0.80, 0.05, 0.15, 0.05])
        self.btn_export = Button(ax_export, 'Export & Save')
        self.btn_export.on_clicked(self.export_and_save)
        
        self.is_dropping_anchor = False
        self.anchor_floating_core = None  
        self.anchor_raw_depth = None      
        
        # Auto-Realign Checkbox
        self.ax_check_align = plt.axes([0.02, 0.05, 0.15, 0.05]) 
        self.check_align = CheckButtons(self.ax_check_align, ['Auto-Realign'], [True])

        self.click_splice = None
        self.click_cand = None
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.update_plots()
        
    def submit_min(self, text):
        try:
            self.view_min = float(text) if text.strip() != '' else None
        except ValueError:
            self.view_min = None
            self.update_plots()

    def submit_max(self, text):
        try:
            self.view_max = float(text) if text.strip() != '' else None
        except ValueError:
            self.view_max = None
        self.update_plots()
        
    def submit_offset(self, text):
        """Overrides the dynamic offset with a user-defined fixed value."""
        try:
            self.custom_offset = float(text) if text.strip() != '' else None
        except ValueError:
            self.custom_offset = None
            print("Invalid offset value entered. Reverting to automatic offset.")
        self.update_plots()

    def switch_proxy(self, label):
        self.proxy = label
        self.clear_clicks()
        self.update_plots()
        
    def toggle_hole(self, label):
        try:
            target_hole = str(label).strip()
            if target_hole in self.active_holes:
                self.active_holes.remove(target_hole)
            else:
                self.active_holes.add(target_hole)
            print(f"UI Update: Toggled '{target_hole}'. Active tracks: {self.active_holes}")
            self.clear_clicks()
            self.update_plots()
        except Exception as e:
            print("Something is wrong!")
            print(f"Error in toggle_hole: {e}")

    def clear_clicks(self):
        self.click_splice = None
        self.click_cand = None

    def update_plots(self):
        self.ax.clear()
        self.ax.set_title(f"Final Splice Review ({self.proxy})", fontweight='bold')
        self.ax.set_xlabel("Composite Depth (MCD)", fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.5) 
        
        splice_df = self.builder.get_splice_dataframe(self.proxy)
        if not splice_df.empty:
            proxy_min = splice_df[self.proxy].min()
            data_range = splice_df[self.proxy].max() - proxy_min
            if self.custom_offset is not None:
                offset_step = self.custom_offset
            else:
                offset_step = data_range * 1.2  
                
            proxy_baseline = proxy_min  
        else:
            offset_step = self.custom_offset if self.custom_offset is not None else 1.0
            proxy_baseline = 0.0
            
            
        self.ax.set_ylabel(f"{self.proxy} (Offset by {offset_step:.1f})", fontweight='bold')

        if not splice_df.empty:
            self.ax.plot(splice_df['MCD'], splice_df[self.proxy], 
                         color='black', lw=1, alpha=0.3, label='Composite Section')
            
            self.ax.text(0.01, proxy_baseline, "Composite", 
                         transform=self.ax.get_yaxis_transform(),
                         fontsize=10, fontweight='bold', color='black',
                         verticalalignment='center', zorder=20,
                         bbox=dict(facecolor='gold', alpha=0.8, edgecolor='black', boxstyle='round,pad=0.4'))

        plotted_labels = set()
        visible_track_idx = 1 
        
        for h_name, hole in self.builder.holes.items():
            if h_name not in self.active_holes:
                continue
                
            hole_offset = visible_track_idx * offset_step
            plotted_anything_for_hole = False  
            current_affine_shift = 0.0
            
            for core in hole.cores:
                is_activated = any(sec.is_locked for sec in core.sections)
                has_custom_shift = any(sec.affine_shift != 0.0 for sec in core.sections)
                
                if is_activated:
                    locked_secs = [s for s in core.sections if s.is_locked]
                    if locked_secs:
                        current_affine_shift = locked_secs[-1].affine_shift
                
                if not is_activated and not has_custom_shift and not getattr(self, 'show_floating_cores', False):
                    continue
                
                core_labeled = False 
                
                for sec in core.sections:
                    if self.proxy not in sec.scaled_data.columns:
                        continue
                        
                    clean = sec.scaled_data.dropna(subset=[self.proxy])
                    if clean.empty: 
                        continue
                    
                    if is_activated or has_custom_shift:
                        applied_shift = sec.affine_shift
                    else:
                        applied_shift = current_affine_shift
                    
                    mcd = (clean['Base_Scaled_Depth'] - getattr(sec, 'original_drilled_top', sec.drilled_top)) * sec.stretch_factor + \
                           getattr(sec, 'original_drilled_top', sec.drilled_top) + applied_shift
                    
                    plot_y = clean[self.proxy] + hole_offset
                    color = 'blue' if sec.is_locked else 'red'
                    label_text = f"On-Splice ({h_name})" if sec.is_locked else f"Off-Splice ({h_name})"
                    
                    if label_text not in plotted_labels:
                        self.ax.plot(mcd, plot_y, color=color, lw=1.2, alpha=0.8, label=label_text)
                        plotted_labels.add(label_text)
                    else:
                        self.ax.plot(mcd, plot_y, color=color, lw=1.2, alpha=0.8)
                        
                    if not core_labeled and not mcd.empty:
                        start_x = mcd.iloc[0]
                        start_y = plot_y.iloc[0]
                        self.ax.text(start_x, start_y + (offset_step * 0.05), f"Core {core.core_id}", 
                                     fontsize=9, fontweight='bold', color='black',
                                     verticalalignment='bottom',
                                     bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
                        core_labeled = True
                        
                    plotted_anything_for_hole = True

            if plotted_anything_for_hole:
                self.ax.text(0.01, hole_offset + proxy_baseline, f"Hole {h_name}", 
                             transform=self.ax.get_yaxis_transform(),
                             fontsize=10, fontweight='bold', color='black',
                             verticalalignment='top', zorder=20,
                             bbox=dict(facecolor='lightgray', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.4'))
                visible_track_idx += 1

        if getattr(self, 'click_splice', None):
            self.ax.axvline(self.click_splice[0], color='black', linestyle='--', alpha=0.6)
            self.ax.plot(self.click_splice[0], self.click_splice[1], 'ks', markersize=7)
            
        if getattr(self, 'click_cand', None):
            self.ax.axvline(self.click_cand[0], color='red', linestyle='--', alpha=0.6)
            self.ax.plot(self.click_cand[0], self.click_cand[1], 'ro', markersize=7) 
            
        if getattr(self, 'click_splice', None) and getattr(self, 'click_cand', None):
            self.ax.plot([self.click_splice[0], self.click_cand[0]], 
                         [self.click_splice[1], self.click_cand[1]], 
                         color='darkorange', linestyle='-', linewidth=2.5, zorder=10)
            
        if getattr(self, 'last_anchor_x', None):
            self.ax.axvline(self.last_anchor_x, color='magenta', linestyle='-.', lw=2, alpha=0.8)
            self.ax.text(self.last_anchor_x, self.ax.get_ylim()[1], ' Anchor Drop ', 
                         color='magenta', rotation=90, verticalalignment='top', 
                         horizontalalignment='right', fontweight='bold')

        self.ax.legend(loc='upper right')
        
        if self.view_min is not None and self.view_max is not None:
            if self.view_min < self.view_max: # Prevent crash if user types min > max
                self.ax.set_xlim(self.view_min, self.view_max)
        
        self.fig.canvas.draw_idle()

    def on_anchor_clicked(self, event):
        self.is_dropping_anchor = not getattr(self, 'is_dropping_anchor', False)
        
        if self.is_dropping_anchor:
            self.show_floating_cores = True
            self.anchor_step = 1           
            self.last_anchor_x = None      
            self.btn_anchor.color = 'yellow'
            print('\n Anchors Away')
            print("\n Anchor Tool Active ")
            print("Step 1: Click a distinct feature on an off-splice core.")
        else:
            self.show_floating_cores = False
            self.anchor_step = 1
            self.last_anchor_x = None
            self.btn_anchor.color = '0.85' 
            print("\n Anchor Tool Canceled ")
            
        self.update_plots()

    def on_click(self, event):
        if event.inaxes != self.ax: return
        if getattr(self.fig.canvas.manager, 'toolbar', None) and self.fig.canvas.manager.toolbar.mode != '': return

        if self.is_dropping_anchor:
            if self.anchor_raw_depth is None:
                self.last_anchor_x = event.xdata
                clicked_core = self.get_core_from_click(event.xdata)
                
                if clicked_core is None:
                    print("Could not identify a core under your click. Why did you click there? Try again.")
                    self.last_anchor_x = None
                    return
                    
                self.anchor_floating_core = clicked_core
                
                clicked_sec = clicked_core.sections[0] 
                for sec in clicked_core.sections:
                    orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    mcd_top = orig_top + sec.affine_shift
                    mcd_bot = (sec.drilled_bottom - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                    if (mcd_top - 0.5) <= event.xdata <= (mcd_bot + 0.5):
                        clicked_sec = sec
                        break
                        
                orig_clicked_top = getattr(clicked_sec, 'original_drilled_top', clicked_sec.drilled_top)
                true_raw_depth = orig_clicked_top + ((event.xdata - clicked_sec.affine_shift - orig_clicked_top) / clicked_sec.stretch_factor)
                
                self.anchor_raw_depth = true_raw_depth
                print(f"Locked onto Core {clicked_core.core_id} at raw depth {self.anchor_raw_depth:.2f}m.")
                print("Click the matching feature on the Master Splice.")
                self.update_plots()
                
            else:
                splice_mcd_depth = event.xdata 
                print(f"Locked Master Splice target at {splice_mcd_depth:.2f}m.")
                manual_anchor_shift = splice_mcd_depth - self.anchor_raw_depth
                
                # handoff to builder.py
                self.builder.snap_floating_core_to_anchor(
                    core=self.anchor_floating_core, 
                    manual_anchor_shift=manual_anchor_shift, 
                    proxy=self.proxy
                )
                
                self.is_dropping_anchor = False
                self.show_floating_cores = False 
                self.anchor_floating_core = None
                self.anchor_raw_depth = None
                self.btn_anchor.color = '0.85' 
                self.last_anchor_x = None
                self.update_plots() 
                print("Tiepoint Added Successfully")
                
            return 

        if event.button == 1: 
            self.click_splice = (event.xdata, event.ydata)
        elif event.button == 3: 
            self.click_cand = (event.xdata, event.ydata)
            
        self.update_plots()

    def get_core_from_click(self, click_depth):
        for h_name, hole in self.builder.holes.items():
            if h_name not in self.active_holes: 
                continue 
                
            for core in hole.cores:
                core_top = min(sec.drilled_top + sec.affine_shift for sec in core.sections)
                core_bottom = max(sec.drilled_bottom + sec.affine_shift for sec in core.sections)
                buffer = 0.5 
                
                if (core_top - buffer) <= click_depth <= (core_bottom + buffer):
                    return core
        return None

    def apply_nudge(self, event):
        if not getattr(self, 'click_splice', None) or not getattr(self, 'click_cand', None):
            print("Error: Missing tie-points. Left-click Master, Right-click Candidate.")
            return
            
        target_mcd = self.click_splice[0]
        cand_mcd = self.click_cand[0]
        shift_delta = target_mcd - cand_mcd
        
        core_to_shift = None
        target_hole_name = ""
        
        for h_name, hole in self.builder.holes.items():
            if h_name not in self.active_holes: continue
            
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked: continue
                    
                    orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    mcd_top = orig_top + sec.affine_shift
                    mcd_bot = (sec.drilled_bottom - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                    
                    if (mcd_top - 0.5) <= cand_mcd <= (mcd_bot + 0.5):
                        core_to_shift = core
                        target_hole_name = h_name
                        break
                if core_to_shift: break
            if core_to_shift: break
            
        if not core_to_shift:
            print("Error: Could not find an unlocked off-splice core at the right-clicked depth.")
            return
            
        print(f"Manual Override: Nudging Hole {target_hole_name}, Core {core_to_shift.core_id} by {shift_delta:+.2f}m")
        unlocked_secs = [s for s in core_to_shift.sections if not s.is_locked]
        
        if unlocked_secs:
            new_anchor_shift = unlocked_secs[0].affine_shift + shift_delta

            if hasattr(self, 'check_align') and self.check_align.get_status()[0]:
                print("Running Auto-Realign around the new nudged position...")
                self.builder.snap_floating_core_to_anchor(
                    core=core_to_shift,
                    manual_anchor_shift=new_anchor_shift,
                    proxy=self.proxy
                )
            else:
                for sec in unlocked_secs:
                    sec.affine_shift = new_anchor_shift
                        
        self.click_splice = None
        self.click_cand = None
        self.update_plots()
        
    def export_and_save(self, event):
        """Passes the current state to the IO handler to generate CSVs."""
        export_project_data(self.builder, self.active_holes, self.all_proxies)
        
class SpliceBuilderGUI:
    def __init__(self, builder, mudline_hole, proxy=None):
        """
        The GUI for building new splices / composite sections.
        """
        self.builder = builder
        self.candidate_hole = list(self.builder.holes.keys())[0]
        self.history = []
        
        self.view_min = None
        self.view_max = None
        
        self.all_proxies = []
        for h in self.builder.holes.values():
            for c in h.cores:
                for p in getattr(c, 'active_proxies', []):
                    if p not in self.all_proxies:
                        self.all_proxies.append(p)
        if not self.all_proxies:
            self.all_proxies = ['Density'] 
            
        self.proxy = proxy if proxy in self.all_proxies else self.all_proxies[0]
        
        mud_hole = self.builder.holes.get(mudline_hole)
        if mud_hole and mud_hole.cores:
            mudline_core = mud_hole.cores[0]
            for sec in mudline_core.sections:
                sec.is_locked = True
                sec.affine_shift = 0.0
                
        self.current_tie_top_mcd = 0.0
        
        self.fig, self.ax = plt.subplots(figsize=(15, 8))
        self.fig.subplots_adjust(left=0.15, bottom=0.25)
        self.fig.canvas.manager.set_window_title('Splice Builder')
        
        ax_radio_proxy = plt.axes([0.02, 0.65, 0.1, 0.15])
        ax_radio_proxy.set_title('Proxy', fontweight='bold')
        active_idx = self.all_proxies.index(self.proxy) if self.proxy in self.all_proxies else 0
        self.radio_proxy = RadioButtons(ax_radio_proxy, self.all_proxies, active=active_idx)
        self.radio_proxy.on_clicked(self.switch_proxy)
        
        ax_radio_hole = plt.axes([0.02, 0.25, 0.1, 0.15])
        ax_radio_hole.set_title('Hole', fontweight='bold')
        self.radio_hole = RadioButtons(ax_radio_hole, list(self.builder.holes.keys()))
        self.radio_hole.on_clicked(self.switch_candidate)
        
        self.show_photos = False
        ax_check_photo = plt.axes([0.02, 0.15, 0.1, 0.05])
        self.check_photo = CheckButtons(ax_check_photo, ['Show Photos'], [False])
        self.check_photo.on_clicked(self.toggle_photos)
        
        # Depth Controls
        ax_min = plt.axes([0.25, 0.05, 0.08, 0.05])
        self.txt_min = TextBox(ax_min, 'Min: ', initial='')
        self.txt_min.on_submit(self.submit_min)

        ax_max = plt.axes([0.42, 0.05, 0.08, 0.05])
        self.txt_max = TextBox(ax_max, 'Max: ', initial='')
        self.txt_max.on_submit(self.submit_max)
        
        # Action Buttons
        ax_undo = plt.axes([0.55, 0.05, 0.1, 0.05])
        self.btn_undo = Button(ax_undo, 'Undo')
        self.btn_undo.on_clicked(self.apply_undo)
        
        ax_tie = plt.axes([0.7, 0.05, 0.1, 0.05])
        self.btn_tie = Button(ax_tie, 'Tie & Snip')
        self.btn_tie.on_clicked(self.apply_tie)
        
        ax_finalize = plt.axes([0.85, 0.05, 0.1, 0.05])
        self.btn_finalize = Button(ax_finalize, 'Finalize')
        self.btn_finalize.on_clicked(self.finalize)
        
        self.click_splice = None
        self.click_cand = None
        self.line_splice = None
        self.line_cand = None
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.update_plots()
        plt.show(block=True)

    def submit_min(self, text):
        try:
            self.view_min = float(text) if text.strip() != '' else None
        except ValueError:
            self.view_min = None
        self.update_plots()

    def submit_max(self, text):
        try:
            self.view_max = float(text) if text.strip() != '' else None
        except ValueError:
            self.view_max = None
        self.update_plots()
        
    def switch_proxy(self, label):
        self.proxy = label
        self.clear_active_clicks()
        self.update_plots()
        
    def switch_candidate(self, label):
        self.candidate_hole = label
        self.clear_active_clicks()
        self.update_plots()
        
    def clear_active_clicks(self):
        self.click_splice = None
        self.click_cand = None
        self.line_splice = None
        self.line_cand = None
        
    def toggle_photos(self, label):
        self.show_photos = not self.show_photos
        self.update_plots()

    def update_plots(self):
        self.ax.clear()
        
        self.ax.set_title(f"Correlation View: Master Splice vs Hole {self.candidate_hole} - {self.proxy}", fontweight='bold')
        self.ax.set_ylabel(self.proxy)
        self.ax.set_xlabel("MCD (m)")
        self.ax.grid(True, linestyle='--', alpha=0.5)

        # Build Composite Section / Splice from currently locked sections. Iterates every time the plot is updated.
        locked_chunks = []
        for h_name, hole in self.builder.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked and self.proxy in sec.scaled_data.columns:
                        clean = sec.scaled_data.dropna(subset=[self.proxy]).copy()
                        clean = clean[(clean['Base_Scaled_Depth'] >= sec.drilled_top) & 
                                      (clean['Base_Scaled_Depth'] <= sec.drilled_bottom)]
                        if not clean.empty:
                            mcd = (clean['Base_Scaled_Depth'] - getattr(sec, 'original_drilled_top', sec.drilled_top)) * sec.stretch_factor + getattr(sec, 'original_drilled_top', sec.drilled_top) + sec.affine_shift
                            locked_chunks.append(pd.DataFrame({'MCD': mcd, self.proxy: clean[self.proxy]}))

        if locked_chunks:
            splice_df = pd.concat(locked_chunks, ignore_index=True).sort_values('MCD')
        else:
            splice_df = pd.DataFrame(columns=['MCD', self.proxy])

        # Calculate Ranges & Offsets
        master_min = splice_df[self.proxy].min() if not splice_df.empty else 0
        master_max = splice_df[self.proxy].max() if not splice_df.empty else 1
        master_range = master_max - master_min if not splice_df.empty else 1

        cand_hole = self.builder.holes[self.candidate_hole]
        all_proxy_data = []
        for core in cand_hole.cores:
            for sec in core.sections:
                if self.proxy in sec.scaled_data.columns:
                    all_proxy_data.append(sec.scaled_data[self.proxy].dropna())
                    
        cand_range = 0
        if all_proxy_data:
            full_series = pd.concat(all_proxy_data)
            cand_range = full_series.max() - full_series.min()

        self.proxy_range = max(master_range, cand_range)
        if self.proxy_range == 0: self.proxy_range = 1
        
        self.y_offset = 1.1 * self.proxy_range 

        # Composite Section / Splice photo scale constraints
        master_median = splice_df[self.proxy].median() if not splice_df.empty else 0
        master_y_half = (master_range * 0.5) if master_range > 0 else 0.5

        # Candidate borehole photo scale constraints
        if all_proxy_data:
            cand_median = full_series.median() - self.y_offset
            cand_y_half = (cand_range * 0.5) if cand_range > 0 else 0.5
        else:
            cand_median = -self.y_offset
            cand_y_half = 0.5

        # Plot Composite Section / Splice & Photos
        if not splice_df.empty:
            self.ax.plot(splice_df['MCD'], splice_df[self.proxy], color='black', linewidth=1.5, label='Master Splice', zorder=3)
            
            if self.show_photos: 
                for h_name, hole in self.builder.holes.items():
                    for core in hole.cores:
                        for sec in core.sections:
                            if sec.is_locked and getattr(core, 'photo_array', None) is not None:
                                mcd_top = getattr(sec, 'original_drilled_top', sec.drilled_top) + sec.affine_shift
                                mcd_bot = (sec.drilled_bottom - getattr(sec, 'original_drilled_top', sec.drilled_top)) * sec.stretch_factor + getattr(sec, 'original_drilled_top', sec.drilled_top) + sec.affine_shift
                            
                                # Force slice_photo to grab the correct part of the photo
                                sliced_img = self.slice_photo(core, getattr(sec, 'original_drilled_top', sec.drilled_top), sec.drilled_bottom, affine_shift=0)

                                # Calculate the scaled layout for the graph
                                mcd_sec_top = getattr(sec, 'original_drilled_top', sec.drilled_top) + sec.affine_shift
                                mcd_sec_bot = (sec.drilled_bottom - getattr(sec, 'original_drilled_top', sec.drilled_top)) * sec.stretch_factor + getattr(sec, 'original_drilled_top', sec.drilled_top) + sec.affine_shift

                                # Use Matplotlib to stretch and map the pixels to the data
                            
                                if sliced_img is not None and sliced_img.size > 0:
                                    self.ax.imshow(
                                        sliced_img, 
                                        extent=[mcd_top, mcd_bot, master_median - master_y_half, master_median + master_y_half], 
                                        aspect='auto', 
                                        alpha=0.85, 
                                        zorder=1
                                    )

        # Plot Candidate Hole Cores & Photos
        # Okabe-Ito colorblind-friendly palette. Each core is a different color to help differentiate them.
        colors = itertools.cycle(['#E69F00', '#56B4E9', '#009E73', '#0072B2', '#D55E00', '#CC79A7'])
        
        for core in cand_hole.cores:
            color = next(colors)
            core_mcd_vals = []
            core_y_vals = []
            
            for sec in core.sections:
                if sec.is_locked: continue
                if self.proxy not in sec.scaled_data.columns: continue
                
                # Plot the photo as layer 1
                if self.show_photos and getattr(core, 'photo_array', None) is not None:
                    affine_shift = getattr(sec, 'affine_shift', 0.0)
                    stretch_factor = getattr(sec, 'stretch_factor', 1.0)
    
                    mcd_sec_top = sec.drilled_top + affine_shift
                    mcd_sec_bot = (sec.drilled_bottom - sec.drilled_top) * stretch_factor + getattr(sec, 'original_drilled_top', sec.drilled_top) + affine_shift
    
                    sliced_img = self.slice_photo(core, getattr(sec, 'original_drilled_top', sec.drilled_top), sec.drilled_bottom, affine_shift=0)
    
                    if sliced_img is not None and sliced_img.size > 0:
                        self.ax.imshow(
                            sliced_img, 
                            extent=[mcd_sec_top, mcd_sec_bot, cand_median - cand_y_half, cand_median + cand_y_half], 
                            aspect='auto', 
                            alpha=0.85, 
                            zorder=1
                        )
                
                # Data filtering prior to plotting overtop the photo
                clean = sec.scaled_data.dropna(subset=[self.proxy])
                clean = clean[(clean['Base_Scaled_Depth'] >= getattr(sec, 'original_drilled_top', sec.drilled_top)) & 
                              (clean['Base_Scaled_Depth'] <= sec.drilled_bottom)]
                
                if clean.empty: continue 
                
                # Calculate the MCD for the data
                mcd = (clean['Base_Scaled_Depth'] - getattr(sec, 'original_drilled_top', sec.drilled_top)) * sec.stretch_factor + getattr(sec, 'original_drilled_top', sec.drilled_top) + sec.affine_shift
                offset_y = clean[self.proxy] - self.y_offset
                
                self.ax.plot(mcd, offset_y, color=color, linewidth=1.2, zorder=3)
                
                core_mcd_vals.extend(mcd.tolist())
                core_y_vals.extend(offset_y.tolist())
                
            if core_mcd_vals:
                mid_idx = len(core_mcd_vals) // 2
                self.ax.text(core_mcd_vals[mid_idx], core_y_vals[mid_idx] + (self.proxy_range * 0.1), 
                             f"C{core.core_id}", fontsize=10, color=color, fontweight='bold',
                             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1.5))

        # Draw the vertical dashed line showing where user clicks place tiepoints
        if getattr(self, 'click_splice', None):
            self.ax.axvline(self.click_splice[0], color='black', linestyle='--', alpha=0.7)
        if getattr(self, 'click_cand', None):
            self.ax.axvline(self.click_cand[0], color='red', linestyle='--', alpha=0.7)
            
        self.ax.legend(loc='upper right')

        # Prevent shenanigans with the y-axis
        y_low = master_min
        y_high = master_max
        if all_proxy_data:
            cand_raw_min = full_series.min() - self.y_offset
            cand_raw_max = full_series.max() - self.y_offset
            y_low = min(y_low, cand_raw_min)
            y_high = max(y_high, cand_raw_max)
            
        y_pad = (y_high - y_low) * 0.1
        if y_pad == 0: y_pad = 1
        self.ax.set_ylim(y_low - y_pad, y_high + y_pad)

        # Draw x-axis with the user-defined depth limits from the text boxes
        if self.view_min is not None and self.view_max is not None:
            if self.view_min < self.view_max:
                self.ax.set_xlim(self.view_min, self.view_max)

        self.fig.canvas.draw_idle()
        
    def on_click(self, event):
        if event.inaxes != self.ax: return
        if self.fig.canvas.manager.toolbar.mode != '': return
        
        if event.button == 1:
            self.click_splice = (event.xdata, event.ydata)
            print(f"Tiepoint set at {event.xdata:.2f}m")
            self.update_plots()
            
        elif event.button == 3:
            if not self.click_splice:
                print("Please Left-Click to set the Master Splice anchor first!")
                return
            self.click_cand = (event.xdata, event.ydata)
            print(f"Candidate tiepoint set at {event.xdata:.2f}m")
            self.apply_tie(event)
                
    def apply_undo(self, event):
        if not self.history:
            print("Nothing to undo dog. You haven't done a thing!")
            return
            
        print("Undoing last action...")
        last_state = self.history.pop()
        self.builder.__dict__.update(copy.deepcopy(last_state).__dict__)
        
        self.clear_active_clicks()
        self.update_plots()

    def apply_tie(self, event):
        if not self.click_splice or not self.click_cand:
            print("Need both a Master Splice click and a Candidate click to tie.")
            return
            
        self.history.append(copy.deepcopy(self.builder))
            
        splice_mcd = self.click_splice[0]
        cand_depth = self.click_cand[0]
        cand_y = self.click_cand[1] 
        
        # Cut the prior temporary composite section at the tiepoint and remove the data that is below the tiepoint
        master_tied = False
        for h_name, hole in self.builder.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked:
                        vis_top = sec.drilled_top + sec.affine_shift
                        vis_bot = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                        
                        if vis_top <= splice_mcd <= vis_bot:
                            relative_mcd = splice_mcd - sec.affine_shift - sec.drilled_top
                            raw_cut_depth = sec.drilled_top + (relative_mcd / sec.stretch_factor)
                            
                            rel_start_mcd = getattr(self, 'current_tie_top_mcd', 0.0) - sec.affine_shift - sec.drilled_top
                            raw_start_depth = sec.drilled_top + (rel_start_mcd / sec.stretch_factor)

                            self.builder.splice.append_tie(
                                top_mcd=getattr(self, 'current_tie_top_mcd', 0.0),
                                bot_mcd=splice_mcd,
                                hole_name=h_name,
                                core_id=core.core_id,
                                top_drilled=raw_start_depth, 
                                bot_drilled=raw_cut_depth
                            )
                            
                            self.current_tie_top_mcd = splice_mcd
                            
                            # Removing the data below the tiepoint
                            orig_bot = sec.drilled_bottom
                            sec.drilled_bottom = raw_cut_depth
                            if not sec.scaled_data.empty:
                                sec.scaled_data = sec.scaled_data[sec.scaled_data['Base_Scaled_Depth'] <= raw_cut_depth].copy()
                            
                            # Change status of sections below the tiepoint to unlocked
                            for s2 in core.sections:
                                if s2 != sec and s2.drilled_top >= raw_cut_depth:
                                    s2.is_locked = False
                                    
                            master_tied = True
                            break
                if master_tied: break
            if master_tied: break

        # Tie in the candidate core at the tiepoint to the Master Splice
        # Change the status of the sections below the tiepoint to on-splice
        cand_hole = self.builder.holes[self.candidate_hole]
        best_core = None
        best_sec = None
        best_vis_top = 0
        min_y_dist = float('inf')
        
        for core in cand_hole.cores:
            for sec in core.sections:
                if sec.is_locked: continue
                
                vis_top = sec.drilled_top + sec.affine_shift
                vis_bot = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                
                if (vis_top - 0.5) <= cand_depth <= (vis_bot + 0.5):
                    clean = sec.scaled_data.dropna(subset=[self.proxy])
                    if not clean.empty:
                        mcd_array = (clean['Base_Scaled_Depth'] - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                        idx = (np.abs(mcd_array - cand_depth)).argmin()
                        plotted_y = clean[self.proxy].iloc[idx] - self.y_offset
                        
                        y_dist = abs(plotted_y - cand_y)
                        if y_dist < min_y_dist:
                            min_y_dist = y_dist
                            best_core = core
                            best_sec = sec
                            best_vis_top = vis_top
                            
        if best_core and best_sec:
            relative_depth = cand_depth - best_vis_top
            unstretched_relative_depth = relative_depth / best_sec.stretch_factor
            raw_click_depth = best_sec.drilled_top + unstretched_relative_depth
            
            new_shift = splice_mcd - (raw_click_depth - best_sec.drilled_top) * best_sec.stretch_factor - best_sec.drilled_top
            delta_shift = new_shift - best_sec.affine_shift
            
            print(f"Appending Hole {self.candidate_hole}, Core {best_core.core_id}. (Cascading {delta_shift:+.2f}m downhole)")
            
            # Propogate the affine shift to all subsequent unlocked cores/sections in candidate hole
            original_drilled_top = best_core.drilled_top
            for c2 in cand_hole.cores:
                if c2.drilled_top >= original_drilled_top:
                    for s2 in c2.sections:
                        if not s2.is_locked:
                            s2.affine_shift += delta_shift

            orig_top = best_sec.drilled_top
            orig_bot = best_sec.drilled_bottom
            
            # Keep the portion of the candidate core above the tiepoint as off-splice
            # These points stay in the candidate hole track
            if raw_click_depth > orig_top:
                upper_sec = copy.deepcopy(best_sec)
                upper_sec.drilled_top = orig_top
                upper_sec.drilled_bottom = raw_click_depth
                upper_sec.is_locked = False
                if not upper_sec.scaled_data.empty:
                    upper_sec.scaled_data = upper_sec.scaled_data[
                        (upper_sec.scaled_data['Base_Scaled_Depth'] >= orig_top) & 
                        (upper_sec.scaled_data['Base_Scaled_Depth'] <= raw_click_depth)
                    ].copy()
                sec_idx = best_core.sections.index(best_sec)
                best_core.sections.insert(sec_idx, upper_sec)

            # Move the portion of the candidate core above the tiepoint to the Composite Section / Splice
            if not hasattr(best_sec, 'original_drilled_top'):
                best_sec.original_drilled_top = best_sec.drilled_top
            best_sec.drilled_top = raw_click_depth
            best_sec.drilled_bottom = orig_bot
            best_sec.is_locked = True
            
            if not best_sec.scaled_data.empty:
                best_sec.scaled_data = best_sec.scaled_data[
                    (best_sec.scaled_data['Base_Scaled_Depth'] >= raw_click_depth) & 
                    (best_sec.scaled_data['Base_Scaled_Depth'] <= orig_bot)
                ].copy()

            # Cores below the tiepoint become locked, until the next tiepoint is added
            for s2 in best_core.sections:
                if s2 != best_sec and s2.drilled_top >= raw_click_depth:
                    s2.is_locked = True

        else:
            print("Warning: Could not find a valid core trace near that click.")
            
        self.clear_active_clicks()
        self.update_plots()
        self.fig.canvas.draw_idle()
        
    def slice_photo(self, core, req_top, req_bot, affine_shift=0):
        """
        Slices core.photo_array between req_top and req_bot (drilled/mbsf depth),
        derives core bounds from core.sections if explicit attributes are missing,
        and guarantees depth is along axis 1 (horizontal) for Matplotlib extent.
        """
        if not hasattr(core, 'photo_array') or core.photo_array is None:
            return None

        photo_arr = core.photo_array

        # c_top is the topmost depth mbsf corresponding to the top of the core photo
        c_top = getattr(core, 'drilled_top', getattr(core, 'top_depth', None))
        if c_top is None and hasattr(core, 'sections') and core.sections:
            c_top = min(getattr(s, 'original_drilled_top', s.drilled_top) for s in core.sections)

        # Physical bottom of recovered core
        if hasattr(core, 'scaled_data') and core.scaled_data is not None and not core.scaled_data.empty:
            c_bot = core.scaled_data['Base_Scaled_Depth'].max()
        elif hasattr(core, 'sections') and core.sections:
            c_bot = max(getattr(s, 'original_drilled_bottom', s.drilled_bottom) for s in core.sections)
        else:
            c_bot = getattr(core, 'drilled_bottom', getattr(core, 'bot_depth', None))

        # Calculate depth interval based on the affine shift 
        raw_top = req_top - affine_shift
        raw_bot = req_bot - affine_shift
        total_len = c_bot - c_top

        overlap_top = max(raw_top, c_top)
        overlap_bot = min(raw_bot, c_bot)

        if overlap_top >= overlap_bot or total_len <= 0:
            return None

        f_top = max(0.0, min(1.0, (overlap_top - c_top) / total_len))
        f_bot = max(0.0, min(1.0, (overlap_bot - c_top) / total_len))

        # slice and rotate so depth is plotted on the x-axis
        if photo_arr.shape[0] > photo_arr.shape[1]:  # Vertical array (Depth = axis 0)
            y_start = int(f_top * photo_arr.shape[0])
            y_end = int(f_bot * photo_arr.shape[0])
            if y_start >= y_end:
                return None
        
            sliced = photo_arr[y_start:y_end, :, :]
            sliced = np.rot90(sliced, -1)
        
        else:  # Horizontal array (Depth = axis 1)
            x_start = int(f_top * photo_arr.shape[1])
            x_end = int(f_bot * photo_arr.shape[1])
            if x_start >= x_end:
                return None
        
            sliced = photo_arr[:, x_start:x_end, :]

        return sliced
    
    def export_composite_photo(self, filename="Master_Splice_Composite.pdf"):
        print("Generating composite PDF with depth track...")
    
        # Gather the locked sections
        locked_sections = []
        for h_name, hole in self.builder.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked and getattr(core, 'photo_array', None) is not None:
                        orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                        
                        # Use the stored MCD depth bounds, use the MCD equation if they were not stored properly
                        mcd_top = getattr(sec, 'splice_top_mcd', (sec.drilled_top - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift)
                        mcd_bot = getattr(sec, 'splice_bot_mcd', (sec.drilled_bottom - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift)
                        
                        locked_sections.append((mcd_top, mcd_bot, core, sec))
                    
        if not locked_sections:
            print("No photos found on the master splice to export.")
            return
        
        # Cores by depth so they render in the correct order
        locked_sections.sort(key=lambda x: x[0])
    
        # Build figure for the export
        fig, ax = plt.subplots(figsize=(24, 4))
    
        min_mcd = float('inf')
        max_mcd = float('-inf')
    
        # Plot each photo slice into the figure at its MCD coordinates
        for mcd_top, mcd_bot, core, sec in locked_sections:
            sliced = self.slice_photo(core, sec.drilled_top, sec.drilled_bottom, affine_shift=0)
        
            if sliced is not None and sliced.size > 0:
                ax.imshow(sliced, extent=[mcd_top, mcd_bot, 0, 1], aspect='auto')
                min_mcd = min(min_mcd, mcd_top)
                max_mcd = max(max_mcd, mcd_bot)
            
            if min_mcd == float('inf'):
                print("Failed to slice any valid photos.")
                plt.close(fig)
                return
        
        # Format axes: included to make it straightforward to include the photo in figures 
        # that are edited in Illustrator
        ax.set_xlim(min_mcd, max_mcd)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
    
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_linewidth(1.5)
    
        ax.tick_params(axis='x', which='major', labelsize=11, length=6, width=1.2, direction='out')
        ax.tick_params(axis='x', which='minor', length=3.5, width=0.8, direction='out')
        ax.xaxis.set_minor_locator(plt.AutoMinorLocator())
    
        ax.set_xlabel("Composite Depth (MCD) [m]", fontweight='bold', fontsize=12, labelpad=8)
    
        try:
            fig.savefig(filename, format='pdf', bbox_inches='tight', dpi=300)
            print(f"SUCCESS: Master Splice PDF saved to {filename}")
        except Exception as e:
            print(f"Error saving PDF: {e}")
        finally:
            plt.close(fig)
        
    def finalize(self, event):
        deepest_bot_mcd = 0.0
        final_core = None
        final_hole = None
        final_bot_drilled = 0.0

        for h_name, hole in self.builder.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked:
                        orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                        # Calculate composite depth for the final core
                        bot_mcd = getattr(
                            sec, 
                            'splice_bot_mcd', 
                            (sec.drilled_bottom - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                        )
                        
                        if bot_mcd > deepest_bot_mcd:
                            deepest_bot_mcd = bot_mcd
                            final_core = core
                            final_hole = h_name
                            final_bot_drilled = sec.drilled_bottom

        if final_core:
            raw_start = final_core.drilled_top
            for sec in final_core.sections:
                if sec.is_locked:
                    orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    mcd_top = getattr(
                        sec, 
                        'splice_top_mcd', 
                        (sec.drilled_top - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                    )
                    
                    if mcd_top <= getattr(self, 'current_tie_top_mcd', 0.0):
                        rel_mcd = getattr(self, 'current_tie_top_mcd', 0.0) - sec.affine_shift - orig_top
                        raw_start = orig_top + (rel_mcd / sec.stretch_factor)
                        break

            self.builder.splice.append_tie(
                top_mcd=getattr(self, 'current_tie_top_mcd', 0.0),
                bot_mcd=deepest_bot_mcd,
                hole_name=final_hole,
                core_id=final_core.core_id,
                top_drilled=raw_start,
                bot_drilled=final_bot_drilled
            )

        print("Finalizing Composite. Proceeding to align off-splice core sections.")
        
        # Call comosite photo export
        self.export_composite_photo()
        
        plt.close(self.fig)