# Overview
These are the same instructions for using Core Composite to do image analysis as in the user guide (user_guide.md).

## Extracting color data from core photos: CorePhotoDigitizer
CorePhotoDigitizer is set up to convert the .pdf core photos from the DSDP / ODP / IODP database to .jpg format prior to image extration. 
A demo version of the script that implements CorePhotoDigitizer is included in the "demos" folder. 
The script needs to be in the same folder as the .pdfs of the core photos and requires a supporting file that includes the core section summary from the preliminary report. 

### Required Files and how to find them in the Janus Database
**The required files to use CorePhotoDigitizer are:**

**1). core photo .pdf files**

**2). The core section summary from your drill site, which specifies the cored length of each core section at the drill site**

The ODP Janus web database stores all of the data from legacy cores that was produced by Shipboard Scientific Parties. It can be accessed here: [Janus](https://www-odp.tamu.edu/database/).

Click the highlighted link to access the database from the main webpage.

<img width="930" height="926" alt="image" src="https://github.com/user-attachments/assets/8cea1623-ab26-42b9-96d7-4a266cd6953d" />

From there, you can access the data from each DSDP, ODP, or IODP leg by clicking the Report number at the top of each column on the database, highlighted in the image below. Go ahead and click on Leg 145.

<img width="1892" height="1006" alt="image" src="https://github.com/user-attachments/assets/cc9a0397-0625-4ffc-9606-dffb4b0211f5" />

This will take you to the data for all of the drill sites from that DSDP, ODP, or IODP Leg. From here, click on the number of the drill site you are studying. We are going to look at Site 887 as an example, highlighted in the image below.

<img width="1156" height="1060" alt="image" src="https://github.com/user-attachments/assets/70e59222-4c5b-4b3f-8da1-e2f409b26038" />


Great. You are now looking at all of the data archived by DSDP, ODP, or IODP from your drill site. The numbers correspond to the number of data points from each hole of a given data type. Click on the numbers to see the data. Here, we are going to click on the photos for Site 887 Hole A.

<img width="1302" height="1142" alt="image" src="https://github.com/user-attachments/assets/ed30a9f1-bddb-4dab-882b-bffd99879d67" />

Each of the image links will take you to the core photos, which you can download as a .pdf file. Core composite will convert them to .jpg format for you later, so do not worry about that. Save all of the .pdf files to a single folder on your computer that you will use for this project.

<img width="687" height="720" alt="image" src="https://github.com/user-attachments/assets/0c988f3e-55e7-4223-95ea-7a8b4d4ed338" />

You will also need the "core section summary" for your drill site. You can find that here:

<img width="1262" height="1057" alt="image" src="https://github.com/user-attachments/assets/9d16c7a4-aef2-4bf7-b2a0-ae4cee5b7e88" />

When you click the highlighted link, you should see this:

<img width="727" height="1067" alt="image" src="https://github.com/user-attachments/assets/8bba7d9f-a247-4900-a4c7-a6387d2bb095" />

Go ahead and paste this info into a .csv file. Make sure that the information is properly formatted such that the columns are properly divided into cells. This will probably require you to do some reformatting in your .csv file. A trick I like to use is to paste this info into the Notepad app on windows and then copy that text again before pasting into the .csv, which makes sure everything is formatted correctly.

Make sure this .csv file is saved in the same folder as your core photos. I like to call this file something like "887_section_summary.csv" so that I do not confuse it with other files.

### Core Image Analysis
Alrighty then. You now have all of your core images in a single folder for your project. You now need to extract color data from them. If you skipped the previous section, four core photographs and the ODP Site 887 section summary file are included in the **core_photo_analysis_demo_files** folder.

The basic format of the script that is used for calling the image analysis functions in core composite is contained in **"image_processing_demo.py"** in the demos folder of this Github repository. The file path is: **core_composite/demos/core_photo_analysis_demo_files/image_processing_demo.py** ; Go ahead and copy **"image_processing_demo.py"** into the same folder as all of your core images. 

You now need to activate your python environment where you installed Spyder (see the installation guide for details on how to make a python environment and install core_composite via pip). To do this, you must open Anaconda Prompt (Windows) or the Terminal (Mac / Linux) and type the following command and press enter: 

**conda activate your_environment_name_here**

My python environment is called workstation, so the version of this command that I type is:

**conda activate workstation**

Here is what that looks like on my Windows device:

<img width="1532" height="910" alt="image" src="https://github.com/user-attachments/assets/0d1975f3-1cec-4049-88ae-3a34b6f7ea7e" />

Then, launch your python IDE. I prefer to use Spyder, so this tutorial is written with that use case in mind. To use Spyder in your python environment, you will have to install it if you have not already. See the installation guide for those instructions (it is only two lines of code!). To launch Spyder from Anaconda prompt or the terminal, simply type "Spyder" and press enter:

<img width="1532" height="892" alt="image" src="https://github.com/user-attachments/assets/c09d8cde-0463-467f-980d-5ddc9a8070b0" />

When you first launch Spyder, your screen should look something like this:

<img width="1911" height="1127" alt="image" src="https://github.com/user-attachments/assets/351535aa-faac-4620-af6f-18d0d5c1933e" />

The first time you do this, you will need to connect Spyder to the core_composite python environment. Instructions for how to do this are in the installation guide. 

Use the folder button on the top left side to open the demo script. You should now see the code that calls the image analysis functions in Core Composite:

<img width="1535" height="910" alt="image" src="https://github.com/user-attachments/assets/880e55fc-ea85-4e70-a350-b2ddf0a4b12a" />

To run this code, you will have to set your working directory to be the folder that contains the .pdf files of the core photographs. You can do that by clicking the folder button on the **top right** of the spyder user interface:

<img width="1535" height="910" alt="image" src="https://github.com/user-attachments/assets/ccb78143-23e5-41b5-967e-f6a425c0ccbe" />

Before we run the code, we need to make sure that the information matches for our site. The demo file is set up for ODP Site 887, but if you are working on another site, you will need to update three things:

**1) Line 22:**
  **image_path - this is the name of the image file to generate the diagnostic RGB histogram.   By default, it will search you current working directory for the converted .jpg files produced by convert_pdfs_to_images(). You can provide a path to a different folder if you prefer via this argument as well.**

  **figure_filename - this is the file name of the .pdf of the histogram figure.**

