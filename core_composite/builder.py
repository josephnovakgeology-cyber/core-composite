# -*- coding: utf-8 -*-
"""
Created on Fri May  1 06:47:58 2026

@author: joseph novak

CompositeBuilder algorithm -> note that the heavy math is in alignment.py
"""

import pandas as pd
import numpy as np
import matplotlib
try:
    matplotlib.use('Qt5Agg') 
except:
    pass
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from scipy.stats import pearsonr
import copy
import re
from .models import SpliceRecord

class CompositeBuilder:
    """
    The CompositeBuilder class holds all of the functions that handle the automated alignment of off-splice 
    core sections to the main splice. 

    The equations in this class are described in Methods section 2.2 of the manuscript 
    
    Definitions below.
    """
    def __init__(self):
        self.holes = {}
        self.splice = SpliceRecord()

    def add_hole(self, hole):
        self.holes[hole.hole_name] = hole
        
    def get_splice_dataframe(self, proxy):
        """
        Compiles all locked sections into a single DataFrame.
        
        The output from this function is the off-splice data aligned to the composite section.
        """
        depths, vals = [], []
        
        for hole in self.holes.values():
            for core in hole.cores:
                for sec in core.sections:
                    if sec.is_locked and proxy in sec.scaled_data.columns:
                        clean = sec.scaled_data.dropna(subset=[proxy])
                        if not clean.empty:
                            mcd = (clean['Base_Scaled_Depth'] - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                            depths.extend(mcd.values)
                            vals.extend(clean[proxy].values)
                            
        if not depths:
            return pd.DataFrame()
            
        return pd.DataFrame({'MCD': depths, proxy: vals}).sort_values('MCD')
                   
        
    def optimize_off_splice(self, proxy='auto', str_range=(0.70, 1.05), str_step=0.01,stretch_penalty = 0.1, plot_results=True):
        """
        Uses on-splice sections as tiepoints to constrain micro-scale grid searches.
        Grid searches are optimized based on penalized Pearson correlation values.
        Generates a correlation plot upon completion.
        
        Note: the grid search algorithm was moved and is called as another function here
        because there were too many for loops and I got confused. The grid search is done by
        the optimize_single_section function.
        """
        
        print(f"Starting Automated Alignment (Target Proxy: {proxy})")
        
        def get_snr(vals):
            clean_vals = vals[~np.isnan(vals)]
            if len(clean_vals) < 15: return 0.0
            smoothed = savgol_filter(clean_vals, 15, 3)
            noise = clean_vals - smoothed
            var_noise = np.var(noise)
            if var_noise < 1e-8: return 0.0
            return np.var(smoothed) / var_noise

        all_proxies = set()
        for h in self.holes.values():
            for c in h.cores:
                all_proxies.update(c.active_proxies)
        all_proxies = list(all_proxies)

        if proxy != 'auto' and proxy not in all_proxies:
            print(f"Error: '{proxy}' not found. Available: {all_proxies}")
            return

        splices = {}
        for p in all_proxies:
            df = self.get_splice_dataframe(p)
            if not df.empty:
                splices[p] = df.dropna(subset=[p, 'MCD']).sort_values('MCD')

        # Keep track of the primary proxy used for plotting at the end
        plot_proxy = proxy if proxy != 'auto' else (all_proxies[0] if all_proxies else None)

        # List to store successful chunk correlation scores
        alignment_scores = []

        for h_name, hole in self.holes.items():
            print(f"\nOptimizing Hole {h_name}...")
            
            for core in hole.cores:
                has_locked = any(s.is_locked for s in core.sections)
                has_unlocked = any(not s.is_locked for s in core.sections)
                
                if not (has_locked and has_unlocked):
                    continue 
                
                # Calculate the affine shift from the on-splice sections
                locked_shifts = [s.affine_shift for s in core.sections if s.is_locked]
                anchor_shift = sum(locked_shifts) / len(locked_shifts)
                
                unlocked_secs = [s for s in core.sections if not s.is_locked]
                if not unlocked_secs: continue
                    
                print(f"Correlating Core {core.core_id} ({len(unlocked_secs)} unlocked sections, Affine shift: {anchor_shift:+.2f}m)...")
                
                for sec in unlocked_secs:
                    # When proxy is set to "auto", this code uses the signal-to-noise ratio of the
                    # physical properties / colorimetry data to determine the best one to use for automatic
                    # correlation for a given chunk
                    best_proxy = proxy
                    if proxy == 'auto':
                        best_snr = -1.0
                        for p in all_proxies:
                            if p not in splices or p not in sec.scaled_data.columns: continue
                            clean_data = sec.scaled_data[p].dropna().values
                            if len(clean_data) > 15:
                                snr = get_snr(clean_data)
                                if snr > best_snr:
                                    best_snr, best_proxy = snr, p
                                    plot_proxy = best_proxy # Update plot proxy if "auto" setting chose a better one
                        
                        if best_snr == -1.0:
                            print(f"[Sec {sec.section_id}] Skipped: No valid data.")
                            continue

                    target_splice = splices.get(best_proxy)
                    if target_splice is None or target_splice.empty:
                        print(f"[Sec {sec.section_id}] Skipped: Splice missing.")
                        continue

                    # Extracting chunk data
                    clean_sec = sec.scaled_data.dropna(subset=[best_proxy])
                    if len(clean_sec) < 15:
                        print(f"[Sec {sec.section_id}] Skipped: Insufficient data.")
                        continue
                        
                    # these variables are important elsewhere and have to be defined here 
                    # do not delete this
                    sec_vals = clean_sec[best_proxy].values
                    base_depths = clean_sec['Base_Scaled_Depth'].values
                    
                    # Grid Search for optimal alignment
                    best_sec_score, best_str = self._optimize_single_section(
                        sec=sec, 
                        anchor_shift=anchor_shift, 
                        target_splice=target_splice, 
                        best_proxy=best_proxy, 
                        str_range=str_range, 
                        str_step=str_step,
                        stretch_penalty = stretch_penalty
                    )
                                
                    # Lock the aligned chunk and then 
                    if best_sec_score > 0.2:
                        print(f"[Sec {sec.section_id}] Matched using '{best_proxy}' R={best_sec_score:.2f} (Shift: locked to {anchor_shift:+.2f}m, Stretch: {best_str:.2f}x)")
                        sec.affine_shift = anchor_shift
                        sec.stretch_factor = best_str
                        sec.aligned_proxy = best_proxy
                        alignment_scores.append(best_sec_score)
                    else:
                        print(f"[Sec {sec.section_id}] Failed to find strong match (Max R={best_sec_score:.2f}). Snapping to tiepoint baseline.")
                        sec.affine_shift = anchor_shift
                        sec.stretch_factor = 1.0  
                        sec.aligned_proxy = None

        # Plot results
        
        # Print the global correlation metric
        if alignment_scores:
            mean_r = np.mean(alignment_scores)
            print(f"Mean localized alignment score: r = {mean_r:.3f}")
        else:
            print("\n Mean localized alignment score: N/A (No successful automated matches)")

        if plot_results:
            print("\n Generating Post-Alignment Correlation Plots")
            
            # Loop through every proxy loaded in the dataset
            for plot_proxy in all_proxies:
                if plot_proxy not in splices or splices[plot_proxy].empty:
                    continue
                    
                print(f" Plotting {plot_proxy.capitalize()}...")
                df_splice = splices[plot_proxy]
                
                off_mcd, off_vals = [], []
                for h_name, hole in self.holes.items():
                    for core in hole.cores:
                        for sec in core.sections:
                            if not sec.is_locked and plot_proxy in sec.scaled_data.columns:
                                
                                if getattr(sec, 'aligned_proxy', None) != plot_proxy:
                                    continue
                                
                                clean_sec = sec.scaled_data.dropna(subset=[plot_proxy])
                                if clean_sec.empty: continue
                                
                                st = getattr(sec, 'stretch_factor', 1.0)
                                mcd = (clean_sec['Base_Scaled_Depth'] - sec.drilled_top) * st + sec.drilled_top + sec.affine_shift
                                
                                off_mcd.extend(mcd.values)
                                off_vals.extend(clean_sec[plot_proxy].values)

                if off_mcd:
                    off_mcd = np.array(off_mcd)
                    off_vals = np.array(off_vals)

                    f_splice = interp1d(df_splice['MCD'], df_splice[plot_proxy], kind='linear', bounds_error=False, fill_value=np.nan)
                    matched_splice_vals = f_splice(off_mcd)

                    valid_idx = ~np.isnan(matched_splice_vals) & ~np.isnan(off_vals)
                    x_splice = matched_splice_vals[valid_idx]
                    y_off = off_vals[valid_idx]

                    if len(x_splice) > 2:
                        r_val, p_val = pearsonr(x_splice, y_off)

                        plt.figure(figsize=(8, 8))
                        plt.scatter(x_splice, y_off, alpha=0.2, color='#1f77b4', edgecolor='none', s=15, label='Data Points')
                        
                        min_val = min(np.min(x_splice), np.min(y_off))
                        max_val = max(np.max(x_splice), np.max(y_off))
                        plt.plot([min_val, max_val], [min_val, max_val], 'k--', lw=2, label='1:1 Line')

                        # the plot commands are down here
                        plt.title(f"Proxy: {plot_proxy.capitalize()} | Overall r = {r_val:.3f} p = {p_val:e}", fontsize=14, fontweight='bold')
                        plt.xlabel("Splice / Composite Section Value (Interpolated)", fontsize=12)
                        plt.ylabel("Off-Splice Auto-Aligned Value", fontsize=12)
                        plt.legend(loc='upper left', fontsize=12)
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        
                        safe_proxy = re.sub(r'[\\/*?:"<>|]', "", proxy) # remove weird characters that cause Windows to crash
                        
                        filename = f"Post_Alignment_Correlation_{safe_proxy}.png"
                        plt.savefig(filename, dpi=300)
                        plt.show()
                        
                        print(f"Overall Pearson r for {plot_proxy}: {r_val:.3f}")
                        print(f"Saved plot as: {filename}")
                    else:
                        print(f"Not enough overlapping data points to plot correlation for {plot_proxy}.")
                else:
                    print(f"No off-splice data available to plot for {plot_proxy}.")
        
    def _optimize_single_section(self, sec, anchor_shift, target_splice, best_proxy, str_range=(0.70, 1.05), str_step=0.02, stretch_penalty = 0.1):
        """
        Optimizes the stretch factor of a single section.
        Assumes the section is strictly locked to the provided anchor_shift.
        """

        best_sec_score, best_str = -np.inf, 1.0
        
        # Calculate the exact shift needed to snap this section to the composite section
        best_shift = anchor_shift - sec.affine_shift 
        
        clean_sec = sec.scaled_data.dropna(subset=[best_proxy])
        if len(clean_sec) < 15:
            return best_sec_score, best_str
            
        sec_vals = clean_sec[best_proxy].values
        base_depths = clean_sec['Base_Scaled_Depth'].values

        stretches = np.arange(str_range[0], str_range[1] + str_step, str_step)
        
        for st in stretches:
            # Apply the locked shift and the test stretch
            test_mcd = (base_depths - sec.drilled_top) * st + sec.drilled_top + sec.affine_shift + best_shift
            min_mcd, max_mcd = test_mcd.min(), test_mcd.max()
            
            splice_overlap = target_splice[(target_splice['MCD'] >= min_mcd) & (target_splice['MCD'] <= max_mcd)]
            if len(splice_overlap) < 15: continue
                
            try:
                f_splice = interp1d(splice_overlap['MCD'], splice_overlap[best_proxy], kind='linear', fill_value="extrapolate")
                splice_interp = f_splice(test_mcd)
                
                r_val, _ = pearsonr(sec_vals, splice_interp)
                
                # Soft penalty for stretching too much
                penalty = abs(1.0 - st) * stretch_penalty
                penalized_score = r_val - penalty
                
                if not np.isnan(penalized_score) and penalized_score > best_sec_score:
                    best_sec_score, best_str = penalized_score, st
            except Exception:
                continue
                
        return best_sec_score, best_str
    
    def snap_floating_core_to_anchor(self, core, manual_anchor_shift, proxy, str_range=(0.70, 1.05), str_step=0.02, stretch_penalty = 0.1):
        """
        This function is only triggered by the review GUI. 
        Takes a manually calculated shift for a floating core and uses CompositeBuilder
        to optimize the stretch factor for all of its sections.
        """
        print(f"\n Snapping Floating Core {core.core_id} to tiepoint ({manual_anchor_shift:+.2f}m)")
        
        target_splice = self.get_splice_dataframe(proxy)
        if target_splice.empty:
            print("Error: Target splice is empty for the selected proxy.")
            return

        for sec in core.sections:
            if sec.is_locked:
                continue # Skip sections that are already safely on the splice
                
            # Same math as the batch processor
            score, best_str = self._optimize_single_section(
                sec=sec, 
                anchor_shift=manual_anchor_shift, 
                target_splice=target_splice, 
                best_proxy=proxy, 
                str_range=str_range, 
                str_step=str_step,
                stretch_penalty = stretch_penalty
            )

            # Apply the results
            if score > 0.2:
                print(f"     [Sec {sec.section_id}] Snapped & Stretched! R={score:.2f} (Stretch: {best_str:.2f}x)")
                sec.affine_shift = manual_anchor_shift
                sec.stretch_factor = best_str
                sec.aligned_proxy = proxy
            else:
                print(f"     [Sec {sec.section_id}] Stretch failed (Max R={score:.2f}). Snapping without stretching.")
                sec.affine_shift = manual_anchor_shift
                sec.stretch_factor = 1.0 
                sec.aligned_proxy = None