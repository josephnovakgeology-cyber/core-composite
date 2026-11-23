# Overview
If you are struggling to figure out how to install Core Composite, please check out the installation guide :)

This document is really long. Each section is split off into a separate document within the relevant demo folder, which you may find easier to follow.

Here, I will walk you through how to use the three major tools within Core Composite:

**1) CorePhotoDigitizer** is an interactive GUI for processing legacy core photographs from the DSDP, ODP, and IODP contained within the `image.py` module. 
CorePhotoDigitizer allows geoscientists to extract L*, a*, and b* from analog and digital core photos, which is especially useful when working on drilling sites with no other useful archived stratigraphic information. 
CorePhotoDigitizer also allows users to convert L* values to % reflectance. 

**2) CompositeBuilder** is an algorithm that takes new or published affine shifts and uses them as the basis for automated centimeter-scale dynamic stretching or squeezing of off-splice drilling materials so that they are aligned to the main composite section for a set of parallel boreholes within the `builder.py` module. 
This algorithm is particularly useful for maximizing the scientific lifespan of very heavily sampled drill sites with preexisting composite stratigraphies and age models that need to be applied to off-splice cores that still have unsampled material.

**3) SpliceBuilderGUI** is an interactive GUI that enables users to generate new composite sections from physical properties data within the `gui.py` module. 

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

### Calculating % reflectance from L\*
Core Composite includes a simple function to calculate % reflectance from L* values. An example of how to do that with your 887A color data is included in the "get_reflectance_demo.py" file. 

## Building a new splice / composite section: SpliceBuilderGUI
SpliceBuilderGUI is a point-and-click interface for manually identifying tiepoints between parallel boreholes at a drill site. The software is set up to conveniently work with DSDP, ODP, and IODP datasets, but can in-principal be used with any type of drilling data provided that you have adequate supporting information about the driller's wire line depth scale and the recovery of sediments within each of the cores taken from a given borehole.

These instructions walk you through the demo AND what each line of the code in the demo script does. This is because using SpliceBuilderGUI requires more steps than CorePhotoDigitizer in terms of editing the code for a new drill site, so it is important that you understand the basic logic of the code as you make edits.

### Required Files
**The files required to use SpliceBuilderGUI are:**

**1). At least one set of physical properties data that was measured at each of the boreholes that will be included in your splice / composite section.**

**2). The coring summary, which specifies the cored length of each core recovered from the drill site.**

All of the files necessary to go through the demo are included in: **core_composite/demos/build_a_new_splice_demo_files**

