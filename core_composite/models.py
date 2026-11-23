# -*- coding: utf-8 -*-
"""
Created on Fri May  1 06:02:41 2026

@author: joseph novak

These are the data structure classes for core composite.
"""

import pandas as pd
import numpy as np
from pandas.api.indexers import BaseIndexer

"""
The section, core, and hole classes are major organizing features of the script that 
tell core_composite how to properly handle scientific drilling data.
"""
class Section:
    def __init__(self, hole_name, core_id, section_id, section_data, proxies, is_locked=False):
        """
        Definitions for the variables in this class.
        """
        self.hole_name = hole_name # Data organized by hole
        self.core_id = str(core_id) # organize data within a hole by core
        self.section_id = str(section_id) # organize data within a core by section
        self.scaled_data = section_data.copy() # depth mbsf, scaled to deal with a recovery factor > 1.0
        self.proxies = proxies # physical properties or colorimetry data
        
        self.drilled_top = self.scaled_data['Base_Scaled_Depth'].min() # topmost depth within a core section
        self.drilled_bottom = self.scaled_data['Base_Scaled_Depth'].max() # bottom depth within a core section
        self.drilled_length = self.drilled_bottom - self.drilled_top # length of the core section
        
        self.is_locked = is_locked # tells the algorithm that the Depth (MCD) of a chunk cannot be changed
        self.stretch_factor = 1.0 #S_f 
        self.affine_shift = 0.0 #Shift_affine
        self.last_r_score = np.nan #R_penalized
        
    def split_at_depth(self, split_drilled_depth):
        if split_drilled_depth <= self.drilled_top or split_drilled_depth >= self.drilled_bottom:
            return None
        
        orig_top = getattr(self, 'original_drilled_top', self.drilled_top)
        orig_bot = getattr(self, 'original_drilled_bottom', self.drilled_bottom)
        
        # Use strict < on top_data so the exact cut point isn't duplicated in both chunks
        top_data = self.scaled_data[self.scaled_data['Base_Scaled_Depth'] < split_drilled_depth].copy()
        bot_data = self.scaled_data[self.scaled_data['Base_Scaled_Depth'] >= split_drilled_depth].copy()
        
        if top_data.empty or bot_data.empty:
            return None

        top_sec = Section(self.hole_name, self.core_id, f"{self.section_id}a", top_data, self.proxies, is_locked=True)
        bot_sec = Section(self.hole_name, self.core_id, f"{self.section_id}b", bot_data, self.proxies, is_locked=False)
        
        # preserve anchor depths
        top_sec.original_drilled_top = orig_top
        top_sec.original_drilled_bottom = orig_bot
        bot_sec.original_drilled_top = orig_top
        bot_sec.original_drilled_bottom = orig_bot
        
        # preserve affine shifts and stretch factors
        top_sec.affine_shift = self.affine_shift
        bot_sec.affine_shift = self.affine_shift
        top_sec.stretch_factor = self.stretch_factor
        bot_sec.stretch_factor = self.stretch_factor
        
        return top_sec, bot_sec

