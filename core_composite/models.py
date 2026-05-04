# -*- coding: utf-8 -*-
"""
Created on Fri May  1 06:02:41 2026

@author: joseph novak

These are the data structure classes for core composite.
"""

import pandas as pd
import numpy as np


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
        """
        This function handles the logic for the transition from on-splice to off-splice within a section.
        
        The section is split at the on-splice / off-splice boundary, and the off-splice
        data is then tagged as a chunk that can be stretched or compressed later by CompositeBuilder.
        """
        if split_drilled_depth <= self.drilled_top or split_drilled_depth >= self.drilled_bottom:
            return None # Sometimes there are data without depth assignments in ODP data files. IDK why, but this logic handles that problem.
        
        # splitting the data up
        top_data = self.scaled_data[self.scaled_data['Base_Scaled_Depth'] <= split_drilled_depth]
        bot_data = self.scaled_data[self.scaled_data['Base_Scaled_Depth'] > split_drilled_depth]
        
        # The top piece becomes is locked as part of the composite section / splice
        top_sec = Section(self.hole_name, self.core_id, f"{self.section_id}a", top_data, self.proxies, is_locked=True)
        # The bottom piece remains unlocked as part of the off-splice materials
        bot_sec = Section(self.hole_name, self.core_id, f"{self.section_id}b", bot_data, self.proxies, is_locked=False)
        
        # Keeps continuity of affine shifts and stretch factors between chunks
        # The alignments become completely nonsensical if this is not here
        top_sec.affine_shift = self.affine_shift
        bot_sec.affine_shift = self.affine_shift
        top_sec.stretch_factor = self.stretch_factor
        bot_sec.stretch_factor = self.stretch_factor
        
        return top_sec, bot_sec

class Core:
    def __init__(self, hole_name, core_id, core_df, drilled_top, drilled_bottom, proxy_keywords):
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
                
        # Outlier removal
        # This is just meant to deal with isolated extreme values
        outlier_multiplier = 3.0 
        for proxy in self.active_proxies:
            Q1 = self.data[proxy].quantile(0.25)
            Q3 = self.data[proxy].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - (outlier_multiplier * IQR)
            upper_bound = Q3 + (outlier_multiplier * IQR)
            if proxy == 'Density': lower_bound = max(lower_bound, 1.15) 
            outlier_mask = (self.data[proxy] < lower_bound) | (self.data[proxy] > upper_bound)
            self.data.loc[outlier_mask, proxy] = np.nan
            
        # Bringing in our relevant variables from the section class
        self.data.dropna(subset=self.active_proxies, how='all', inplace=True)
        self.drilled_top = drilled_top
        self.drilled_bottom = drilled_bottom
        self.drilled_length = drilled_bottom - drilled_top
        self.scaled_data = None 
        self.sections = []

    def compress_depth_and_split(self, chunk_size=1.0):
        """
        This function applies (1) any necessary compression if drilled length < recovered length and
        (2) the function that splits on-splice from off-splice data.
        
        Default chunk size is set to 1 meter.
        """
        if self.data.empty: return
        recovered_length = self.data['Depth'].max() - self.data['Depth'].min()
        # calculating R_f from Equation 11
        rf = min(1.0, self.drilled_length / recovered_length) if recovered_length > 0 else 1.0
        
        self.scaled_data = self.data.copy()
        
        # Equation 11 from the manuscript
        self.scaled_data['Base_Scaled_Depth'] = self.drilled_top + ((self.data['Depth'] - self.data['Depth'].min()) * rf)
        
        # making the chunks
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
        """
        When the user is using the SpliceBuilderGUI to make a new splice, this function
        cuts the current "master core" where the user selects a tie point to the parallel bore hole
        (the "master core" refers to the core that is currently the basis of the deepest
        portion of the splice that is being actively built) and "discards" any data in the core that are
        deeper than the new tiepoint as "off-splice" data.
        
        Those deeper data in the core will be aligned to the composite section later by CompositeBuilder.
        
        Note: the logic here assumes that you are building the splice from the top down, per standard
        ODP / IODP convention.
        
        """
        for sec in self.sections:
            if not sec.is_locked: continue
            
            # Calculate the visual boundaries of this section for the GUI
            vis_top = sec.drilled_top + sec.affine_shift
            vis_bot = (sec.drilled_bottom - sec.drilled_top) * sec.stretch_factor + sec.drilled_top + sec.affine_shift
            
            # If the cut falls inside this section
            if vis_top <= splice_mcd <= vis_bot:
                # Convert MCD back to Depth (mbsf)
                relative_mcd = splice_mcd - sec.affine_shift - sec.drilled_top
                raw_cut_depth = sec.drilled_top + (relative_mcd / sec.stretch_factor)
                
                # Filter the dataframe to only keep data above the cut
                sec.scaled_data = sec.scaled_data[sec.scaled_data['Base_Scaled_Depth'] <= raw_cut_depth].copy()
                
                # update the chunk boundaries
                sec.drilled_bottom = raw_cut_depth
                
                # any chunks in the core below this are unlocked and will be aligned by CompositeBuilder later
                unlock_rest = False
                for s in self.sections:
                    if unlock_rest:
                        s.is_locked = False
                    if s == sec:
                        unlock_rest = True
                break

    def apply_candidate_cut(self, raw_click_depth):
        """
        Cuts the "candidate core" so it begins at raw_click_depth.
        Everything above this depth is labeled as off-splice and ignored; 
        everything below is locked into the splice.
        
        Here, a "candidate core" refers to the core that is about to be added to the splice. 
        It will then become the "master core" that a subsequent candidate core is splice onto.
        """
        for sec in self.sections:
            # If the cut falls inside this section
            if sec.drilled_top <= raw_click_depth <= sec.drilled_bottom:
                
                # Only keep data below the cut
                sec.scaled_data = sec.scaled_data[sec.scaled_data['Base_Scaled_Depth'] >= raw_click_depth].copy()
                
                # Update the section boundaries to place the section onto the MCD scale
                sec.drilled_top = raw_click_depth
                
                # Mark this section and all below it as "on-splice" until a new tiepoint is placed
                lock_rest = False
                for s in self.sections:
                    if s == sec:
                        lock_rest = True
                    if lock_rest:
                        s.is_locked = True
                break

class Hole:
    def __init__(self, hole_name):
        """
        Definitions for the variables in this class.
        """
        self.hole_name = hole_name
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
        Gathers all the on-splice data from the holes to build the composite section view.
        """
        splice_dfs = []
        for h_name, hole in builder_obj.holes.items():
            hole_data = hole.get_positioned_data()
            if not hole_data.empty:
                # Extract only the on-splice data
                locked_data = hole_data[hole_data['Is_Locked'] == True]
                if not locked_data.empty:
                    splice_dfs.append(locked_data)
                    
        if splice_dfs:
            combined = pd.concat(splice_dfs, ignore_index=True)
            return combined.sort_values(by='MCD')
        return pd.DataFrame()
