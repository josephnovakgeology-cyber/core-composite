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
        
        # Build UI Canvas
        self.fig, self.ax = plt.subplots(figsize=(15, 8))
        self.fig.canvas.manager.set_window_title('Multi-Track Alignment')
        plt.subplots_adjust(left=0.18, bottom=0.15)
        
        # UI Element: Adjusted Depth Window Controls (TextBoxes)
        ax_min = plt.axes([0.42, 0.05, 0.08, 0.05])
        self.txt_min = TextBox(ax_min, 'Min: ', initial='')
        self.txt_min.on_submit(self.submit_min)

        ax_max = plt.axes([0.55, 0.05, 0.08, 0.05])
        self.txt_max = TextBox(ax_max, 'Max: ', initial='')
        self.txt_max.on_submit(self.submit_max)
        
        # UI Element: Proxy RadioButtons
        ax_radio_proxy = plt.axes([0.02, 0.65, 0.12, 0.15])
        ax_radio_proxy.set_title('Proxy', fontweight='bold')
        self.radio_proxy = RadioButtons(ax_radio_proxy, self.all_proxies, active=self.all_proxies.index(self.proxy))
        self.radio_proxy.on_clicked(self.switch_proxy)
        
        # UI Element: Hole CheckButtons
        self.hole_names = list(self.builder.holes.keys())
        initial_states = [True] * len(self.hole_names) 
        self.active_holes = set(self.hole_names)
        
        ax_check_hole = plt.axes([0.02, 0.40, 0.12, 0.20])
        ax_check_hole.set_title('Display Holes', fontweight='bold')
        self.check_buttons = CheckButtons(ax_check_hole, self.hole_names, initial_states)
        self.check_buttons.on_clicked(self.toggle_hole)
        
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
        
        # Auto-Realign Checkbox UI
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
            offset_step = data_range * 1.2  
            proxy_baseline = proxy_min  # Captures the baseline data shift
        else:
            offset_step = 1.0
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
                    
                    mcd = (clean['Base_Scaled_Depth'] - sec.drilled_top) * sec.stretch_factor + \
                           sec.drilled_top + applied_shift
                    
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
                    print("Could not identify a core under your click. Try again.")
                    self.last_anchor_x = None
                    return
                    
                self.anchor_floating_core = clicked_core
                
                clicked_sec = clicked_core.sections[0] 
                for sec in clicked_core.sections:
                    mcd_top = sec.drilled_top + sec.affine_shift
                    mcd_bot = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                    if (mcd_top - 0.5) <= event.xdata <= (mcd_bot + 0.5):
                        clicked_sec = sec
                        break
                        
                true_raw_depth = clicked_sec.drilled_top + ((event.xdata - clicked_sec.affine_shift - clicked_sec.drilled_top) / clicked_sec.stretch_factor)
                
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
                    
                    mcd_top = sec.drilled_top + sec.affine_shift
                    mcd_bot = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                    
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
                # HANDOFF TO BUILDER!
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
    def __init__(self, builder, mudline_hole, proxy= None):
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
                
        self.fig, self.ax = plt.subplots(figsize=(15, 8))
        self.fig.subplots_adjust(left=0.15, bottom=0.25) # Leaves room for buttons
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
        
        # Adjusted Depth Window Controls (TextBoxes)
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

    # Callbacks for the TextBoxes
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

    def get_cumulative_growth(self):
        """
        Helper function for applying the affine shifts down each hole.
        """
        cumulative_growth = 0.0
        locked_sections = []
        for h_name, hole in self.builder.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked:
                        locked_sections.append(sec)
        if locked_sections:
            locked_sections.sort(key=lambda x: x.scaled_data['Base_Scaled_Depth'].max())
            deepest_locked = locked_sections[-1]
            if hasattr(deepest_locked, 'affine_shift'):
                cumulative_growth = deepest_locked.affine_shift
        return cumulative_growth

    def update_plots(self):
        self.ax.clear()
        
        self.ax.set_title(f"Correlation View: Master Splice vs Hole {self.candidate_hole} - {self.proxy}", fontweight='bold')
        self.ax.set_ylabel(self.proxy)
        self.ax.set_xlabel("MCD (m)")
        self.ax.grid(True, linestyle='--', alpha=0.5)

        # Calculate 1.5x Y-offset
        splice_df = self.builder.get_splice_dataframe(self.proxy)
        master_range = 0
        if not splice_df.empty:
            master_range = splice_df[self.proxy].max() - splice_df[self.proxy].min()

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
        
        self.y_offset = 1.5 * self.proxy_range 

        # Plot Master Splice
        if not splice_df.empty:
            self.ax.plot(splice_df['MCD'], splice_df[self.proxy], color='black', linewidth=1.5, label='Master Splice')

        # Plot Candidate Hole
        # Palette: Orange, Sky Blue, Bluish Green, Blue, Vermillion, Reddish Purple
        colors = itertools.cycle(['#E69F00', '#56B4E9', '#009E73', '#0072B2', '#D55E00', '#CC79A7'])
        
        for core in cand_hole.cores:
            color = next(colors)
            core_mcd_vals = []
            core_y_vals = []
            
            for sec in core.sections:
                if sec.is_locked: continue
                if self.proxy not in sec.scaled_data.columns: continue
                
                clean = sec.scaled_data.dropna(subset=[self.proxy])
                if clean.empty: continue
                
                mcd = (clean['Base_Scaled_Depth'] - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                offset_y = clean[self.proxy] - self.y_offset
                
                self.ax.plot(mcd, offset_y, color=color, linewidth=1.2)
                
                core_mcd_vals.extend(mcd.tolist())
                core_y_vals.extend(offset_y.tolist())
                
            if core_mcd_vals:
                mid_idx = len(core_mcd_vals) // 2
                self.ax.text(core_mcd_vals[mid_idx], core_y_vals[mid_idx] + (self.proxy_range * 0.1), 
                             f"C{core.core_id}", fontsize=10, color=color, fontweight='bold',
                             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1.5))

        # Draw Clicks
        if getattr(self, 'click_splice', None):
            self.ax.axvline(self.click_splice[0], color='black', linestyle='--', alpha=0.7)
        if getattr(self, 'click_cand', None):
            self.ax.axvline(self.click_cand[0], color='red', linestyle='--', alpha=0.7)
            
        self.ax.legend(loc='upper right')

        # Apply Custom Depth Limits if Provided
        if self.view_min is not None and self.view_max is not None:
            if self.view_min < self.view_max: # Prevent crash if user types min > max
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
            print("Nothing to undo dog.")
            return
            
        print("Undoing last action...")
        last_state = self.history.pop()
        
        #  Update the internal dictionary of the original builder object in-place
        # This prevents the main script from losing the reference.
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
        
        for h_name, hole in self.builder.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked:
                        vis_top = sec.drilled_top + sec.affine_shift
                        vis_bot = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                        if vis_top <= splice_mcd <= vis_bot:
                            core.apply_splice_cut(splice_mcd)
                            break

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
                            
        if best_core:
            relative_depth = cand_depth - best_vis_top
            unstretched_relative_depth = relative_depth / best_sec.stretch_factor
            raw_click_depth = best_sec.drilled_top + unstretched_relative_depth
            
            new_shift = splice_mcd - (raw_click_depth - best_sec.drilled_top) * best_sec.stretch_factor - best_sec.drilled_top
            delta_shift = new_shift - best_sec.affine_shift
            
            print(f"Appending Hole {self.candidate_hole}, Core {best_core.core_id}. (Cascading {delta_shift:+.2f}m downhole)")
            
            original_drilled_top = best_core.drilled_top
            for c2 in cand_hole.cores:
                if c2.drilled_top >= original_drilled_top:
                    for s2 in c2.sections:
                        if not s2.is_locked:
                            s2.affine_shift += delta_shift
                            
            best_core.apply_candidate_cut(raw_click_depth)
        else:
            print(f"Warning: Could not find a valid core trace near that click.")
                
        self.clear_active_clicks()
        self.update_plots()
        self.fig.canvas.draw_idle()
        
    def finalize(self, event):
        """
        Closes the GUI window to allow the main script to proceed align off-splice core sections.
        """
        print("Finalizing Composite. Proceeding to align off-splice core sections.")
        plt.close(self.fig)