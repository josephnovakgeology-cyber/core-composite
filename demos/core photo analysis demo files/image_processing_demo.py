# -*- coding: utf-8 -*-
"""
Created on Tue May  5 11:10:44 2026

@author: joseph novak


"""

from core_composite.image import extract_image_from_pdf
from core_composite.image import run_batch_digitization
import os
import glob

%matplotlib qt  

if __name__ == "__main__":
    
    print("Step 1: .pdf to .jpg conversion")
    
    pdf_files = sorted(glob.glob("*.pdf"))
    
    if not pdf_files:
        print("No .pdf files found. Skipping conversion step.")
    else:
        for pdf_path in pdf_files:
            base_name = os.path.splitext(pdf_path)[0]
            jpg_path = f"{base_name}_converted.jpg"
            
            if os.path.exists(jpg_path):
                print(f"-> Skipping {pdf_path}: {jpg_path} already exists.")
            else:
                print(f"-> Converting {pdf_path}.")
                extract_image_from_pdf(pdf_path, jpg_path)
                
    print("Step 2: core photo batch digitization")
    
    
    search_patterns = ["*_converted.jpg", "*.png", "*.jpg", "*.jpeg"]
    all_core_photos = []
    
    for pattern in search_patterns:
        all_core_photos.extend(glob.glob(pattern))
        
    all_core_photos = sorted(list(set(all_core_photos)))
    
    if not all_core_photos:
        print("Could not find any valid core photos (*.png, *.jpg) in this folder.")
    else:
        print(f"Found {len(all_core_photos)} image files to check: {all_core_photos}")
        
        
        master_datasets = run_batch_digitization(
            image_paths=all_core_photos,
            section_summary_csv="887_section_summary.csv", # Swap this to your active summary file
            leg=145, # e.g., Leg 346 for U1426
            output_prefix="Site887"
        )
