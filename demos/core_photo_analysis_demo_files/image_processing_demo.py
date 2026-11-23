# -*- coding: utf-8 -*-
"""
Created on Tue May  5 11:10:44 2026

@author: joseph novak


"""

from core_composite.image import convert_pdfs_to_images, digitize_core_photos
from core_composite.image import check_photo_quality, evaluate_exposure, stack_photos


%matplotlib qt  

    
    
convert_pdfs_to_images()

check_photo_quality()

status, warnings, diagnostics = evaluate_exposure(image_path = "887A2H_converted.jpg", plot_diagnostics = True, 
                                     figure_filename = '887A2H_RGB_hist.pdf')
    
my_datasets = digitize_core_photos(summary_csv_path="887_section_summary.csv", leg=145, output_prefix="Site887")
    
if my_datasets:
    stack_photos(summary_csv_path="887_section_summary.csv", master_datasets=my_datasets)


