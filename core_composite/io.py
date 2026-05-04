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

def load_from_multiple_files(hole_name, odp_summary_csv, hole_data_files, proxy_keywords=['density']):
    new_hole = Hole(hole_name)
    summary_df = pd.read_csv(odp_summary_csv)
    
    """
    This function loads DSDP / ODP / IODP physical properties data from Janus / LIMS into the Hole, Core, 
    and Section classes in a coherent way. I so very strongly advise you do not mess with this.
    """
    
    # Remove whitespace from summary headers
    # Fix for loading problems
    summary_df.rename(columns=lambda x: str(x).strip(), inplace=True)
    
    hole_letter = hole_name[-1].upper()
    hole_summary = summary_df[summary_df['H'].astype(str).str.strip().str.upper() == hole_letter]
    
    combined_data = pd.DataFrame()
    
    for file in hole_data_files:
        df = pd.read_csv(file)
        
        df.rename(columns=lambda x: str(x).strip(), inplace=True)
        
        depth_col = next((c for c in df.columns if ('mbsf' in c.lower() or 'depth' in c.lower() or 'csf' in c.lower()) and 'mcd' not in c.lower()), None)
        if depth_col: df.rename(columns={depth_col: 'Depth'}, inplace=True)
        
        core_col = next((c for c in df.columns if c.lower() in ['core', 'cor']), None)
        if core_col: df.rename(columns={core_col: 'Core'}, inplace=True)
        
        combined_data = pd.concat([combined_data, df], ignore_index=True)
        
    if not combined_data.empty and 'Depth' in combined_data.columns and 'Core' in combined_data.columns:
        combined_data.sort_values(by=['Core', 'Depth'], inplace=True)
        combined_data['Core_Clean'] = combined_data['Core'].astype(str).str.extract(r'(\d+)')[0]
        
    for _, row in hole_summary.iterrows():
        core_num = str(row['Cor']).strip().split('.')[0]
        core_type = str(row['T']).strip() if str(row['T']).lower() != 'nan' else ''
        cid = f"{core_num}{core_type}" # changed variable name from Core ID in earlier version
        core_mask = combined_data['Core_Clean'] == core_num
        core_data_slice = combined_data[core_mask]
        if not core_data_slice.empty:
            drilled_top = float(row['Top(mbsf)'])
            drilled_bottom = drilled_top + float(row['Cored(m)'])
            new_core = Core(hole_name, cid, core_data_slice, drilled_top, drilled_bottom, proxy_keywords)
            if new_core.active_proxies:
                new_core.compress_depth_and_split(chunk_size=1.0)
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
    
    top_mcd_col = next((c for c in df.columns if 'comp top' in c or 'mcd top' in c), None)
    bot_mcd_col = next((c for c in df.columns if 'comp bot' in c or 'mcd bot' in c), None)
    
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
                    if top_mcd_col and not pd.isna(row[top_mcd_col]):
                        top_mcd = float(row[top_mcd_col])
                        raw_top = sec.drilled_top + ((top_mcd - shift_val - sec.drilled_top) / stretch_val)
                    else:
                        raw_top = -np.inf
                        
                    if bot_mcd_col and not pd.isna(row[bot_mcd_col]):
                        bot_mcd = float(row[bot_mcd_col])
                        raw_bot = sec.drilled_top + ((bot_mcd - shift_val - sec.drilled_top) / stretch_val)
                    else:
                        raw_bot = np.inf
                        
                    # Non-destructively split the data into 3 chunks
                    df_data = sec.scaled_data
                    df_top = df_data[df_data['Base_Scaled_Depth'] < raw_top].copy()
                    df_splice = df_data[(df_data['Base_Scaled_Depth'] >= raw_top) & (df_data['Base_Scaled_Depth'] <= raw_bot)].copy()
                    df_bot = df_data[df_data['Base_Scaled_Depth'] > raw_bot].copy()
                    
                    # Save the top off-splice tail
                    if not df_top.empty:
                        sec_top = copy.deepcopy(sec)
                        sec_top.scaled_data = df_top
                        sec_top.drilled_top = df_top['Base_Scaled_Depth'].min()
                        sec_top.drilled_bottom = df_top['Base_Scaled_Depth'].max()
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
                        sec_splice.affine_shift = shift_val
                        sec_splice.stretch_factor = stretch_val
                        sec_splice.is_locked = True
                        new_sections.append(sec_splice)
                        
                    # Save the bottom off-splice tail
                    if not df_bot.empty:
                        sec_bot = copy.deepcopy(sec)
                        sec_bot.scaled_data = df_bot
                        sec_bot.drilled_top = df_bot['Base_Scaled_Depth'].min()
                        sec_bot.drilled_bottom = df_bot['Base_Scaled_Depth'].max()
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
    This captures the final state after all automated and manual tweaks.
    """
    
    print(f"\n Exporting Final Affine/Splice Table")
    records = []
    
    for h_name, hole in builder.holes.items():
        for core in hole.cores:
            for sec in core.sections:
                # Calculate MCD bounds
                top_mcd = sec.drilled_top + sec.affine_shift
                bot_mcd = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                
                records.append({
                    'Hole': sec.hole_name,
                    'Core': sec.core_id,
                    'Section': sec.section_id,
                    'Top_Drilled_mbsf': round(sec.drilled_top, 3),
                    'Bot_Drilled_mbsf': round(sec.drilled_bottom, 3),
                    'Top_MCD': round(top_mcd, 3),
                    'Bot_MCD': round(bot_mcd, 3),
                    'Affine_Shift_m': round(sec.affine_shift, 4),
                    'Stretch_Factor': round(sec.stretch_factor, 4),
                    'Status': 'On-Splice' if sec.is_locked else 'Off-Splice'
                })
    
    if records:
        df = pd.DataFrame(records)
        
        # Sort by Hole -> Core -> Top Depth
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
    print("\n Starting Data Export ")
    
    # Loop through every data type (proxy)
    for proxy in all_proxies:
        master_splice_dfs = []
        
        # Loop through every hole
        for h_name, hole in builder.holes.items():
            
            # Skip holes that are turned off in the UI
            if h_name not in active_holes:
                continue
            
            hole_dfs = []
            
            for core in hole.cores:
                
                # Skip cores that aren't tied into the main splice
                is_activated = any(sec.is_locked for sec in core.sections)
                if not is_activated:
                    continue
                    
                for sec in core.sections:
                    if proxy not in sec.scaled_data.columns:
                        continue
                        
                    # Grab valid data for this proxy (Preserves original columns exactly as imported)
                    df_clean = sec.scaled_data.dropna(subset=[proxy]).copy()
                    if df_clean.empty:
                        continue
                        
                    # Run the final mathematical offsets for MCD
                    mbsf = df_clean['Base_Scaled_Depth']
                    mcd = (mbsf - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
                    
                    # only add the specific calculated columns
                    df_clean['Depth (mcd)'] = mcd
                    df_clean['Status'] = 'on-splice' if sec.is_locked else 'off-splice'
                    
                    df_clean['Hole'] = h_name
                    df_clean['Core'] = core.core_id
                    df_clean['Section'] = sec.section_id
                    
                    # Add this dataframe block to our hole export list
                    hole_dfs.append(df_clean)
                    
                    # If it's locked, it belongs in the Master Splice export too
                    if sec.is_locked:
                        ms_df = df_clean.copy()
                        ms_df.drop(columns=['Status'], inplace=True, errors='ignore')
                        master_splice_dfs.append(ms_df)
                            
            # Save the specific Hole Data
            if hole_dfs:
                df_hole = pd.concat(hole_dfs, ignore_index=True)
                df_hole.sort_values(by='Depth (mcd)', inplace=True)
                
                # Optional: If you want to drop internal calculation columns generated by your loader script
                df_hole.drop(columns=['Base_Scaled_Depth', 'Virtual_Section', 'Core_Clean'], inplace=True, errors='ignore')
                
                safe_proxy = re.sub(r'[\\/*?:"<>|]', "", proxy)
                filename_hole = f"Export_Hole_{h_name}_{safe_proxy}.csv"
                df_hole.to_csv(filename_hole, index=False)
                print(f"  -> Saved: {filename_hole}")
                
        # Save the Master Splice Data
        if master_splice_dfs:
            df_ms = pd.concat(master_splice_dfs, ignore_index=True)
            df_ms.sort_values(by='Depth (mcd)', inplace=True)
            
            # Same internal column cleanup for the Master Splice
            df_ms.drop(columns=['Base_Scaled_Depth', 'Virtual_Section', 'Core_Clean'], inplace=True, errors='ignore')
            
            safe_proxy = re.sub(r'[\\/*?:"<>|]', "", proxy)
            filename_ms = f"Export_MasterSplice_{safe_proxy}.csv"
            df_ms.to_csv(filename_ms, index=False)
            print(f"Saved: {filename_ms}")
            
    print("Export Complete. Check your directory.")
    

def map_subsamples_to_mcd(builder, csv_path, output_filename="Mapped_Subsamples.csv"):
    """
    Takes an external CSV of subsample data (e.g., benthic oxygen isotopes) and 
    calculates their Composite Depth (MCD) using the current affine/splice model.
    """

    print(f"\nMapping Subsamples to MCD from {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return
        
    # Fuzzy match columns (case insensitive)
    hole_col = next((c for c in df.columns if 'hole' in c.lower()), None)
    core_col = next((c for c in df.columns if 'core' in c.lower()), None)
    sec_col = next((c for c in df.columns if 'sec' in c.lower() and 'sed' not in c.lower()), None)
    
    # Look for the original depth column (ignore any old MCD columns if they exist)
    depth_col = next((c for c in df.columns if 'depth' in c.lower() and 'mcd' not in c.lower() and 'comp' not in c.lower()), None)
    
    if not hole_col or not core_col or not depth_col:
        print("Error: Subsample CSV must contain at least 'Hole', 'Core', and 'Depth' (mbsf) columns.")
        return
        
    mcd_values = []
    
    for idx, row in df.iterrows():
        raw_hole = str(row[hole_col]).strip()
        raw_core = str(row[core_col]).strip()
        raw_depth = float(row[depth_col]) if not pd.isna(row[depth_col]) else np.nan
        
        if pd.isna(raw_depth):
            mcd_values.append(np.nan)
            continue
            
        # Match the Hole
        target_hole = None
        for h_name, h_obj in builder.holes.items():
            if h_name.endswith(raw_hole) or raw_hole.endswith(h_name):
                target_hole = h_obj
                break
        if not target_hole:
            mcd_values.append(np.nan)
            continue
            
        # Match the Core (ignoring letters like 'H' or 'X')
        target_core = None
        
        # If pandas added a '.0', chop it off before doing the regex
        # regex = regular expression pattern, the search pattern used for matching
        if raw_core.endswith('.0'):
            raw_core = raw_core[:-2]
            
        core_num_csv = re.sub(r'\D', '', raw_core)
        for c_obj in target_hole.cores:
            core_num_obj = re.sub(r'\D', '', str(c_obj.core_id))
            if core_num_obj == core_num_csv:
                target_core = c_obj
                break
        if not target_core:
            mcd_values.append(np.nan)
            continue
            
        # Match the Section 
        target_sec = None
        if sec_col and not pd.isna(row[sec_col]):
            raw_sec = str(row[sec_col]).strip()
            for s_obj in target_core.sections:
                if str(s_obj.section_id) == raw_sec:
                    target_sec = s_obj
                    break
        
        # If no Section column is provided in the CSV, find which section's depths contain the sample
        if not target_sec:
            for s_obj in target_core.sections:
                if s_obj.drilled_top <= raw_depth <= s_obj.drilled_bottom:
                    target_sec = s_obj
                    break
            # Just use the core's affine shift if it fell in a gap
            if not target_sec and target_core.sections:
                target_sec = target_core.sections[0]
                
        if not target_sec:
            mcd_values.append(np.nan)
            continue
            
        # Calculate the precise MCD
        st = getattr(target_sec, 'stretch_factor', 1.0)
        mcd = (raw_depth - target_sec.drilled_top) * st + target_sec.drilled_top + target_sec.affine_shift
        mcd_values.append(mcd)
        
    # Append the new data and save
    df['Depth (mcd)'] = mcd_values
    df.to_csv(output_filename, index=False)
    
    success_count = len([m for m in mcd_values if not pd.isna(m)])
    print(f" Successfully mapped {success_count} samples to the Composite Depth scale")
    print(f" Saved to: {output_filename}")
    
def export_project_data(builder_obj, output_prefix="Core_Composite_Master"):
    """
    Extracts the final alignment data from the CompositeBuilder and exports 
    the Affine Table (shifts/stretches) and the Master Splice Record to CSVs.
    """
    print(f"\nExporting project data with prefix '{output_prefix}'...")
    
    # 1. Build and Export the Affine Table
    affine_data = []
    for h_name, hole in builder_obj.holes.items():
        for core in hole.cores:
            for sec in core.sections:
                affine_data.append({
                    'Hole': h_name,
                    'Core': core.core_id,
                    'Section': sec.section_id,
                    'Top_Depth_Drilled (mbsf)': sec.drilled_top,
                    'Bottom_Depth_Drilled (mbsf)': sec.drilled_bottom,
                    'Affine_Shift (m)': getattr(sec, 'affine_shift', 0.0),
                    'Stretch_Factor': getattr(sec, 'stretch_factor', 1.0),
                    'On_Splice': getattr(sec, 'is_locked', False)
                })
                
    if affine_data:
        affine_df = pd.DataFrame(affine_data)
        affine_filename = f"{output_prefix}_Affine_Table.csv"
        affine_df.to_csv(affine_filename, index=False)
        print(f"  -> Saved Affine Table: {affine_filename}")
        
    # 2. Export the Splice Record
    if hasattr(builder_obj, 'splice') and builder_obj.splice is not None:
        if builder_obj.splice.intervals:
            splice_df = pd.DataFrame(builder_obj.splice.intervals)
            splice_filename = f"{output_prefix}_Splice_Record.csv"
            splice_df.to_csv(splice_filename, index=False)
            print(f"  -> Saved Master Splice Record: {splice_filename}")
        else:
            print("  -> No splice intervals found to export.")
            
    print("Export complete.")