**2) Line 25:
  summary_csv_path="887_section_summary.csv" - this line must match the name of your section   summary file, with the name and file extension contained within the quotation marks**
  
  **leg=145 - this line must match the expedition number your drill site was collected during** 
  
  **output_prefex="Site887" - this must match your site name, with the name entirely contained     within the quotation marks.**

  **3) Line 28:**
  **summary_csv_path needs to be updated here as well**

Once that is all set, hit the little green arrow on the top ribbon of spyder to save and run the script:

<img width="1535" height="910" alt="image" src="https://github.com/user-attachments/assets/451a9f0a-9f8b-445a-80bd-d2d07654662d" />

When you run this script for the first time, it will convert all of the .pdf files to .jpg before opening a popup window where you will begin the image analysis. Your console in spyder should look like this:

<img width="616" height="707" alt="image" src="https://github.com/user-attachments/assets/d48d24bc-d098-4dc4-ae32-1b7d9ea4470f" />

You should now see see a popup window that looks like this:

<img width="1161" height="811" alt="image" src="https://github.com/user-attachments/assets/d847c24f-aaed-42b2-aaaf-cf4ad7410d6d" />

The popup window will ask you to draw a single box down one of the white tracks to establish the background lighting effects in the image. My preferred method for this is shown below:

<img width="607" height="991" alt="image" src="https://github.com/user-attachments/assets/a656a369-1f32-4598-92d3-83adf7107d3b" />

Notice that the cores in this photo are not perfectly vertical. This is the case in most legacy core photographs. It can make drawing a box that only incapsulates the white backtrack hard to do, so be careful. 

Once you have drawn the vertical box, click enter. Now draw a horizontal box, like so:

<img width="587" height="962" alt="image" src="https://github.com/user-attachments/assets/3eb03361-d1b7-49fc-97a8-67a8b1c2c860" />

