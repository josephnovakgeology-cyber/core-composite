# -*- coding: utf-8 -*-
"""
Created on Mon May  4 14:05:55 2026

@author: josep
"""

from core_composite.io import load_from_multiple_files, load_external_affine, export_affine_table, export_and_save
from core_composite.builder import CompositeBuilder
from core_composite.gui import Phase3ReviewGUI

%matplotlib qt

builder = CompositeBuilder()

target_proxies = ['Density', 'Magnetic']

# Load the data
hole_A = load_from_multiple_files("883A", "883_summary.csv", ["883A_GRAPE_WBD.csv", "883A_magsus.csv"], 
                                  proxy_keywords=target_proxies)

hole_B = load_from_multiple_files("883B", "883_summary.csv", ["883B_GRAPE_WBD.csv", "883B_magsus.csv"], 
                                  proxy_keywords=target_proxies)

hole_C = load_from_multiple_files("883C", "883_summary.csv", ["883C_GRAPE_WBD.csv", "883C_magsus.csv"], 
                                  proxy_keywords=target_proxies)

hole_D = load_from_multiple_files("883D", "883_summary.csv", ["883D_GRAPE_WBD.csv", "883D_magsus.csv"], 
                                  proxy_keywords=target_proxies)

# Add the holes to the builder
builder.add_hole(hole_A)
builder.add_hole(hole_B)
builder.add_hole(hole_C)
builder.add_hole(hole_D)

# Apply the published splice
load_external_affine(builder, "published_upper_splice.csv")

# Run the automated alignment
builder.optimize_off_splice(proxy='auto', str_range=(0.6, 1.05))

# Review the results
Phase3ReviewGUI(builder, proxy='auto')

export_affine_table(builder)
export_and_save(builder, active_holes = builder.holes, all_proxies = target_proxies)