The magnetic susceptibility, gamma ray attenuation and porosity evaluator (GRAPE) wet bulk density (WBD), and coring summary were downloaded from the ODP Janus database (https://www-odp.tamu.edu/database/). *You can access these data using the same procedure outlined in the User Guide and Instructions for the image processing demo, but clicking the links for "Magnetic Susceptibility (sections)" ; "GRA Bulk Density (sections)" or ; "Hole / Core Summary (cores)."*

*SpliceBuilderGUI is set up to run with files as they are formatted in the Janus Database. Extensively reformatting the files may cause errors.*

The color data (L\*, a\*, b\*) were extracted from core photos using Core Composite's CorePhotoDigitizer. These are the exact same files that were produced from **image_processing_demo.py** 

### Building a new splice
This demo is written assuming that you are using the spyder IDE. Download the demo files from GitHub and place them all into the same project folder.

To get started, open Anaconda Prompt (PC) or the Terminal (Mac / Linux) and activate your python environment where you installed Core Composite. Mine is called "core_composite" so I use the following command in Anaconda Prompt:

**conda activate core_composite**

Now launch spyder with the following command:

**spyder**

Spyder will open to the last script you were working on. Use the navigation buttons to open **splicebuildergui_demo.py** - change your working directory to be the folder that contains **splicebuildergui_demo.py** and the .csv files that you downloaded from GitHub (if you are following the demo) or to the folder that contains the files that you downloaded from Janus if you are following along with data from your drill site. 

**Confused about where the navigation buttons are?**
*Take a look at the user guide or instructions for **Core Photo Analysis** for pictures showing you where these buttons are.*

Once you have the demo script open and the working directory set, spyder should look like this:

<img width="1900" height="1126" alt="image" src="https://github.com/user-attachments/assets/15e3cab4-d68c-4104-90b0-247ae6dab478" />

If you are following the demo, then the file is already set up to run. Let's walk through what each of the lines of code in this script do so that you can modify it later to work on different drill sites. 

The imports [lines 8-14] do not need to be changed. Line 12 makes the plots appear as popups. I recommend leaving it alone, even if spyder flags an error on that line. It works. Removing that line of code will make the GUI show up in the plots window of spyder, which is not ideal.

IF you are working with your own dataset, the first thing you may need to change are the types of physical properties data you are working with. Here, physical properties data are called "proxies" because proxies is a shorter word than "physical properties data." The "target_proxies" variable reflects the data types that you want plotted in SpliceBuilderGUI. The string (the text within the quotation marks inside the brackets) needs to match at least part of the column header name in one of your data files. 

You can plot any type of data you would like, although there could be some plotting oddities that arise if you use a data type other than the three in this demo (these are the only types of data I tested). If you find a plotting bug, please leave a comment on the GitHub page or contact me via email (my email as of 7/8/2026 is: joseph_novak@brown.edu; since I am a postdoc, my email address will likely change in the future, so take a look at a recent paper of mine to find my up to date contact). 

In addition to specifying the target proxies, you need to tell Core Composite which files to look in to find the information for each hole. This is done in lines 19-29 with the function **"load_from_multiple_files()"** - the function takes three arguments:

**hole_A = load_from_multiple_files("SiteA", "Site_Core_Summary.csv", [SiteA_target_proxy_data_file_1.csv", "SiteA_target_proxy_data_file_2.csv", etc...]**

**hole_B = load_from_multiple_files("SiteB", "Site_Core_Summary.csv", ["SiteB_target_proxy_data_file_1.csv", "SiteB_target_proxy_data_file_2.csv", etc...]**

This information is stored in the "hole objects" (hole_A, hole_B, etc.) that need to be added to the builder prior to initializing the SpliceBuilderGUI. This is done in lines 31-33 in the demo with the following commands:

**builder.add_hole(hole_A)**
**builder.add_hole(hole_B)**

SpliceBuilderGUI is ready to run once the hole objects are added to the builder. This is done with the function **SpliceBuilderGUI()** - this function takes three arguments:

**SpliceBuilderGUI(builder, mudline_hole = "887B", proxy = "density")**

These arguments specify: 1) the name of your builder object, 2) the mudline hole, i.e. the borehole with the shallowest absolute depth core at the drill site. This is usually specified in the initial site report. If you do not have this info, you will need to compare the data from core 1 of the different boreholes to figure out which one contains the uppermost sediment in the sequence.

If you are following along with the demo script, go ahead and press the small green arrow at the top of the spyder tool ribbon. This will run the code and open the SpliceBuilderGUI. The popup containing the GUI will look like this:

<img width="1876" height="1052" alt="image" src="https://github.com/user-attachments/assets/b17d88f0-8af8-4152-bac1-0e23adf1ee0d" />

You can press the different bottons on the left side of the plot to cycle between different data types and different boreholes. The data plotted at the top of the plot in black is the composite section / splice that you are building. The "mudline_hole" argument from before determines which core is plotted as a starting point for the correlation. 

The data on the bottom of the plot is from the borehole that is currently selected with the buttons on the right. For longer sequences, it can be useful to zoom in on the region where you are currently working, which you can do using the text boxes on the bottom of the plot. "Undo" removes your last tiepoint, and "Finalize" closes the GUI and builds an affine table. 

For this demo, I will primarily use the b* data to build the splice since there are pronounced and repeated variations in those data between each of the boreholes. I am going to draw my first tiepoint between 887B 1H (our mudline core) and 887C 1H. To do this, I first left click on the composite at the place where I want to tie in 887C 1H:

<img width="1830" height="1007" alt="image" src="https://github.com/user-attachments/assets/66ce9cb4-980f-4068-9ff3-de114b1b6157" />

The black dashed line shows where the tiepoint is attached to the composite section / splice. Next, right click on the depth interval of 887C 1H you want to tie into the composite section / splice. In my case, I clicked at about 1 meter, so the result looks like this:

<img width="1846" height="1050" alt="image" src="https://github.com/user-attachments/assets/e7442287-4aad-461c-b163-021ed60861b7" />

Continue toggling between holes and adding successively deeper cores to build your composite section / splice. Here is what mine looks like:

<img width="1862" height="1036" alt="image" src="https://github.com/user-attachments/assets/fae49060-358c-46d3-9b25-84ff96f5ffae" />

When you are finished, hit the "Finalize" button. This will pass your affine shifts to Core Composite, which will automatically assign all of the data in the builder object to the composite depth scale, include the automated alignment of off-splice materials to the main composite section / splice. We can then review our results in the "ReviewGUI".

<img width="1841" height="1040" alt="image" src="https://github.com/user-attachments/assets/3d460a4e-30ce-4c63-b538-8fbeb2ed598d" />

Here, the composite section is plotted at the bottom. The data above it are from each of the parallel boreholes. The blue data are the values that compose the composite section / splice, and the red data are the off-splice data. The program attempts to align the off-splice data with the composite, which you can verify in this GUI. If you are satisified with the alignment, hit "Export and Save." 

Further instructions on how to refine these off-splice alignments can be found in the "Align to Existing Splice" demo. 

## Placing subsamples onto the composite depth (MCD) scale
So now you have a splice, how do you place your samples onto that depth scale? Included in this folder is a short script that calls a function for this in Core Composite. Go ahead and download **"map_subsamples_to_mcd_demo.py"** - this file will use the composite depth scale we just made to assign calcium carbonate wt. % measurements from ODP 887 to the composite depth scale. 

Looking at this script, you will notice that it is very similar to the previous demo. That is because the mapping function requires us to define the builder object. If you are working on your own core, make sure that lines 10-32 match what you did to put together the builder object in your work. Then, at line 35, load in the affine table that you made last time. 

You are now ready to call the function **"map_subsamples_to_mcd"** - this function requires three arguments:
**1). the builder object**

**2). the input file name, as a string**

