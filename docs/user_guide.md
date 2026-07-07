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

### Finding Core Photos in the Janus Database
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

You now need to activate your python environment where you installed Core Composite (see the installation guide for details on how to make a python environment and install core_composite via pip). To do this, you must open Anaconda Prompt (Windows) or the Terminal (Mac / Linux) and type the following command and press enter: 

**conda activate your_environment_name_here**

My python environment is called core_composite, so the version of this command that I type is:

**conda activate core_composite**

Here is what that looks like on my Windows device:

<img width="1167" height="587" alt="image" src="https://github.com/user-attachments/assets/553b718a-00d9-4305-938e-b6271107faa7" />

Then, launch your python IDE. I prefer to use Spyder, so this tutorial is written with that use case in mind. To use spyder in your python environment, you will have to install it if you have not already. See the installation guide for those instructions (it is only one line of code!). To launch spyder from Anaconda prompt or the terminal, simply type "spyder" and press enter:

<img width="1161" height="587" alt="image" src="https://github.com/user-attachments/assets/47e16118-b824-48eb-9480-27c934becc26" />

When you first launch Spyder, your screen should look something like this:

<img width="1911" height="1127" alt="image" src="https://github.com/user-attachments/assets/351535aa-faac-4620-af6f-18d0d5c1933e" />

Use the folder button on the top left side to open the demo script. You should now see the code that calls the image analysis functions in Core Composite:

<img width="1905" height="1127" alt="image" src="https://github.com/user-attachments/assets/86e866dc-f75e-4452-920b-7e9f39dd1eff" />

To run this code, you will have to set your working directory to be the folder that contains the .pdf files of the core photographs. You can do that by clicking the folder button on the **top right** of the spyder user interface:

<img width="1912" height="1142" alt="image" src="https://github.com/user-attachments/assets/65e4e8cd-dd14-4cd6-89df-a3b2f87b0abf" />

Before we run the code, we need to make sure that the information matches for our site. The demo file is set up for ODP Site 887, but if you are working on another site, you will need to update two things:

**1) Line 55: section_summary_csv="887_section_summary.csv" - this line must match the name of your section summary file, with the name and file extension contained within the quotation marks.**

**2) Line 56: leg=145 - this line must match the expedition number your drill site was collected during.**

**3) Line 57: output_prefex="Site887" - this must match your site name, with the name entirely contained within the quotation marks.**

Once that is all set, hit the little green arrow on the top ribbon of spyder to save and run the script:

<img width="1912" height="1142" alt="image" src="https://github.com/user-attachments/assets/aaca94fe-d88d-4cde-86b1-9713e41bff44" />

When you run this script for the first time, it will convert all of the .pdf files to .jpg before opening a popup window where you will begin the image analysis. Your console in spyder should look like this:

<img width="616" height="707" alt="image" src="https://github.com/user-attachments/assets/d48d24bc-d098-4dc4-ae32-1b7d9ea4470f" />

The popup window will show you the first core photograph in your sequence and will ask you to draw a single box down one of the white tracks to establish the background lighting effects in the image. My preferred method for this is shown below:

<img width="607" height="991" alt="image" src="https://github.com/user-attachments/assets/a656a369-1f32-4598-92d3-83adf7107d3b" />

Notice that the cores in this photo are not perfectly vertical. This is the case in most legacy core photographs. It can make drawing a box that only incapsulates the white backtrack hard to do, so be careful. 

Once you have drawn the vertical box, click enter. Now draw a horizontal box, like so:

<img width="587" height="962" alt="image" src="https://github.com/user-attachments/assets/3eb03361-d1b7-49fc-97a8-67a8b1c2c860" />

Hit enter. You will be prompted about whether you want to calibrate the image processing with a color checker. In almost all cases, there is no color checker present, so you will select skip. If there is a color checker present, follow the prompts to calibrate the image processing. Compare your extracted values with and without the calibration to see whether this additional step is useful for the images you are processing. 

You will then be prompted to draw boxes over the sediment core sections by left clocking and dragging your mouse. I prefer to do this in the middle of cores, skipping the core catcher since those sediments are not stratigraphically informative, like so:

<img width="567" height="992" alt="image" src="https://github.com/user-attachments/assets/6b632dad-0cd5-4fea-a437-485db9886c4a" />

If you make a mistake, hit the "d" button on your keyboard to undo the last box you drew. Close the window to extract the color data and repeat this process for each core. *Recommendation: make notes of large cracks or voids in each core while doing this step. It will make the post-extraction data processing much easier.*