Hit enter. You will be prompted about whether you want to calibrate the image processing with a color checker. In almost all cases, there is no color checker present, so you will select skip. If there is a color checker present, follow the prompts to calibrate the image processing. Compare your extracted values with and without the calibration to see whether this additional step is useful for the images you are processing. 

You will then be prompted to draw boxes over the sediment core sections by left clocking and dragging your mouse. I prefer to do this in the middle of cores, skipping the core catcher since those sediments are not stratigraphically informative, like so:

<img width="1201" height="832" alt="image" src="https://github.com/user-attachments/assets/5a010e72-ebd5-49e2-958e-11a22e41d776" />

If you make a mistake, hit the "d" button on your keyboard to undo the last box you drew. 

**Important:** 
**Notice that in core section 1, I draw the box down to 150 cm, even though the bottom of this core section was sampled for interstitial water analyses ("IW") from 145 cm to 150 cm. This is because the curated length of this section in "887_section_summary.csv" is 1.5 m. For convenience, the curated length (CL) of the core and the other information from the section summary is provided in the table to the right. The discrepancy between the length of sediment in the photo and the curated length is because this sediment was sampled before the core was photographed. We address this by drawing a separate box around the "IW section, followed by hitting the "V" key to mark that box as symbolizing a void:**

<img width="1157" height="846" alt="image" src="https://github.com/user-attachments/assets/ccbf5069-6ff9-426c-acca-e7b7abbe349c" />


**We handle voids and core distirbances the same way. This "V" or void designation tells CorePhotoDigitizer to mask this interval of the core since the extracted color data are not reliable. You can see an example of this in the image above.**

When you are done drawing your core and void boxes, close the popup window. The software will process the image and then show you the next one in a new popup window. You will repeat the above procedure for each image from which you extract color data. After you finish color extraction of the last core, the popup window will close and your console will look like this:

<img width="970" height="585" alt="image" src="https://github.com/user-attachments/assets/5fc6e90e-267c-474d-8d5e-a1fe7fe44e8a" />

And your working directory will have a lot of new files. Notice "Site887_Hole_A_Color.csv" and "Site887_Hole_B_Color.csv" - these files contain all of the extracted color data for the cores from hole A and hole B that you processed plotted on the driller's wire line depth scale [depth (mbsf) or meters below sea floor] (if you are processing a different core, you will see different names). Let's open "Site887_Hole_A_Color.csv" to see what is inside.

<img width="1502" height="871" alt="image" src="https://github.com/user-attachments/assets/55f43aa1-9573-4148-b1b0-2e7837d1b433" />

These are the L*, a*, and b* data that we extracted from these core images. The empty values were masked because I drew a void box over that particular core section. 

Congratulations! You just extracted color data from legacy core images for the first time.

### Interpreting RGB histograms and output from the check_photo_quality() function

<img width="570" height="185" alt="image" src="https://github.com/user-attachments/assets/8e80448d-241c-49ea-835f-abb35e797e1f" />

Plotted above are histograms of the red, green, and blue pixels within the core photo for 887A 2H. These are the typical histograms of a well-exposed core photo: a bimodal R, G, and B distribution with very few pixels at the extreme edges (0 and 255) of the spectrum. Below is an example of a severely overexposed photo:

<img width="752" height="246" alt="image" src="https://github.com/user-attachments/assets/5bb8cb9c-a287-4310-afbe-97178695ebae" />

As described in our manuscript, overexposure leads to color information loss in the channel(s) that are overexposed. Such photographs are not suitable for color data extraction, at least until we figure out a better protocol. 

To prevent anyone from wasting time processing low-quality images, we include the check_photo_quality function that summarizes these tests, as shown below:

<img width="682" height="137" alt="image" src="https://github.com/user-attachments/assets/9dd4c85c-4274-49ee-b923-5654f88a6261" />

The percentages listed here are the proportions of the photograph that have a R, G, or B value < 5 (crushed shadows) or > 250 (blown highlights). In either case, images with crushed shadows or blown highlights should not be analyzed. We strongly recommend checking the quality of your images with this function after conversion from .pdf and **before** extracting any color data.

### Calculating % reflectance from L\*
Core Composite includes a simple function to calculate % reflectance from L* values. An example of how to do that with your 887A color data is included in the "get_reflectance_demo.py" file. 