class Core:
    def __init__(self, hole_name, core_id, core_df, drilled_top, drilled_bottom, recovered_length, proxy_keywords):
        """
        Definitions for the variables in this class.
        """
        
        self.hole_name = hole_name
        self.core_id = str(core_id)
        self.data = core_df.copy() 
        
        depth_col = next((c for c in self.data.columns if ('mbsf' in c.lower() or 'depth' in c.lower() or 'csf' in c.lower()) and 'mcd' not in c.lower()), None)
        if not depth_col: raise ValueError(f"Missing depth column for Core {core_id}")
        self.data.rename(columns={depth_col: 'Depth'}, inplace=True)
        
        # Force the depth to be numeric
        # Addresses issues with some legacy files
        self.data['Depth'] = pd.to_numeric(self.data['Depth'], errors='coerce')
        self.data.dropna(subset=['Depth'], inplace=True) 
        
        # Sort by depth and remove duplicates
        self.data.sort_values(by='Depth', ascending=True, inplace=True)
        self.data.drop_duplicates(subset=['Depth'], keep='first', inplace=True)
        self.data.reset_index(drop=True, inplace=True)
        
        # Flexible structure that creates a variable for each of the "proxy" data types 
        # (here proxy means density, magsus, L*, etc.) in the file
        self.active_proxies = []
        for kw in proxy_keywords: #kw means "Keyword"
            match = next((c for c in self.data.columns if kw.lower() in c.lower()), None)
            if match:
                std_name = kw.capitalize()
                self.data.rename(columns={match: std_name}, inplace=True)
                self.data[std_name] = pd.to_numeric(self.data[std_name], errors='coerce')
                self.active_proxies.append(std_name)
                
        # Outlier removal by depth-based rolling window
        physical_window_m = 0.25  
        std_multiplier = 4.0      
        
        depth_indexer = DepthWindowIndexer(index_array=self.data['Depth'].values, window_size=physical_window_m)
        
        for proxy in self.active_proxies:
            rolling_median = self.data[proxy].rolling(depth_indexer, min_periods=3).median()
            rolling_std = self.data[proxy].rolling(depth_indexer, min_periods=3).std()
            
            rolling_std = rolling_std.fillna(self.data[proxy].std())
            
            lower_bound = rolling_median - (std_multiplier * rolling_std)
            upper_bound = rolling_median + (std_multiplier * rolling_std)
            
            outlier_mask = (self.data[proxy] < lower_bound) | (self.data[proxy] > upper_bound)
            if proxy.lower() == 'density': 
                outlier_mask = outlier_mask | (self.data[proxy] < 1.0) # density of water
                outlier_mask = outlier_mask | (self.data[proxy] > 3.4) # max density of peridotite
                
            self.data.loc[outlier_mask, proxy] = np.nan
            
        # Bringing in our relevant variables from the section class
        self.data.dropna(subset=self.active_proxies, how='all', inplace=True)
        self.drilled_top = drilled_top
        self.drilled_bottom = drilled_bottom
        self.drilled_length = drilled_bottom - drilled_top
        self.recovered_length = recovered_length
        self.scaled_data = None 
        self.sections = []

    def compress_depth_and_split(self, chunk_size=1.0, compress_depth=True):
        """
        This function applies (1) any necessary compression if drilled length < recovered length and
        (2) the function that splits on-splice from off-splice data.
        
        If compress_depth is False, scaled depth is set equal to depth (mbsf) to align 
        with legacy MCD values that did not account for excess recovery.
        Default chunk size is set to 1 meter.
        """
        if self.data.empty: return
    
        self.scaled_data = self.data.copy()
        
        if compress_depth:
            # Calculate recovery factor based on the summary file
            rf = min(1.0, self.drilled_length / self.recovered_length) if self.recovered_length > 0 else 1.0
            self.scaled_data['Base_Scaled_Depth'] = self.drilled_top + ((self.data['Depth'] - self.drilled_top) * rf)
        else:
            # Bypass compression entirely for legacy splice compatibility
            self.scaled_data['Base_Scaled_Depth'] = self.data['Depth']
    
        # Making the chunks
        min_d = self.scaled_data['Base_Scaled_Depth'].min()
        max_d = self.scaled_data['Base_Scaled_Depth'].max()
        bins = np.arange(min_d, max_d + chunk_size, chunk_size)
        if len(bins) == 1: bins = np.append(bins, max_d + chunk_size)
        
        self.scaled_data['Virtual_Section'] = pd.cut(self.scaled_data['Base_Scaled_Depth'], bins, include_lowest=True, labels=False)
    
        for sect_id, group in self.scaled_data.groupby('Virtual_Section'):
            if len(group) > 5:
                self.sections.append(Section(self.hole_name, self.core_id, str(sect_id), group, self.active_proxies))
            
            if not self.sections:
                self.sections.append(Section(self.hole_name, self.core_id, "1", self.scaled_data, self.active_proxies))

    def apply_splice_cut(self, splice_mcd):
        """Cuts the master core at splice_mcd, retaining data above as locked."""
        new_sections = []
        for sec in self.sections:
            if not sec.is_locked:
                new_sections.append(sec)
                continue
            
            orig_top = getattr(sec, 'original_drilled_top', sec.drilled_top)
            vis_top = (sec.drilled_top - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
            vis_bot = (sec.drilled_bottom - orig_top) * sec.stretch_factor + orig_top + sec.affine_shift
            
            if vis_top <= splice_mcd <= vis_bot:
                relative_mcd = splice_mcd - sec.affine_shift - orig_top
                raw_cut_depth = orig_top + (relative_mcd / sec.stretch_factor)
                
                split_res = sec.split_at_depth(raw_cut_depth)
                if split_res:
                    top_sec, bot_sec = split_res
                    top_sec.is_locked = True
                    bot_sec.is_locked = False
                    
                    # Store exact MCD bounds on the locked section
                    top_sec.splice_top_mcd = vis_top
                    top_sec.splice_bot_mcd = splice_mcd
                    
                    new_sections.extend([top_sec, bot_sec])
                else:
                    new_sections.append(sec)
            else:
                new_sections.append(sec)
                
        self.sections = new_sections

    def apply_candidate_cut(self, raw_click_depth):
        """Cuts candidate core at raw_click_depth, locking deeper data."""
        new_sections = []
        for sec in self.sections:
            if sec.drilled_top <= raw_click_depth <= sec.drilled_bottom:
                split_res = sec.split_at_depth(raw_click_depth)
                if split_res:
                    top_sec, bot_sec = split_res
                    top_sec.is_locked = False
                    bot_sec.is_locked = True
                    
                    orig_top = getattr(bot_sec, 'original_drilled_top', bot_sec.drilled_top)
                    bot_sec.splice_top_mcd = (bot_sec.drilled_top - orig_top) * bot_sec.stretch_factor + orig_top + bot_sec.affine_shift
                    bot_sec.splice_bot_mcd = (bot_sec.drilled_bottom - orig_top) * bot_sec.stretch_factor + orig_top + bot_sec.affine_shift
                    
                    new_sections.extend([top_sec, bot_sec])
                else:
                    new_sections.append(sec)
            else:
                new_sections.append(sec)
                
        self.sections = new_sections

class Hole:
    def __init__(self, hole_name, leg = ""):
        """
        Definitions for the variables in this class.
        """
        self.hole_name = hole_name
        self.leg = leg
        self.cores = []

    def get_positioned_data(self):
        """
        Applies compression, affine shifts, and stretch factor calculations in the Hole class.
        """
        all_dfs = []
        for c in self.cores:
            for s in c.sections:
                df = s.scaled_data.copy()
                base_top = df['Base_Scaled_Depth'].min()
                shifted_top = base_top + s.affine_shift
                df['MCD'] = shifted_top + (df['Base_Scaled_Depth'] - base_top) * s.stretch_factor
                df['Is_Locked'] = s.is_locked
                all_dfs.append(df)
        return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()


class SpliceRecord:
    """
    Manages the composite section / main splice. The script treats the 
    composite section / main splice as a new hole built out of snippets from real holes.
    
    The hole thing falls apart without this section of code.
    """
    def __init__(self):
        self.intervals = [] # List of dictionaries representing splice snippets

    def append_tie(self, top_mcd, bot_mcd, hole_name, core_id, top_drilled, bot_drilled):
        """
        Records a segment of a core that makes up the composite section
        """
        self.intervals.append({
            'Top_MCD': top_mcd,
            'Bot_MCD': bot_mcd,
            'Hole': hole_name,
            'Core': core_id,
            'Top_Drilled': top_drilled,
            'Bot_Drilled': bot_drilled
        })
        
    def get_splice_dataframe(self, builder_obj):
        """
        Gathers composite section data by strictly filtering each core's 
        data to the Top_MCD and Bot_MCD boundaries recorded in self.intervals.
        """
        if not self.intervals:
            # Fallback if no ties were recorded in SpliceRecord
            print("Warning: No ties found in SpliceRecord. intervals list is empty.")
            return pd.DataFrame()

        splice_dfs = []

        # Iterate over every interval tie logged in the splice
        for tie in self.intervals:
            hole_name = tie['Hole']
            core_id = str(tie['Core'])
            top_mcd = tie['Top_MCD']
            bot_mcd = tie['Bot_MCD']

            # Retrieve the specific hole
            hole = builder_obj.holes.get(hole_name)
            if not hole:
                continue

            # Fetch all MCD-positioned data for this hole
            hole_data = hole.get_positioned_data()
            if hole_data.empty:
                continue

            # Filter data belonging only to this specific core and strictly within the tie MCD bounds
            core_mask = (hole_data['Core'].astype(str) == core_id) if 'Core' in hole_data.columns else True
            
            # Extract data mathematically bounded between top_mcd and bot_mcd
            tie_data = hole_data[
                core_mask & 
                (hole_data['MCD'] >= top_mcd) & 
                (hole_data['MCD'] <= bot_mcd)
            ].copy()

            if not tie_data.empty:
                splice_dfs.append(tie_data)

        if splice_dfs:
            combined = pd.concat(splice_dfs, ignore_index=True)
            return combined.sort_values(by='MCD').reset_index(drop=True)
            
        return pd.DataFrame()

class DepthWindowIndexer(BaseIndexer):
    """
    Depth-smart outlier detection, executed within the Core object.
    """
    def get_window_bounds(self, num_values, min_periods, center, closed, step):
        depths = self.index_array
        half_window = self.window_size / 2.0
        start = np.searchsorted(depths, depths - half_window, side='left')
        end = np.searchsorted(depths, depths + half_window, side='right')
        return start, end