**Important:** 
**Notice that in core section 1, I draw the box down to 150 cm, even though the bottom of this core section was sampled for intersitial water analyses ("IW") from 145 cm to 150 cm. This is because the cored length of this section in "887_section_summary.csv" is 1.5 m. The discrepency is caused by the fact that this sediment was sampled before the core was photographed. Unfortunately, we have to address this in one of two ways:**

**1). Draw a box down to 150 cm (1.5 m) and then later delete this interval from the spreadsheet. [this tutorial uses this method].**

**2). Edit the variable "CL(m)" in "887_section_summary.csv" to match the depth to which there is sediment in the photograph (in this case, 1.45 m) and then draw the box over the region of the core section where there is sediment.**

**My overwhelming preference is to use the first method because it is much more efficient. This is because you can sort the final spreadsheet by L\* values and then delete all values that are near 100. You will see this at the end of the process.**

After you finish color extraction of the last core, the popup window will close and your console will look like this:

<img width="615" height="582" alt="image" src="https://github.com/user-attachments/assets/33dff198-f75a-45c0-8db0-3457a7b4a26c" />

And your working directory will have a lot of new files. Notice "Site887_Hole_A_Color.csv" and "Site887_Hole_B_Color.csv" - these files contain all of the extracted color data for the cores from hole A and hole B that you processed plotted on the driller's wire line depth scale [depth (mbsf) or meters below sea floor] (if you are processing a different core, you will see different names). Let's open "Site887_Hole_A_Color.csv" to see what is inside.

<img width="1907" height="897" alt="image" src="https://github.com/user-attachments/assets/8606c60b-215c-43cc-9ba5-78650fa7715b" />

These are the L*, a*, and b* data that we extracted from these core images. We now need to do a bit of post-processing to make sure that there are no artifacts in our color data. We can identify issues by plotting the L* data in our .csv file. An annotated example is plotted below, where we can see large excursions from the bulk of our extracted color data that correspond to features we saw in our core photos:

<img width="1883" height="1095" alt="image" src="https://github.com/user-attachments/assets/8fc6f968-91c6-4304-82b8-af75f5e99f5d" />

These artifacts need to be removed from our data. We can do this by sorting the sheet by the L* and clicking yes when prompted about whether you would like to expand the selection. You can find the sort button under the data tab in Microsoft Excel:

<img width="1905" height="1105" alt="image" src="https://github.com/user-attachments/assets/e8d45dc2-3145-4f08-92b7-53de3f672f51" />

First, sort the sheet by Z to A (largest to smallest when used on numbers) to put all of the rows with high L\* values at the top. In our dataset, the largest L\* values that are part of our sedimentary sequence appear to be ~50, so we will remove all L\* values > 55 to be safe. We will do the same thing for very low values by sorting the sheet from A to Z (smallest to largest), but here we will just remove L\* values <0 since the ash layers (a real geologic feature) also have very low L\* values.  *L\* values < 0 should be removed, since measured L\* cannot be < 0 (these occur because of how the program mitigates lighting artifacts).*

Now, sort the sheet again from A to Z by depth. You will see that, while we removed the extreme values, there are still some sharp color changes that we should investigate further by comparing these sharp color changes to our notes and core photographs. For example, if we look at 887A 2H, there are real sharp color changes due to ash layers, but other sharp changes are caused by voids: 

<img width="727" height="1062" alt="image" src="https://github.com/user-attachments/assets/80cccc22-8798-4c52-a7b1-26a5bf767209" />

A good rule of thumb is to check the following places:

i). The top of section 1 of every core, this is the most likely place to be disturbed by the coring process. 

ii). The bottom of each core section, these are sometimes disturbed, presumably by core splitting.

Be careful to only remove color excursions (artifacts) caused by voids or missing sediment! The best way to do this is to carefully compare your color data to core photographs. It is also ok to simply ignore these features if your purpose is to do stratigraphic correlation, but it will likely cause problems for the automatic of off-splice materials to your splice since the calculated signal-to-noise ratio of these features in that algorithm is very high. 

After cleaning, your dataset from 887A should look something like this:

<img width="1211" height="522" alt="image" src="https://github.com/user-attachments/assets/14208a68-7fde-4ed8-af34-2075ea7c233d" />

Repeat this process with 887B. You just finished extracting your first color data!

### Calculating % reflectance from L\*
Core Composite includes a simple function to calculate % reflectance from L* values. An example of how to do that with your 887A color data is included in the "get_reflectance_demo.py" file. 

## Building a new splice / composite section: SpliceBuilderGUI
