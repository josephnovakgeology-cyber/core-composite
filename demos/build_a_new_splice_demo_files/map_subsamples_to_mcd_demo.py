# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 17:37:58 2026

@author: joseph novak
"""

# map any subsamples to the mcd scale created with the SpliceBuilderGUI

from core_composite.io import map_subsamples_to_mcd, load_external_affine
from core_composite.builder import CompositeBuilder

builder = CompositeBuilder()


load_external_affine(builder, "Master_Final_Affine_Table.csv")

map_subsamples_to_mcd(builder, "Site887_Hole_A_Carbonate.csv", #input file 
                      "Site887_Hole_A_carbonate_mcd.csv") # output file name