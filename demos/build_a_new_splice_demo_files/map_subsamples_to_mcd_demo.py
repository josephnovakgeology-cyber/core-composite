# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 17:37:58 2026

@author: joseph novak
"""

# map any subsamples to the mcd scale created with the SpliceBuilderGUI

from core_composite.io import map_subsamples_to_mcd, load_external_affine, load_from_multiple_files
from core_composite.builder import CompositeBuilder

builder = CompositeBuilder()

target_proxies = ['Density', 'Magnetic', 'L*', 'A*', 'B*']


hole_A = load_from_multiple_files("887A", "887_summary.csv",
                                  ["887A_GRAPE_WBD.csv","887A_magsus.csv", "Site887_Hole_A_Color.csv"], 
                                  proxy_keywords=target_proxies)

hole_B = load_from_multiple_files("887B", "887_summary.csv",
                                  ["887B_GRAPE_WBD.csv","887B_magsus.csv", "Site887_Hole_B_Color.csv"],
                                  proxy_keywords=target_proxies)

hole_C = load_from_multiple_files("887C", "887_summary.csv",
                                  ["887C_GRAPE_WBD.csv","887C_magsus.csv", "Site887_Hole_C_Color.csv"],
                                  proxy_keywords=target_proxies)

builder.add_hole(hole_A)
builder.add_hole(hole_B)
builder.add_hole(hole_C)


load_external_affine(builder, "Master_Final_Affine_Table.csv")

map_subsamples_to_mcd(builder, "Site887_Hole_A_Carbonate.csv", #input file 
                      "Site887_Hole_A_carbonate_mcd.csv") # output file name