# -*- coding: utf-8 -*-
"""
Created on Fri May  1 06:09:13 2026

@author: josep
"""

import pandas as pd
import copy
import re
import numpy as np
import os
import glob
from .models import Hole, Core, Section
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

def load_from_multiple_files(hole_name, odp_summary_csv, hole_data_files, proxy_keywords=['density'], data_dir=None, chunk_size=1.0, depth_scale = "mbsf"):
    """
    This function loads DSDP / ODP / IODP physical properties data from Janus / LIMS into the Hole, Core, 
    and Section classes in a coherent way. I so very strongly advise you do not mess with this.
    
    depth_scale: specifies whether to use Depth (mbsf) or to first correct for core expansion using the 
    compressed depth scale.
    
    chunk_size: the length of the sections along which off-splice correlations by CompositeBuilder are made.
    
    """
    # Load and clean the summary file FIRST
    summary_df = pd.read_csv(odp_summary_csv, sep=None, engine='python')
    summary_df.rename(columns=lambda x: str(x).strip(), inplace=True)
    
    hole_letter = hole_name[-1].upper()
    hole_summary = summary_df[summary_df['H'].astype(str).str.strip().str.upper() == hole_letter]
    
    # Extract the Leg/Expedition to pass to the Hole model
    leg_col = next((c for c in summary_df.columns if 'leg' in c.lower() or 'exp' in c.lower()), None)
    extracted_leg = str(hole_summary[leg_col].iloc[0]).strip() if leg_col and not hole_summary.empty else ""
    
    # Instantiate the Hole with the leg parameter
    new_hole = Hole(hole_name, leg=extracted_leg)
    
    combined_data = pd.DataFrame()
    
    for file in hole_data_files:
        df = pd.read_csv(file, sep=',')
        
        df.rename(columns=lambda x: str(x).strip(), inplace=True)
        
        depth_col = next((c for c in df.columns if ('mbsf' in c.lower() or 'depth' in c.lower() or 'csf' in c.lower()) and 'mcd' not in c.lower()), None)
        if depth_col: df.rename(columns={depth_col: 'Depth'}, inplace=True)
        
        if 'Depth' in df.columns:
            df['Depth'] = pd.to_numeric(df['Depth'], errors='coerce').round(4)
        
        core_col = next((c for c in df.columns if c.lower() in ['core', 'cor']), None)
        if core_col: df.rename(columns={core_col: 'Core'}, inplace=True)
        
        combined_data = pd.concat([combined_data, df], ignore_index=True)
        
    if not combined_data.empty and 'Depth' in combined_data.columns and 'Core' in combined_data.columns:
        combined_data.sort_values(by=['Core', 'Depth'], inplace=True)
        combined_data['Core_Clean'] = combined_data['Core'].astype(str).str.extract(r'(\d+)')[0]
        
    for _, row in hole_summary.iterrows():
        core_num = str(row['Cor']).strip().split('.')[0]
        core_type = str(row['T']).strip() if str(row['T']).lower() != 'nan' else ''
        cid = f"{core_num}{core_type}" 
        core_mask = combined_data['Core_Clean'] == core_num
        core_data_slice = combined_data[core_mask]
        if not core_data_slice.empty:
            drilled_top = float(row['Top(mbsf)'])
            drilled_bottom = drilled_top + float(row['Cored(m)'])
            recovered_length = float(row['Rec(m)'])
            new_core = Core(hole_name, cid, core_data_slice, drilled_top, drilled_bottom, recovered_length, proxy_keywords)
            
            # Optionally load photos if a directory was provided
            if data_dir:
                load_core_photo(new_core, data_dir)
            
            if depth_scale in ["mbsf", "CSF-A", "traditional", "normal"]:
                compress_depth = False
            elif depth_scale in ["mbsfc", "compressed"]:
                compress_depth = True
            else:
                compress_depth = True
                
            
            if new_core.active_proxies:
                # Pass the compress_depth flag down to the Core method
                new_core.compress_depth_and_split(chunk_size=chunk_size, compress_depth=compress_depth)
                new_hole.cores.append(new_core)
                
    return new_hole

