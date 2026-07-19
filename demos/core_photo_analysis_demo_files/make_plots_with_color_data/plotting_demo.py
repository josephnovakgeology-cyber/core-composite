# -*- coding: utf-8 -*-
"""
Created on Sun Jul 19 05:09:36 2026

@author: joseph novak
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

#### loading in data files ####
os.chdir(r"C:/Users/josep/OneDrive/Documents/papers/automated_compsite_section_generator/data analysis/969")

# Read the CSV file into a pandas DataFrame
L_synthetic_969 = pd.read_csv('Site969_Hole_A_Color_Reflectance.csv')

### making "thinned" datasets ####
# EXPLANATION:
# the command below is taking every 10th row from the synthetic color
# data file and putting them into a new data frame object. 
#
# We will use this new data frame object for plotting.
thinned_synth_data = L_synthetic_969.iloc[::10]

#### plotting ####
# Create a new figure
plt.figure()

# Plot the data 
plt.plot(thinned_synth_data['Depth (mbsf)'], thinned_synth_data['L*'], 
         color='darkgray', linewidth=2)

# Add axis labels and limits
plt.xlabel('Depth (mbsf)')
plt.ylabel('Synthetic L*')
plt.xlim(0, 40)
plt.ylim(0, 80)

ax = plt.gca() # Gets the current axes
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Display the plot
plt.show()