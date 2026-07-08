# -*- coding: utf-8 -*-
"""
Created on Tue May 12 16:36:39 2026

@author: joseph novak
"""

from core_composite.gui import SpliceBuilderGUI, Phase3ReviewGUI
from core_composite.builder import CompositeBuilder
from core_composite.io import load_from_multiple_files, export_affine_table, export_and_save

%matplotlib qt  

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

SpliceBuilderGUI(builder, mudline_hole = "887B", proxy = "density")

print("Running off-splice alignment")
builder.optimize_off_splice(proxy='auto')

print("Launching review GUI")
Phase3ReviewGUI(builder, proxy='auto')

export_affine_table(builder)
export_and_save(builder, active_holes = builder.holes, all_proxies = target_proxies)
print("Done.")