**3). the output file name, as a string**

## Semi-automated alignment of off-splice materials to published composite sections
### Required Files
The required files for this demo can be found in **core_composite/demos/align_to_existing_splice_demo_files**

There are a substantial number of files because we are working with data from four holes. We will base our work on gamma ray attenuation porosity evaluator (GRAPE) wet bulk density (WBD) and magnetic susceptibility data. These files are freely available in the Janus web database. The required files are:

**1). The coring summary file for ODP Site 883 ("883_summary.csv")**

**2). The physical properties data files ("883A_GRAPE_WBD.csv", "883A_magsus.csv", etc.)**

**3). The published affine table ("Keigwin_splice.csv")**

### Alignment of off-splice materials to a published composite section / splice
Like with the other functions in Core Composite, all of the data files should be in the same folder as your script. Download all of the files from Github if you want to follow along with the demo. These instructions will be very similar to those for **SpliceBuilderGUI** because both of these modules use the same data structures. 

To get started, open Anaconda Prompt (PC) or the Terminal (Mac / Linux) and activate your python environment where you installed Core Composite. Mine is called "core_composite" so I use the following command in Anaconda Prompt:

**conda activate core_composite**

Now launch spyder with the following command:

**spyder**

Spyder will open to the last script you were working on. Use the navigation buttons to open **compositebuilder_demo.py** - change your working directory to be the folder that contains **compositebuilder_demo.py** and the .csv files that you downloaded from GitHub (if you are following the demo) or to the folder that contains the files that you downloaded from Janus if you are following along with data from your drill site. 

**Confused about where the navigation buttons are?**
*Take a look at the user guide or instructions for **Core Photo Analysis** for pictures showing you where these buttons are.*

Once you have the demo script open and the working directory set, spyder should look like this:

<img width="1902" height="1125" alt="image" src="https://github.com/user-attachments/assets/9e03204a-5b31-44b2-b469-2d565ce18ace" />

If you are following the demo, then the file is already set up to run. Let's walk through what each of the lines of code in this script do so that you can modify it later to work on different drill sites. 

The imports [lines 8-14] do not need to be changed. Line 12 makes the plots appear as popups. I recommend leaving it alone, even if spyder flags an error on that line. It works. Removing that line of code will make the Review GUI show up in the plots window of spyder, which is not ideal.

IF you are working with your own dataset, the first thing you may need to change are the types of physical properties data you are working with. Here, physical properties data are called "proxies" because proxies is a shorter word than "physical properties data." The "target_proxies" variable reflects the data types that you want to be used for the automated alignment of off-splice materials to the composite section. The string (the text within the quotation marks inside the brackets) needs to match at least part of the column header name in one of your data files. 

In addition to specifying the target proxies, you need to tell Core Composite which files to look in to find the information for each hole. This is done in lines 19-29 with the function **"load_from_multiple_files()"** - the function takes three arguments:

