# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 17:24:25 2026

@author: joseph novak
"""

import pandas as pd
from core_composite.image import get_reflectance

# Load the color data
color_data = pd.read_csv("Site887_Hole_A_Color.csv")

# Calculate reflectance and add it as a new column
color_data["% reflectance"] = get_reflectance(color_data["L*"])

# Save the updated data
color_data.to_csv("Site887_Hole_A_Color_Reflectance.csv", index=False)