def load_external_affine(builder, csv_path):
    """
    Reads an external Affine/Splice table.
    Applies shifts to cores and non-destructively splits them into locked (on-splice)
    and unlocked (off-splice) chunks based on the bounds defined by the splice table.
    """
    
    print(f"\n Loading External Splice from {csv_path} ---")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return
        
    col_map = {c: c.strip().lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    
    hole_col = next((c for c in df.columns if 'hole' in c), None)
    core_col = next((c for c in df.columns if 'core' in c), None)
    sec_col = next((c for c in df.columns if 'sec' in c and 'sed' not in c), None)
    
    shift_col = next((c for c in df.columns if any(x in c for x in ['shift', 'offset', 'affine'])), None)
    stretch_col = next((c for c in df.columns if 'stretch' in c), None)
    status_col = next((c for c in df.columns if any(x in c for x in ['status', 'splice', 'lock'])), None)
    
    top_mcd_col = next((c for c in df.columns if 'comp top' in c or 'mcd top' in c or 'top_mcd' in c or 'top mcd' in c), None)
    bot_mcd_col = next((c for c in df.columns if 'comp bot' in c or 'mcd bot' in c or 'bot_mcd' in c or 'bot mcd' in c), None)
    
    if not hole_col or not core_col or not shift_col:
        print("Error: External CSV must contain at least 'Hole', 'Core', and 'Shift' columns.")
        return
        
    for idx, row in df.iterrows():
        raw_hole = str(row[hole_col]).strip()
        core_id = str(row[core_col]).strip()
        
        shift_val = float(row[shift_col]) if not pd.isna(row[shift_col]) else 0.0
        stretch_val = float(row[stretch_col]) if stretch_col and not pd.isna(row[stretch_col]) else 1.0
        
        is_locked = False
        if status_col and not pd.isna(row[status_col]):
            stat_val = str(row[status_col]).strip().lower()
            if stat_val in ['on-splice', 'true', '1', 'yes', 'locked', 'on']:
                is_locked = True
                
        target_hole = None
        for h_name, h_obj in builder.holes.items():
            if h_name.endswith(raw_hole) or raw_hole.endswith(h_name):
                target_hole = h_obj
                break
        if not target_hole: continue
            
        for core in target_hole.cores:
            if str(core.core_id) == core_id:
                target_sec_id = str(row[sec_col]).strip() if sec_col and not pd.isna(row[sec_col]) else None
                
                new_sections = []
                for sec in core.sections:
                    if target_sec_id and str(sec.section_id) != target_sec_id:
                        new_sections.append(sec)
                        continue
                        
                    # If not on-splice, shift it and keep it unlocked
                    if not is_locked:
                        sec.affine_shift = shift_val
                        sec.stretch_factor = stretch_val
                        new_sections.append(sec)
                        continue
                        
                    # If on-Splice, determine the depth bounds to split the section
                    orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    orig_bot = getattr(sec, 'original_drilled_bottom', sec.drilled_bottom)
                    
                    if top_mcd_col and not pd.isna(row[top_mcd_col]):
                        top_mcd = float(row[top_mcd_col])
                        raw_top = orig_top + ((top_mcd - shift_val - orig_top) / stretch_val)
                    else:
                        raw_top = -np.inf
                        
                    if bot_mcd_col and not pd.isna(row[bot_mcd_col]):
                        bot_mcd = float(row[bot_mcd_col])
                        raw_bot = orig_top + ((bot_mcd - shift_val - orig_top) / stretch_val)
                    else:
                        raw_bot = np.inf
                        
                    
                    df_data = sec.scaled_data
                    df_top = df_data[df_data['Base_Scaled_Depth'] < raw_top].copy()
                    df_splice = df_data[(df_data['Base_Scaled_Depth'] >= raw_top) & (df_data['Base_Scaled_Depth'] < raw_bot)].copy()
                    df_bot = df_data[df_data['Base_Scaled_Depth'] >= raw_bot].copy()
                    
                    # Save the top off-splice tail
                    if not df_top.empty:
                        sec_top = copy.deepcopy(sec)
                        sec_top.scaled_data = df_top
                        sec_top.drilled_top = df_top['Base_Scaled_Depth'].min()
                        sec_top.drilled_bottom = df_top['Base_Scaled_Depth'].max()
                        sec_top.original_drilled_top = orig_top
                        sec_top.original_drilled_bottom = orig_bot
                        sec_top.affine_shift = shift_val
                        sec_top.stretch_factor = stretch_val
                        sec_top.is_locked = False
                        new_sections.append(sec_top)
                        
                    # Save the locked Master Splice interval
                    if not df_splice.empty:
                        sec_splice = copy.deepcopy(sec)
                        sec_splice.scaled_data = df_splice
                        sec_splice.drilled_top = df_splice['Base_Scaled_Depth'].min()
                        sec_splice.drilled_bottom = df_splice['Base_Scaled_Depth'].max()
                        sec_splice.original_drilled_top = orig_top
                        sec_splice.original_drilled_bottom = orig_bot
                        sec_splice.affine_shift = shift_val
                        sec_splice.stretch_factor = stretch_val
                        sec_splice.is_locked = True

                        calc_top_mcd = top_mcd if (top_mcd_col and not pd.isna(row[top_mcd_col])) else (sec_splice.drilled_top - orig_top) * stretch_val + orig_top + shift_val
                        calc_bot_mcd = bot_mcd if (bot_mcd_col and not pd.isna(row[bot_mcd_col])) else (sec_splice.drilled_bottom - orig_top) * stretch_val + orig_top + shift_val

                        
                        sec_splice.splice_top_mcd = calc_top_mcd
                        sec_splice.splice_bot_mcd = calc_bot_mcd
                        
                        new_sections.append(sec_splice)

                        builder.splice.append_tie(
                            top_mcd=calc_top_mcd,
                            bot_mcd=calc_bot_mcd,
                            hole_name=target_hole.hole_name,
                            core_id=core.core_id,
                            top_drilled=sec_splice.drilled_top,
                            bot_drilled=sec_splice.drilled_bottom
                        )
                        
                    # Save the bottom off-splice tail
                    if not df_bot.empty:
                        sec_bot = copy.deepcopy(sec)
                        sec_bot.scaled_data = df_bot
                        sec_bot.drilled_top = df_bot['Base_Scaled_Depth'].min()
                        sec_bot.drilled_bottom = df_bot['Base_Scaled_Depth'].max()
                        sec_bot.original_drilled_top = orig_top
                        sec_bot.original_drilled_bottom = orig_bot
                        sec_bot.affine_shift = shift_val
                        sec_bot.stretch_factor = stretch_val
                        sec_bot.is_locked = False
                        new_sections.append(sec_bot)
                        
                # Replace the core's old sections with the newly split chunks
                core.sections = new_sections
                
    print("Splice successfully applied")
    print("\n Ready to run: builder.optimize_off_splice()")
    
    return builder
def export_affine_table(builder, output_filename="Master_Final_Affine_Table.csv"):
    """
    Exports the final affine shift, stretch, and lock status for every section 
    in the composite builder into a .csv file.
    """
    print("Exporting Final Affine/Splice Table...")
    records = []
    
    for h_name, hole in builder.holes.items():
        for core in hole.cores:
            
            # 1. Group chunks by section_id to prevent duplicate rows for split sections
            unique_sec_ids = []
            for sec in core.sections:
                if sec.section_id not in unique_sec_ids:
                    unique_sec_ids.append(sec.section_id)
            
            for sid in unique_sec_ids:
                chunks = [s for s in core.sections if s.section_id == sid]
                
                # Prioritize the locked (On-Splice) chunk if the section was split
                locked_chunks = [s for s in chunks if getattr(s, 'is_locked', False)]
                export_sec = locked_chunks[0] if locked_chunks else chunks[0]
                
                orig_top = getattr(export_sec, 'original_drilled_top', export_sec.drilled_top)
                orig_bot = getattr(export_sec, 'original_drilled_bottom', export_sec.drilled_bottom)
                
                # 2. Use stored splice bounds to prevent tie-points shrinking to data bounds
                top_mcd = getattr(export_sec, 'splice_top_mcd', (export_sec.drilled_top - orig_top) * export_sec.stretch_factor + orig_top + export_sec.affine_shift)
                bot_mcd = getattr(export_sec, 'splice_bot_mcd', (export_sec.drilled_bottom - orig_top) * export_sec.stretch_factor + orig_top + export_sec.affine_shift)
                
                sec_hole = getattr(export_sec, 'hole_name', h_name)
                sec_core = getattr(core, 'core_id', getattr(export_sec, 'core_id', ''))
                
                records.append({
                    'Hole': sec_hole,
                    'Core': sec_core,
                    'Section': export_sec.section_id,
                    'Top_Drilled_mbsf': round(orig_top, 3), # 3. FIXED: use orig_top instead of cut drilled_top
                    'Bot_Drilled_mbsf': round(orig_bot, 3),
                    'Top_MCD': round(top_mcd, 3),
                    'Bot_MCD': round(bot_mcd, 3),
                    'Affine_Shift_m': round(export_sec.affine_shift, 4),
                    'Stretch_Factor': round(export_sec.stretch_factor, 4),
                    'Status': 'On-Splice' if export_sec.is_locked else 'Off-Splice'
                })
    
    if records:
        df = pd.DataFrame(records)
        df = df.sort_values(by=['Hole', 'Top_Drilled_mbsf']).reset_index(drop=True)
        
        try:
            df.to_csv(output_filename, index=False)
            print(f"SUCCESS! Master Affine Table exported to: {output_filename}")
        except PermissionError:
            print(f"\nERROR: Could not save to {output_filename}. Is it open in Excel?")
    else:
        print("No data found to export. Please load holes and cores first.")
                
def export_and_save(builder, active_holes, all_proxies):
    """Compiles all data into CSVs for the Master Splice and individual holes."""
    print(" Starting Data Export ")
    
    # Organize proxies into export groups (Color data together, everything else separate)
    color_keywords = ['L*', 'a*', 'b*', 'A*', 'B*', 'L', 'A', 'B','a', 'b', 'Reflectance L*','Reflectance a*','Reflectance b*', 'LSTAR', 'ASTAR', 'BSTAR']
    color_proxies = [p for p in all_proxies if p.upper() in color_keywords]
    other_proxies = [p for p in all_proxies if p not in color_proxies]
    
    export_groups = []
    if color_proxies:
        export_groups.append(("Color_Data", color_proxies))
    for p in other_proxies:
        export_groups.append((p, [p]))
        
    for group_name, proxy_list in export_groups:
        master_splice_dfs = []
        
        # Export each hole
        for h_name, hole in builder.holes.items():
            if h_name not in active_holes:
                continue
            
            site_val = h_name[:-1] if h_name and not h_name[-1].isdigit() else h_name
            hole_val = h_name[-1] if h_name and not h_name[-1].isdigit() else ""
            leg_val = getattr(hole, 'leg', "")
            
            hole_dfs = []
            
            for core in hole.cores:
                is_activated = any(sec.is_locked for sec in core.sections)
                has_custom_shift = any(getattr(sec, 'affine_shift', 0.0) != 0.0 for sec in core.sections)
                if not (is_activated or has_custom_shift):
                    continue
                    
                for sec in core.sections:
                    valid_targets = set(proxy_list + [p.capitalize() for p in proxy_list])
                    avail_proxies = [p for p in sec.scaled_data.columns if p in valid_targets]
                    if not avail_proxies:
                        continue
                        
                    df_clean = sec.scaled_data.dropna(subset=avail_proxies, how='all').copy()
                    
                    # Filter out-of-bounds rows for this section chunk
                    mbsf_temp = df_clean['Base_Scaled_Depth']
                    valid_mask = (mbsf_temp >= sec.drilled_top) & (mbsf_temp <= sec.drilled_bottom)
                    df_clean = df_clean[valid_mask]
                    
                    if df_clean.empty:
                        continue
                        
                    mbsf = df_clean['Base_Scaled_Depth']
                    orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    mcd = (mbsf - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                    
                    sec_depth_col = next((c for c in df_clean.columns if 'offset' in c.lower() or 'cm' in c.lower() or 'in section' in c.lower()), None)
                    sec_depth_vals = df_clean[sec_depth_col] if sec_depth_col else np.nan
                    
                    orig_sec_col = next((c for c in df_clean.columns if c.strip().lower() in ['section', 'sec', 'sc']), None)
                    orig_sec_vals = df_clean[orig_sec_col] if orig_sec_col else sec.section_id
                    
                    out_df = pd.DataFrame({
                        "Leg": leg_val,
                        "Site": site_val,
                        "Hole": hole_val,
                        "Core": core.core_id,
                        "Sc": orig_sec_vals,
                        "Depth in Section (cm)": sec_depth_vals,
                        "Original Depth": round(df_clean['Depth'], 3),
                        "Depth (MCD)": round(mcd, 3)
                    })
                    
                    for p in avail_proxies:
                        out_df[p] = df_clean[p]
                        
                    out_df['Status'] = 'on-splice' if sec.is_locked else 'off-splice'
                    hole_dfs.append(out_df)
                    
            if hole_dfs:
                df_hole = pd.concat(hole_dfs, ignore_index=True)
                df_hole.sort_values(by='Depth (MCD)', inplace=True)
                
                safe_group = re.sub(r'[\\/*?:"<>|]', "", group_name)
                safe_h_name = re.sub(r'[\\/*?:"<>|]', "", str(h_name))
                filename_hole = f"Export_Hole_{safe_h_name}_{safe_group}.csv"
                df_hole.to_csv(filename_hole, index=False)
                print(f"  -> Saved: {filename_hole}")

        # Export the splice
        if hasattr(builder, 'splice') and builder.splice and builder.splice.intervals:
            for tie in builder.splice.intervals:
                hole_name = tie['Hole']
                core_id = str(tie['Core'])
                top_mcd = tie['Top_MCD']
                bot_mcd = tie['Bot_MCD']
                
                hole = builder.holes.get(hole_name)
                if not hole:
                    continue
                    
                site_val = hole_name[:-1] if hole_name and hole_name[-1].isalpha() else hole_name
                hole_val = hole_name[-1] if hole_name and hole_name[-1].isalpha() else ""
                
                for core in hole.cores:
                    if str(core.core_id) != core_id:
                        continue
                        
                    for sec in core.sections:
                        if not sec.is_locked:
                            continue
                            
                        valid_targets = set(proxy_list + [p.capitalize() for p in proxy_list])
                        avail_proxies = [p for p in sec.scaled_data.columns if p in valid_targets]
                        if not avail_proxies:
                            continue
                            
                        df_clean = sec.scaled_data.dropna(subset=avail_proxies, how='all').copy()
                        
                        # --- FIX 1: ADDED SECTION BOUNDARY FILTER HERE ---
                        mbsf_temp = df_clean['Base_Scaled_Depth']
                        valid_mask = (mbsf_temp >= sec.drilled_top) & (mbsf_temp <= sec.drilled_bottom)
                        df_clean = df_clean[valid_mask]
                        
                        if df_clean.empty:
                            continue
                            
                        mbsf = df_clean['Base_Scaled_Depth']
                        orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                        mcd = (mbsf - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                        df_clean['MCD_Calc'] = mcd
                        
                        # --- FIX 2: CHANGED <= bot_mcd TO < bot_mcd HERE ---
                        df_tie = df_clean[(df_clean['MCD_Calc'] >= top_mcd) & (df_clean['MCD_Calc'] < bot_mcd)].copy()
                        if df_tie.empty:
                            continue
                            
                        sec_depth_col = next((c for c in df_tie.columns if 'offset' in c.lower() or 'cm' in c.lower() or 'in section' in c.lower()), None)
                        sec_depth_vals = df_tie[sec_depth_col] if sec_depth_col else np.nan
                        
                        orig_sec_col = next((c for c in df_tie.columns if c.strip().lower() in ['section', 'sec', 'sc']), None)
                        orig_sec_vals = df_tie[orig_sec_col] if orig_sec_col else sec.section_id
                        
                        ms_row = pd.DataFrame({
                            "Leg": "",
                            "Site": site_val,
                            "Hole": hole_val,
                            "Core": core.core_id,
                            "Sc": orig_sec_vals,
                            "Depth in Section (cm)": sec_depth_vals,
                            "Original Depth": round(df_tie['Depth'], 3),
                            "Depth (MCD)": round(df_tie['MCD_Calc'], 3)
                        })
                        
                        for p in avail_proxies:
                            ms_row[p] = df_tie[p]
                            
                        master_splice_dfs.append(ms_row)
                        
        if master_splice_dfs:
            df_ms = pd.concat(master_splice_dfs, ignore_index=True)
            df_ms.sort_values(by='Depth (MCD)', inplace=True)
            df_ms.drop_duplicates(subset=['Hole', 'Core', 'Sc', 'Depth (MCD)'], inplace=True)
            
            safe_group = re.sub(r'[\\/*?:"<>|]', "", group_name)
            filename_ms = f"Export_MasterSplice_{safe_group}.csv"
            df_ms.to_csv(filename_ms, index=False)
            print(f"  -> Saved Master Splice: {filename_ms}")
            
    print("Export Complete. Check your directory.")
    

def map_subsamples_to_mcd(builder, csv_path, output_filename="Mapped_Subsamples.csv", depth_scale="mbsf"):
    """Takes an external CSV of subsample data and calculates their Composite
    Depth (MCD) using the current affine/splice model. 

    depth_scale: must match the scale used in load_from_multiple_files and the splice. 
    If 'mbsf', maps from depth mbsf to mcd directly. If 'compressed' or 'mbsfc', 
    applies the core recovery factor first.
    """

    print(f"Mapping Subsamples to MCD from {csv_path}...")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Fuzzy match required columns
    hole_col = next((c for c in df.columns if "hole" in c.lower()), None)
    core_col = next((c for c in df.columns if "core" in c.lower()), None)
    depth_col = next(
        (c for c in df.columns if "depth" in c.lower() and "mcd" not in c.lower() and "comp" not in c.lower()), None
    )

    if not hole_col or not core_col or not depth_col:
        print(f"Error: Missing required columns. Found Hole: {hole_col}, Core: {core_col}, Depth: {depth_col}")
        return
    
    # Determine compression flag to match the Core loader
    if depth_scale in ["mbsf", "CSF-A", "traditional", "normal"]:
        compress_depth = False
    else:
        compress_depth = True

    mcd_values = []

    for idx, row in df.iterrows():
        raw_hole = str(row[hole_col]).strip()
        raw_core = str(row[core_col]).strip()

        try:
            raw_depth = float(row[depth_col]) if not pd.isna(row[depth_col]) else np.nan
        except ValueError:
            print(f"Row {idx}: Invalid depth '{row[depth_col]}'. Skipping.")
            mcd_values.append(np.nan)
            continue

        if pd.isna(raw_depth):
            mcd_values.append(np.nan)
            continue

        # Match the Hole
        target_hole = next((h for h_name, h in builder.holes.items() if h_name.endswith(raw_hole) or raw_hole.endswith(h_name)), None)

        if not target_hole:
            print(f"Row {idx} [HOLE MISMATCH]: CSV Hole '{raw_hole}' not found.")
            mcd_values.append(np.nan)
            continue

        # Match the Core (stripping suffixes as validated for your sites)
        if raw_core.endswith(".0"):
            raw_core = raw_core[:-2]
        core_num_csv = re.sub(r"\D", "", raw_core)
        
        target_core = next((c for c in target_hole.cores if re.sub(r"\D", "", str(c.core_id)) == core_num_csv), None)

        if not target_core or not getattr(target_core, 'sections', None):
            mcd_values.append(np.nan)
            continue

        core_top = target_core.drilled_top
        
        # Apply the exact same compression logic used in Core.compress_depth_and_split
        if compress_depth:
            # Use the core's official recovered_length, not the proxy data limits
            rec_len = getattr(target_core, 'recovered_length', 0)
            if rec_len > 0:
                rf = min(1.0, target_core.drilled_length / rec_len)
            else:
                rf = 1.0
            working_depth = core_top + ((raw_depth - core_top) * rf)
        else:
            working_depth = raw_depth

        # Match to the correct Virtual Section using working_depth
        target_sec = None
        for s_obj in target_core.sections:
            if s_obj.drilled_top <= working_depth <= s_obj.drilled_bottom:
                target_sec = s_obj
                break

        # Fallback for boundary rounding edges
        if not target_sec:
            if working_depth < target_core.sections[0].drilled_top:
                target_sec = target_core.sections[0]
            elif working_depth > target_core.sections[-1].drilled_bottom:
                target_sec = target_core.sections[-1]
            else:
                target_sec = min(
                    target_core.sections,
                    key=lambda s: abs(((s.drilled_top + s.drilled_bottom) / 2.0) - working_depth)
                )

        # Calculate MCD matching the math in Core.apply_splice_cut
        st = getattr(target_sec, "stretch_factor", 1.0)
        orig_top = getattr(target_sec, 'original_drilled_top', target_sec.drilled_top)
        
        mcd = ((working_depth - orig_top) * st + orig_top + target_sec.affine_shift)
        mcd_values.append(mcd)

    df["Depth (mcd)"] = mcd_values
    df.to_csv(output_filename, index=False)
    
    success_count = len([m for m in mcd_values if not pd.isna(m)])
    print(f"Mapped {success_count} / {len(df)} samples to MCD scale.")
    
    
def export_project_data(builder, active_holes, all_proxies):
    """
    Extracts the final alignment data from the CompositeBuilder and exports 
    the Affine Table (shifts/stretches) and the Master Splice Record to CSVs.
    """
    print("Exporting project data")
    
    #Export the affine table
    affine_data = []
    
    for h_name, hole in builder.holes.items():
        if h_name not in active_holes:
            continue
            
        for core in hole.cores:
            # Group chunks by section_id to prevent duplicates
            unique_sec_ids = []
            for sec in core.sections:
                if sec.section_id not in unique_sec_ids:
                    unique_sec_ids.append(sec.section_id)
            
            for sid in unique_sec_ids:
                chunks = [s for s in core.sections if s.section_id == sid]
                locked_chunks = [s for s in chunks if getattr(s, 'is_locked', False)]
                export_sec = locked_chunks[0] if locked_chunks else chunks[0]
                
                orig_top = getattr(export_sec, 'original_drilled_top', export_sec.drilled_top)
                orig_bot = getattr(export_sec, 'original_drilled_bottom', export_sec.drilled_bottom)
                
                top_mcd = getattr(export_sec, 'splice_top_mcd', (export_sec.drilled_top - orig_top) * export_sec.stretch_factor + orig_top + export_sec.affine_shift)
                bot_mcd = getattr(export_sec, 'splice_bot_mcd', (export_sec.drilled_bottom - orig_top) * export_sec.stretch_factor + orig_top + export_sec.affine_shift)
                
                affine_data.append({
                    'Hole': h_name,
                    'Core': core.core_id,
                    'Section': export_sec.section_id,
                    'Top_Depth_Drilled (mbsf)': orig_top,  # FIXED
                    'Bottom_Depth_Drilled (mbsf)': orig_bot, # FIXED
                    'Affine_Shift (m)': getattr(export_sec, 'affine_shift', 0.0),
                    'Stretch_Factor': getattr(export_sec, 'stretch_factor', 1.0),
                    'On_Splice': getattr(export_sec, 'is_locked', False),
                    "Top MCD": round(top_mcd, 3),
                    "Bot MCD": round(bot_mcd, 3)
                })
        
    #export the splice record
    if hasattr(builder, 'splice') and builder.splice is not None:
        splice_records = []
        
        for h_name, hole in builder.holes.items():
            for core in hole.cores:
                locked_sections = [sec for sec in core.sections if getattr(sec, 'is_locked', False)]
                
                if not locked_sections:
                    continue
                    
                orig_tops, orig_bots = [], []
                scaled_tops, scaled_bots = [], []
                top_mcds, bot_mcds = [], []
                
                for sec in locked_sections:
                    o_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    o_bot = getattr(sec, 'original_drilled_bottom', sec.drilled_bottom)
                    
                    # CHANGE 3: Prioritize explicit tie bounds stored during section splits
                    t_mcd = getattr(sec, 'splice_top_mcd', (sec.drilled_top - o_top) * sec.stretch_factor + o_top + sec.affine_shift)
                    b_mcd = getattr(sec, 'splice_bot_mcd', (sec.drilled_bottom - o_top) * sec.stretch_factor + o_top + sec.affine_shift)
                    
                    orig_tops.append(o_top)
                    orig_bots.append(o_bot)
                    scaled_tops.append(sec.drilled_top)
                    scaled_bots.append(sec.drilled_bottom)
                    top_mcds.append(t_mcd)
                    bot_mcds.append(b_mcd)
                    
                splice_records.append({
                    "Hole": h_name,
                    "Core": core.core_id,
                    "Top Depth (mbsf)": round(min(orig_tops), 3),
                    "Bot Depth (mbsf)": round(max(orig_bots), 3),
                    "Top Scaled Depth (mbsfc)": round(min(scaled_tops), 3),
                    "Bot Scaled Depth (mbsfc)": round(max(scaled_bots), 3),
                    "Top MCD": round(min(top_mcds), 3),
                    "Bot MCD": round(max(bot_mcds), 3)
                })
                        
        if splice_records:
            splice_df = pd.DataFrame(splice_records)
            splice_df = splice_df.sort_values(by="Top MCD").reset_index(drop=True)
            
            splice_filename = "Export_Splice_Record.csv"
            splice_df.to_csv(splice_filename, index=False)
            print(f" Saved Master Splice Record: {splice_filename}")
        else:
            print("  No splice intervals found to export.")

    # export physical properties data
    color_keywords = ['L*', 'a*', 'b*', 'A*', 'B*', 'L', 'A', 'B','a', 'b', 'Reflectance L*','Reflectance a*','Reflectance b*', 'LSTAR', 'ASTAR', 'BSTAR']
    
    # Evaluated color_keywords as uppercase so p.upper() actually finds a match
    color_proxies = [p for p in all_proxies if str(p).upper() in [k.upper() for k in color_keywords]]
    other_proxies = [p for p in all_proxies if p not in color_proxies]
    
    export_groups = []
    if color_proxies:
        export_groups.append(("Color_Data", color_proxies))
    for p in other_proxies:
        export_groups.append((p, [p]))
        
    for group_name, proxy_list in export_groups:
        master_splice_dfs = []
        
        for h_name, hole in builder.holes.items():
            if h_name not in active_holes:
                continue
            
            site_val = h_name[:-1] if h_name and not h_name[-1].isdigit() else h_name
            hole_val = h_name[-1] if h_name and not h_name[-1].isdigit() else ""
            leg_val = getattr(hole, 'leg', "")
            
            hole_dfs = []
            
            for core in hole.cores:
                is_locked = any(sec.is_locked for sec in core.sections)
                has_custom_shift = any(getattr(sec, 'affine_shift', 0.0) != 0.0 for sec in core.sections)
                if not (is_locked or has_custom_shift):
                    continue
                    
                for sec in core.sections:
                    valid_targets = set(proxy_list + [p.capitalize() for p in proxy_list])
                    avail_proxies = [p for p in sec.scaled_data.columns if p in valid_targets]
                    if not avail_proxies:
                        continue
                        
                    df_clean = sec.scaled_data.dropna(subset=avail_proxies, how='all').copy()
                    
                    # CHANGE 1: Filter out untrimmed section tail rows
                    mbsf_temp = df_clean['Base_Scaled_Depth']
                    valid_mask = (mbsf_temp >= sec.drilled_top) & (mbsf_temp <= sec.drilled_bottom)
                    df_clean = df_clean[valid_mask]
                    
                    if df_clean.empty:
                        continue
                        
                    mbsf = df_clean['Base_Scaled_Depth']
                    orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
                    mcd = (mbsf - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
                    
                    sec_depth_col = next((c for c in df_clean.columns if 'offset' in c.lower() or 'cm' in c.lower() or 'in section' in c.lower()), None)
                    sec_depth_vals = df_clean[sec_depth_col] if sec_depth_col else np.nan
                    
                    orig_depth_vals = df_clean['Depth']
                    
                    out_df = pd.DataFrame({
                        "Leg": leg_val,
                        "Site": site_val,
                        "Hole": hole_val,
                        "Core": core.core_id,
                        "Section": df_clean['Sc'],
                        "Depth in Section (cm)": sec_depth_vals,
                        "Depth (mbsf)": round(orig_depth_vals, 3),
                        "Depth MCD": round(mcd, 3)
                    })
                    
                    for p in avail_proxies:
                        # Map messy actual names to perfectly uniform columns before appending
                        p_upper = str(p).strip().upper()
                        if p_upper in ['L*', 'L', 'LSTAR', 'REFLECTANCE L*']:
                            out_col = 'L*'
                        elif p_upper in ['A*', 'A', 'ASTAR', 'REFLECTANCE A*']:
                            out_col = 'a*'
                        elif p_upper in ['B*', 'B', 'BSTAR', 'REFLECTANCE B*']:
                            out_col = 'b*'
                        else:
                            out_col = p
        
                        if out_col not in out_df.columns:
                            out_df[out_col] = df_clean[p]
                        else:
                            # If the column already exists, only fill NaNs; don't overwrite valid data
                            out_df[out_col] = out_df[out_col].fillna(df_clean[p])
                        
                    out_df['Status'] = 'on-splice' if sec.is_locked else 'off-splice'
                    hole_dfs.append(out_df)
                    
                    # CHANGE 2: Squeeze Master Splice rows between splice_top_mcd and splice_bot_mcd
                    if sec.is_locked:
                        ms_df = out_df.copy()
                        
                        top_b = getattr(sec, 'splice_top_mcd', None)
                        bot_b = getattr(sec, 'splice_bot_mcd', None)
                        
                        if top_b is not None and bot_b is not None:
                            ms_df = ms_df[(ms_df['Depth MCD'] >= round(top_b, 3)) & 
                                          (ms_df['Depth MCD'] < round(bot_b, 3))]
                                          
                        if not ms_df.empty:
                            ms_df.drop(columns=['Status'], inplace=True, errors='ignore')
                            master_splice_dfs.append(ms_df)
                        
            if hole_dfs:
                df_hole = pd.concat(hole_dfs, ignore_index=True)
                df_hole.sort_values(by='Depth MCD', inplace=True)
                
                safe_group = re.sub(r'[\\/*?:"<>|]', "", group_name)
                safe_h_name = re.sub(r'[\\/*?:"<>|]', "", str(h_name))
                
                filename_hole = f"Export_Hole_{safe_h_name}_{safe_group}.csv"
                df_hole.to_csv(filename_hole, index=False)
                print(f"  -> Saved: {filename_hole}")
                
        if master_splice_dfs:
            df_ms = pd.concat(master_splice_dfs, ignore_index=True)
            df_ms.sort_values(by='Depth MCD', inplace=True)
            df_ms.drop_duplicates(subset=['Hole', 'Core', 'Section', 'Depth MCD'], inplace=True)
            
            safe_group = re.sub(r'[\\/*?:"<>|]', "", group_name)
            filename_ms = f"Export_MasterSplice_{safe_group}.csv"
            df_ms.to_csv(filename_ms, index=False)
            print(f"  -> Saved: {filename_ms}")
            
    print("Export Complete. Check your directory.")
    
def load_core_photo(core, data_dir):
    if not data_dir:
        core.photo_array = None
        return
        
    # Strip all punctuation from target to enforce strict matching (e.g., "798A" + "1H" -> "798A1H")
    target_id = re.sub(r'[\W_]+', '', f"{core.hole_name}{core.core_id}").upper()
    
    # Grab all potential vertical PNGs
    search_pattern = os.path.join(data_dir, "*_vertical.[pP][nN][gG]")
    all_pngs = glob.glob(search_pattern)
    
    matched_file = None
    for pfile in all_pngs:
        fname = os.path.basename(pfile)
        # Clean the filename the exact same way for a perfect comparison
        clean_fname = fname.lower().replace("_vertical.png", "")
        clean_fname = re.sub(r'[\W_]+', '', clean_fname).upper()
        
        if clean_fname == target_id:
            matched_file = pfile
            break
            
    if matched_file:
        try:
            img = plt.imread(matched_file)
            
            h, w = img.shape[:2]
            margin = int(w * 0.20)
            img_cropped = img[:, margin:w-margin]
            
            # Transpose to lay horizontally for the GUI
            core.photo_array = np.transpose(img_cropped, (1, 0, 2))
            
            print(f"SUCCESS: Loaded and matched {matched_file} to {target_id}")
        except Exception as e:
            print(f"Warning: Found {matched_file} but could not load it: {e}")
            core.photo_array = None
    else:
        print(f"DEBUG: No exact photo match found for {target_id}")
        core.photo_array = None
        
def export_composite_photo(builder, filename="Composite_Photo.pdf"):
    print("Generating composite PDF from external affine table...")
    
    def slice_photo(core, req_top, req_bot, affine_shift=0):
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

        # Slice and rotate so depth is plotted on the x-axis
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
                 None
    
            sliced = photo_arr[:, x_start:x_end, :]

        return sliced
    
    locked_sections = []
    # Gather locked sections natively generated by load_external_affine
    for h_name, hole in builder.holes.items():
        for core in hole.cores:
            for sec in core.sections:
                if sec.is_locked and getattr(core, 'photo_array', None) is not None:
                    # Rely on the bounds safely assigned during the external load
                    mcd_top = sec.splice_top_mcd
                    mcd_bot = sec.splice_bot_mcd
                    locked_sections.append((mcd_top, mcd_bot, core, sec))
                    
    if not locked_sections:
        print("No photos found on the master splice to export.")
        return
        
    locked_sections.sort(key=lambda x: x[0])
    
    fig, ax = plt.subplots(figsize=(24, 4))
    min_mcd = float('inf')
    max_mcd = float('-inf')
    
    # Slice and plot
    for mcd_top, mcd_bot, core, sec in locked_sections:
        
        # Retrieve the affine shift for this core
        shift = getattr(core, 'affine_shift', 0)
        
        # Pass the MCD splice bounds and the shift
        sliced = slice_photo(core, mcd_top, mcd_bot, affine_shift=shift)
        
        if sliced is not None and sliced.size > 0:
            ax.imshow(sliced, extent=[mcd_top, mcd_bot, 0, 1], aspect='auto')
            min_mcd = min(min_mcd, mcd_top)
            max_mcd = max(max_mcd, mcd_bot)
            
    if min_mcd == float('inf'):
        print("Failed to slice any valid photos.")
        plt.close(fig)
        return
        
    # formatting
    ax.set_xlim(min_mcd, max_mcd)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(1.5)
    ax.tick_params(axis='x', which='major', labelsize=11, length=6, width=1.2, direction='out')
    ax.tick_params(axis='x', which='minor', length=3.5, width=0.8, direction='out')
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.set_xlabel("Composite Depth (MCD)", fontweight='bold', fontsize=12, labelpad=8)
    
    try:
        fig.savefig(filename, format='pdf', bbox_inches='tight', dpi=300)
        print(f"SUCCESS: External Splice PDF saved to {filename}")
    except Exception as e:
        print(f"Error saving PDF: {e}")
    finally:
        plt.close(fig)