**hole_A = load_from_multiple_files("SiteA", "Site_Core_Summary.csv", [SiteA_target_proxy_data_file_1.csv", "SiteA_target_proxy_data_file_2.csv", etc...]**

**hole_B = load_from_multiple_files("SiteB", "Site_Core_Summary.csv", ["SiteB_target_proxy_data_file_1.csv", "SiteB_target_proxy_data_file_2.csv", etc...]**

This information is stored in the "hole objects" (hole_A, hole_B, etc.) that need to be added to the builder prior to initializing the SpliceBuilderGUI. This is done in lines 31-33 in the demo with the following commands:

**builder.add_hole(hole_A)**
**builder.add_hole(hole_B)**

Lastly, the builder object needs the published splice, which is loaded in at line 38. The formatting of this table is very important. It should look like this:

<img width="882" height="162" alt="image" src="https://github.com/user-attachments/assets/5bbeed4f-272d-4519-9a57-69706364733a" />

It is important that you follow the same formatting when using this function for your own projects. Specifically:

Site - this is the number
Hole - this is letter
Core - must be formatted with number and type, i.e. 1H, 2H, etc.
Shift - this is the affine shift, or the difference between Depth (MCD) and Depth (mbsf) for that core. 
Status - this must say "On-splice" for all the entries in this file. This flag is to distinguish the on-splice and off-splice material for the algorithm.
Top [mbsf] - this column is ignored by the algorithm, but I like to have it to verify my shift calculation.
Bot [mbsf] - this column is ignored by the algorithm, but I like to have it to verify my shift calculation.
Depth comp top [mcd] - This is the topmost composite depth assigned to this core. 
Depth comp bot [mcd] - This is the bottommost composite depth assigned to this core.

If you are encountering errors using this script for your own project, it is probably because of how you formatted this table.

Line 41 runs the automated alignment with the function builder.optimize_off_splice() - the function takes three arguments:

**1). the "proxy" (physical properties data) to use for alignment. The default setting is "auto", which means that the data type with the highest signal to noise ratio within each 1 meter interval will be used.**

**2). str_range - this is the permissable range of stretching or squeezing that the algorithm is permitted to try to find a good correlation of the off-splice materials to the composite section / splice. This needs to be input as a pair of values, for example: (0.6, 1.05)**

Let's go ahead and run the script by hitting the small green arrow at the top of the spyder IDE. When you do, you will see a lot of text appear in your console that looks like this:

<img width="952" height="675" alt="image" src="https://github.com/user-attachments/assets/860384ba-5b0c-4652-a861-42c65447ccaa" />

You will also see a couple of scatterplots that pop up:

<img width="1595" height="792" alt="image" src="https://github.com/user-attachments/assets/ee26fc58-0c26-4e37-9a0f-d69a68858ff6" />

These plots allow you to assess the overall quality of the alignment of the off-splice materials to the splice. Let's close them and look at the other popup: the ReviewGUI.

<img width="1887" height="1047" alt="image" src="https://github.com/user-attachments/assets/50fe9a0d-cebc-4c43-891d-9d7f79a3d41b" />

Here, the bottom gray line is the composite section / splice. The data plotted above are from the different boreholes at this drill site. The blue data compose the composite section / splice. The red data are the off-splice portions of the same cores, automatically aligned to the composite section. 

You may have noticed that there are several cores in 883B and 883C where no data were plotted. This is because these cores were entirely excluded from the splice. But, that material is still useful! We can align it to the published splice, and therefore know where we can sample for our future studies, by hitting the button "Tiepoint for off-splice core." When you do that, you will see several cores appear on your screen:

<img width="1867" height="1017" alt="image" src="https://github.com/user-attachments/assets/b3500e37-64eb-4eac-a4bc-2e1868449377" />

Let's focus on correlating the upper cores to the composite section, starting with 883B. You can use the toggles on the left of the **ReviewGUI** to remove the other holes from the screen (for now). You can also type in a depth range to the text boxes in the bottom center of the screen to zoom in on a specific depth interval. Take a look:

<img width="1857" height="1012" alt="image" src="https://github.com/user-attachments/assets/3000aa3e-300c-4eff-b445-8a0ab3ab423a" />

Now, let's add tiepoints for our off-splice cores. You can do this by left clicking the feature on the off-splice core that you want to align to the composite, and then right clicking on the point on the composite where you want to tie in the off-splice core. If you keep the "Auto-Realign" button selected, the algorithm will calculate the stretching and squeecing required to align the rest of the core to the composite (it will not update the plot to show this for the sake of efficiency).

Another useful tool for you is the "Manual Nudge." Let's say that you change your mind about the alignment of an off-splice core that you tied in. You can update the alignment by left clicking on the composite, right clicking on the off splice core, and then clicking the "Manual Nudge" button. This will shift the entire core to that position on the composite section.

Try aligning the off-splice materials at ODP 883. Your end product should look something like this:

<img width="1840" height="1020" alt="image" src="https://github.com/user-attachments/assets/b30d47ec-561d-47be-9f51-e2a07a70843b" />

Once you are satisfied with your work, hit the "Export and Save" button to get .csv files of your composite section and all of the physical properties data you used for this exercise on the composite depth scale.
