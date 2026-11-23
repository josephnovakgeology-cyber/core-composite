# -*- coding: utf-8 -*-
"""
Created on Fri May  1 06:47:58 2026

@author: joseph novak

CompositeBuilder algorithm and code that manages the associated logic.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from scipy.stats import pearsonr
import re
from .models import SpliceRecord


class CompositeBuilder:
    """
    The CompositeBuilder class handles the automated alignment of off-splice 
    core sections to the main splice.
    """
    def __init__(self):
        self.holes = {}
        self.splice = SpliceRecord()

    def add_hole(self, hole):
        self.holes[hole.hole_name] = hole
        
    def get_splice_dataframe(self, proxy):
        """
        Compiles the target splice into a single DataFrame by extracting 
        all sections explicitly locked on-splice by the builder.
        """
        depths, vals = [], []
    
        for h_name, hole in self.holes.items():
            for core in hole.cores:
                for sec in core.sections:
                    if getattr(sec, 'is_locked', False):
                        if proxy in sec.scaled_data.columns:
                            clean = sec.scaled_data.dropna(subset=[proxy]).copy()
                            if clean.empty: 
                                continue
                            
                            # Use original_drilled_top for correct MCD scaling
                            orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                            mcd = (clean['Base_Scaled_Depth'] - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                            clean['MCD'] = mcd
                            
                            # Strictly bound data by MCD tie limits if set
                            top_b = getattr(sec, 'splice_top_mcd', None)
                            bot_b = getattr(sec, 'splice_bot_mcd', None)
                            if top_b is not None and bot_b is not None:
                                clean = clean[(clean['MCD'] >= top_b) & (clean['MCD'] < bot_b)]
                        
                            depths.extend(clean['MCD'].values)
                            vals.extend(clean[proxy].values)
                        
        if not depths:
            return pd.DataFrame()
        
        df = pd.DataFrame({'MCD': depths, proxy: vals}).sort_values('MCD')
        return df.drop_duplicates(subset=['MCD']).reset_index(drop=True)
                    
        
    def optimize_off_splice(self, proxy='auto', str_range=(0.70, 1.05), str_step=0.01, stretch_penalty=0.1, plot_results=True):
        """
        Uses on-splice sections as tiepoints to constrain micro-scale grid searches.
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

        plot_proxy = proxy if proxy != 'auto' else (all_proxies[0] if all_proxies else None)
        alignment_scores = []

        for h_name, hole in self.holes.items():
            print(f"\nOptimizing Hole {h_name}...")
            
            for core in hole.cores:
                has_locked = any(s.is_locked for s in core.sections)
                has_unlocked = any(not s.is_locked for s in core.sections)
                
                if not (has_locked and has_unlocked):
                    continue 
                
                print(f"Correlating Core {core.core_id}...")
                
                locked_indices = [i for i, s in enumerate(core.sections) if s.is_locked]
                if not locked_indices:
                    continue 
                
                first_locked = locked_indices[0]
                last_locked = locked_indices[-1]
                
                # This for loop addresses off-splice sections above the on-splice data
                for i in range(first_locked - 1, -1, -1):
                    sec = core.sections[i]
                    if sec.scaled_data.empty: continue
                        
                    anchor_sec = core.sections[i+1]
                    anchor_orig_top = getattr(anchor_sec, 'original_drilled_top', anchor_sec.drilled_top)
                    anchor_mcd = (anchor_sec.drilled_top - anchor_orig_top) * anchor_sec.stretch_factor + anchor_orig_top + anchor_sec.affine_shift
                    
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
                                    plot_proxy = best_proxy 
                        
                        if best_snr == -1.0:
                            print(f"[Sec {sec.section_id}] Skipped: No valid data.")
                            continue

                    target_splice = splices.get(best_proxy)
                    if target_splice is None or target_splice.empty: 
                        continue

                    score, best_str, best_shift = self._optimize_single_section(
                        sec=sec, anchor_mcd=anchor_mcd, anchor_type='bottom',
                        target_splice=target_splice, best_proxy=best_proxy, 
                        max_allowed_mcd=np.inf, 
                        str_range=str_range, str_step=str_step, stretch_penalty=stretch_penalty
                    )
                    
                    sec.affine_shift = best_shift
                    sec.stretch_factor = best_str
                    if score > 0.2:
                        print(f"[Sec {sec.section_id} - UP] Matched '{best_proxy}' R={score:.2f} (Stretch: {best_str:.2f}x)")
                        sec.aligned_proxy = best_proxy
                        alignment_scores.append(score)
                    else:
                        print(f"[Sec {sec.section_id} - UP] No strong match.")

                # This loop addresses off-splice data below the on-splice section
                for i in range(last_locked + 1, len(core.sections)):
                    sec = core.sections[i]
                    if sec.scaled_data.empty: continue
                        
                    anchor_sec = core.sections[i-1]
                    anchor_orig_top = getattr(anchor_sec, 'original_drilled_top', anchor_sec.drilled_top)
                    anchor_mcd = (anchor_sec.drilled_bottom - anchor_orig_top) * anchor_sec.stretch_factor + anchor_orig_top + anchor_sec.affine_shift
                    
                    max_allowed_mcd = np.inf
                    intervening_length = 0.0
                    for ahead_idx in range(i + 1, len(core.sections)):
                        future_sec = core.sections[ahead_idx]
                        if future_sec.is_locked:
                            f_orig_top = getattr(future_sec, 'original_drilled_top', future_sec.drilled_top)
                            future_top_mcd = (future_sec.drilled_top - f_orig_top) * future_sec.stretch_factor + f_orig_top + future_sec.affine_shift
                            max_allowed_mcd = future_top_mcd - intervening_length
                            break
                        else:
                            intervening_length += (future_sec.drilled_bottom - future_sec.drilled_top)
                    
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
                                    plot_proxy = best_proxy 
                        
                        if best_snr == -1.0:
                            print(f"[Sec {sec.section_id}] Skipped: No valid data.")
                            continue

                    target_splice = splices.get(best_proxy)
                    if target_splice is None or target_splice.empty: 
                        continue

                    score, best_str, best_shift = self._optimize_single_section(
                        sec=sec, anchor_mcd=anchor_mcd, anchor_type='top',
                        target_splice=target_splice, best_proxy=best_proxy, 
                        max_allowed_mcd=max_allowed_mcd,
                        str_range=str_range, str_step=str_step, stretch_penalty=stretch_penalty
                    )
                    
                    sec.affine_shift = best_shift
                    sec.stretch_factor = best_str
                    if score > 0.2:
                        print(f"[Sec {sec.section_id} - DOWN] Matched '{best_proxy}' R={score:.2f} (Stretch: {best_str:.2f}x)")
                        sec.aligned_proxy = best_proxy
                        alignment_scores.append(score)
                    else:
                        print(f"[Sec {sec.section_id} - DOWN] No strong match.")

        if alignment_scores:
            mean_r = np.mean(alignment_scores)
            print(f"Mean localized alignment score: r = {mean_r:.3f}")
        else:
            print("\n Mean localized alignment score: N/A (No successful automated matches)")

        if plot_results:
            print("\n Generating Post-Alignment Correlation Plots")
            
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
                                orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                                mcd = (clean_sec['Base_Scaled_Depth'] - orig_top) * st + orig_top + sec.affine_shift
                                
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

                        plt.title(f"Proxy: {plot_proxy.capitalize()} | Overall r = {r_val:.3f} p = {p_val:e}", fontsize=14, fontweight='bold')
                        plt.xlabel("Splice / Composite Section Value (Interpolated)", fontsize=12)
                        plt.ylabel("Off-Splice Auto-Aligned Value", fontsize=12)
                        plt.legend(loc='upper left', fontsize=12)
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        
                        safe_proxy = re.sub(r'[\\/*?:"<>|]', "", proxy)
                        filename = f"Post_Alignment_Correlation_{safe_proxy}.png"
                        plt.savefig(filename, dpi=300)
                        plt.show()
                        
                        print(f"Overall Pearson r for {plot_proxy}: {r_val:.3f}")
                        print(f"Saved plot as: {filename}")

    def _optimize_single_section(self, sec, anchor_mcd, anchor_type, target_splice, best_proxy, max_allowed_mcd, str_range=(0.70, 1.05), str_step=0.02, stretch_penalty=0.1):
        """
        Optimizes alignment of single length of core while keeping it conjoined to the on-splice core sections. Length is hard coded to one meter.
        """
        best_sec_score, best_str, best_shift = -np.inf, 1.0, 0.0
        orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
        
        # Default is that cores remain in their scaled depth + affine shift scale if a good correlation is not found
        if anchor_type == 'top':
            default_shift = anchor_mcd - orig_top - (sec.drilled_top - orig_top)
        else:
            default_shift = anchor_mcd - orig_top - (sec.drilled_bottom - orig_top)
            
        clean_sec = sec.scaled_data.dropna(subset=[best_proxy])
        if len(clean_sec) < 15:
            return best_sec_score, best_str, default_shift
            
        sec_vals = clean_sec[best_proxy].values
        base_depths = clean_sec['Base_Scaled_Depth'].values

        f_splice = interp1d(target_splice['MCD'], target_splice[best_proxy], kind='linear', bounds_error=False, fill_value=np.nan)
        stretches = np.arange(str_range[0], str_range[1] + str_step, str_step)
        
        for st in stretches:
            if anchor_type == 'top':
                test_shift = anchor_mcd - orig_top - (sec.drilled_top - orig_top) * st
            else: 
                test_shift = anchor_mcd - orig_top - (sec.drilled_bottom - orig_top) * st
                
            test_mcd = (base_depths - orig_top) * st + orig_top + test_shift
            
            if test_mcd.max() > max_allowed_mcd:
                continue
                
            splice_interp = f_splice(test_mcd)
            valid_mask = ~np.isnan(splice_interp) & ~np.isnan(sec_vals)
            
            if np.sum(valid_mask) < 15:
                continue
                
            try:
                r_val, _ = pearsonr(sec_vals[valid_mask], splice_interp[valid_mask])
                penalized_score = r_val - (abs(1.0 - st) * stretch_penalty)
                
                if not np.isnan(penalized_score) and penalized_score > best_sec_score:
                    best_sec_score = penalized_score
                    best_str = st
                    best_shift = test_shift
            except Exception:
                continue
                
        if best_sec_score == -np.inf:
            return best_sec_score, 1.0, default_shift
            
        return best_sec_score, best_str, best_shift
    
    def snap_floating_core_to_anchor(self, core, manual_anchor_shift, proxy, str_range=(0.70, 1.05), str_step=0.02, stretch_penalty=0.1):
        target_splice = self.get_splice_dataframe(proxy)
        if target_splice.empty: return

        sec0 = core.sections[0]
        sec0_orig_top = getattr(sec0, 'original_drilled_top', sec0.drilled_top) # this has to be called here, it is used by a related function - do not remove
        anchor_mcd = sec0.drilled_top + manual_anchor_shift

        for i, sec in enumerate(core.sections):
            if sec.scaled_data.empty: continue
            
            if i > 0:
                anchor_sec = core.sections[i-1]
                anchor_orig_top = getattr(anchor_sec, 'original_drilled_top', anchor_sec.drilled_top)
                anchor_mcd = (anchor_sec.drilled_bottom - anchor_orig_top) * anchor_sec.stretch_factor + anchor_orig_top + anchor_sec.affine_shift

            max_allowed_mcd = np.inf
            intervening_length = 0.0
            for ahead_idx in range(i + 1, len(core.sections)):
                future_sec = core.sections[ahead_idx]
                if future_sec.is_locked:
                    f_orig_top = getattr(future_sec, 'original_drilled_top', future_sec.drilled_top)
                    future_top_mcd = (future_sec.drilled_top - f_orig_top) * future_sec.stretch_factor + f_orig_top + future_sec.affine_shift
                    max_allowed_mcd = future_top_mcd - intervening_length
                    break
                else:
                    intervening_length += (future_sec.drilled_bottom - future_sec.drilled_top)
            
            score, best_str, best_shift = self._optimize_single_section(
                sec=sec, anchor_mcd=anchor_mcd, anchor_type='top',
                target_splice=target_splice, best_proxy=proxy, 
                max_allowed_mcd=max_allowed_mcd,
                str_range=str_range, str_step=str_step, stretch_penalty=stretch_penalty
            )
            
            sec.affine_shift = best_shift
            sec.stretch_factor = best_str
            if score > 0.2:
                sec.aligned_proxy = proxy
                
    def plot_alignment_cor_vs_depth(self):
        """
        Plots the Pearson correlation coefficient (r-value) of each aligned 
        off-splice section as a function of its composite depth (MCD), 
        generating a separate window (figure) for each hole.
        Skipped/unaligned sections are plotted at y=-0.1 for visibility.
        """
        # Pre-compile splices for all active proxies to avoid redundant dataframe builds
        splices = {}
        all_proxies = set()
        for hole in self.holes.values():
            for core in hole.cores:
                all_proxies.update(getattr(core, 'active_proxies', []))
                
        for p in all_proxies:
            df = self.get_splice_dataframe(p)
            if not df.empty:
                splices[p] = df.dropna(subset=[p, 'MCD']).sort_values('MCD')
                
        # Define palette
        cb_palette = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', 
                      '#0072B2', '#D55E00', '#CC79A7', '#000000']
                
        # Calculate r-values and plot for each hole separately
        for h_name, hole in self.holes.items():
            plot_data_by_proxy = {}
            # Lists to hold the bounds of sections that failed alignment
            skipped_starts = []
            skipped_ends = []
            
            for core in hole.cores:
                for sec in core.sections:
                    proxy = getattr(sec, 'aligned_proxy', None)
                    
                    if not sec.is_locked:
                        if proxy is None:
                            st = getattr(sec, 'stretch_factor', 1.0)
                            orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                            
                            # Fallback to drilled boundaries if scaled_data is empty
                            if hasattr(sec, 'scaled_data') and not sec.scaled_data.empty:
                                mcd = (sec.scaled_data['Base_Scaled_Depth'] - orig_top) * st + orig_top + sec.affine_shift
                                skipped_starts.append(np.min(mcd))
                                skipped_ends.append(np.max(mcd))
                            else:
                                mcd_top = sec.drilled_top + sec.affine_shift
                                mcd_bottom = sec.drilled_bottom + sec.affine_shift
                                skipped_starts.append(mcd_top)
                                skipped_ends.append(mcd_bottom)
                            continue
                            
                        # Process successfully aligned sections
                        if proxy not in splices or splices[proxy].empty:
                            continue
                            
                        clean_sec = sec.scaled_data.dropna(subset=[proxy])
                        if len(clean_sec) < 3:
                            continue
                            
                        # Calculate section MCD using final affine shift and stretch factor
                        st = getattr(sec, 'stretch_factor', 1.0)
                        orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                        mcd = (clean_sec['Base_Scaled_Depth'] - orig_top) * st + orig_top + sec.affine_shift
                        
                        # Interpolate the main splice onto the section's MCD grid
                        df_splice = splices[proxy]
                        f_splice = interp1d(df_splice['MCD'], df_splice[proxy], kind='linear', bounds_error=False, fill_value=np.nan)
                        matched_splice_vals = f_splice(mcd)
                        
                        sec_vals = clean_sec[proxy].values
                        valid_mask = ~np.isnan(matched_splice_vals) & ~np.isnan(sec_vals)
                        
                        # Calculate the Pearson r for the overlapping valid data
                        if np.sum(valid_mask) > 2:
                            r_val, _ = pearsonr(sec_vals[valid_mask], matched_splice_vals[valid_mask])
                            
                            if proxy not in plot_data_by_proxy:
                                plot_data_by_proxy[proxy] = {'starts': [], 'ends': [], 'r_vals': []}
                                
                            plot_data_by_proxy[proxy]['starts'].append(np.min(mcd))
                            plot_data_by_proxy[proxy]['ends'].append(np.max(mcd))
                            plot_data_by_proxy[proxy]['r_vals'].append(r_val)
                            
            if not plot_data_by_proxy and not skipped_starts:
                print(f"No aligned or skipped sections to plot for Hole {h_name}.")
                continue
                
            # Generate the diagnostic plot for the current hole
            plt.figure(figsize=(10, 5))
            
            # Loop through each proxy and explicitly assign a color from the colorblind palette
            for i, (proxy, data) in enumerate(plot_data_by_proxy.items()):
                proxy_color = cb_palette[i % len(cb_palette)]
                plt.hlines(y=data['r_vals'], xmin=data['starts'], xmax=data['ends'], 
                           color=proxy_color, linewidth=4, alpha=0.8, zorder=3, label=f'Proxy: {proxy}')
                           
            # Plot the skipped sections below 0
            if skipped_starts:
                skipped_y = [-0.1] * len(skipped_starts)
                plt.hlines(y=skipped_y, xmin=skipped_starts, xmax=skipped_ends, 
                           color='#999999', linewidth=4, alpha=0.6, linestyle=':', 
                           zorder=2, label='Skipped / Unaligned')
            
            # Plot styling
            plt.title(f"Off-Splice r Values vs. Composite Depth - Hole {h_name}\n" "Each bar is one core section\n", fontsize=14, fontweight='bold')
            plt.xlabel("Composite Depth (MCD)", fontsize=12)
            plt.ylabel("Section-level Pearson R-value", fontsize=12)
            
            plt.ylim(-0.15, 1.05)
            
            # Add a faint line at y=0 to separate skipped sections from valid correlations
            plt.axhline(0, color='black', linewidth=1, alpha=0.3, zorder=1)
            
            plt.grid(True, linestyle='--', alpha=0.6, zorder=0)
            plt.legend(loc='lower right')
            plt.tight_layout()
            
            # Save and display a distinct window for each hole
            plt.savefig(f"R_penalty_vs_MCD_{h_name}.png", dpi=300)
            plt.show()