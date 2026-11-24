# Overview
These instructions walk you through how to make a new composite section / splice using Core Composite's SpliceBuilderGUI.

These are the exact same instructions as in the user guide. See the installation guide for help with getting Core Composite running on your device.

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

To get started, open Anaconda Prompt (PC) or the Terminal (Mac / Linux) and activate your python environment where you installed Spyder. Mine is called "workstation" so I use the following command in Anaconda Prompt:

**conda activate workstation**

Now launch spyder with the following command:

**spyder**

Spyder will open to the last script you were working on. Use the navigation buttons to open **splicebuildergui_demo.py** - change your working directory to be the folder that contains **splicebuildergui_demo.py** and the .csv files that you downloaded from GitHub (if you are following the demo) or to the folder that contains the files that you downloaded from Janus if you are following along with data from your drill site. 

**Confused about where the navigation buttons are?**
*Take a look at the user guide or instructions for **Core Photo Analysis** for pictures showing you where these buttons are.*

Once you have the demo script open and the working directory set, spyder should look like this:

<img width="1532" height="911" alt="image" src="https://github.com/user-attachments/assets/2b2f060e-6a14-4358-a46b-c71a44157411" />

If you are following the demo, then the file is already set up to run. Let's walk through what each of the lines of code in this script do so that you can modify it later to work on different drill sites. 

The imports [lines 8-14] do not need to be changed. Line 12 makes the plots appear as popups. I recommend leaving it alone, even if spyder flags an error on that line. It works. Removing that line of code will make the GUI show up in the plots window of spyder, which is not ideal.

IF you are working with your own dataset, the first thing you may need to change are the types of physical properties data you are working with. Here, physical properties data are called "proxies" because proxies is a shorter word than "physical properties data." The "target_proxies" variable reflects the data types that you want plotted in SpliceBuilderGUI. The string (the text within the quotation marks inside the brackets) needs to match at least part of the column header name in one of your data files. 

You can plot any type of data you would like, although there could be some plotting oddities that arise if you use a data type other than the three in this demo (these are the only types of data I tested). If you find a plotting bug, please leave a comment on the GitHub page or contact me via email (my email as of 11/23/2026 is: joseph_novak@brown.edu; since I am a postdoc, my email address will likely change in the future, so take a look at a recent paper of mine to find my up to date contact). 

In addition to specifying the target proxies, you need to tell Core Composite which files to look in to find the information for each hole. This is done in lines 19-29 with the function **"load_from_multiple_files()"** - the function takes up to six arguments:

**hole_name - the hole these data files belong to**

**odp_summary_csv - the name of the file that contains the drilling operations summary file**

**hole_data_files - the data files that belong to that hole**

**data_dir - optional, used if the hole data files are in a different folder than the execution script**

**chunk_size - the length of core over which CompositeBuilder aligns off-splice core sections to the main splice. Default value is 1.0 meter**

**depth_scale - the depth scale used for making the splice. This can either be "mbsf" (the standard ODP depth scale) or "compressed," which is a useful alternative for drill sites with substantial core expansion. Here, we use compressed since that is more appropriate for ODP 887.**

This information is stored in the "hole objects" (hole_A, hole_B, etc.) that need to be added to the builder prior to initializing the SpliceBuilderGUI. This is done in lines 31-33 in the demo with the following commands:

**builder.add_hole(hole_A)**
**builder.add_hole(hole_B)**

Optionally, we can also incorporate core photos into the splicing process if color data was extracted from the core photos using CorePhotoDigitizer. This requires the files that end in "_vertical.png" - these are loaded in with the following function:

**batch_load_core_photos(builder)**

SpliceBuilderGUI is ready to run once the hole objects are added to the builder. This is done with the function **SpliceBuilderGUI()** - this function takes three arguments:

**SpliceBuilderGUI(builder, mudline_hole = "887B", proxy = "density")**

These arguments specify: 1) the name of your builder object, 2) the mudline hole, i.e. the borehole with the shallowest absolute depth core at the drill site. This is usually specified in the initial site report. If you do not have this info, you will need to compare the data from core 1 of the different boreholes to figure out which one contains the uppermost sediment in the sequence.

If you are following along with the demo script, go ahead and press the small green arrow at the top of the spyder tool ribbon. This will run the code and open the SpliceBuilderGUI. The popup containing the GUI will look like this:

<img width="1501" height="830" alt="image" src="https://github.com/user-attachments/assets/6f9e3fc0-f970-431f-9b90-3e4d10a6b938" />

You can press the different bottons on the left side of the plot to cycle between different data types and different boreholes. The data plotted at the top of the plot in black is the composite section / splice that you are building. The "mudline_hole" argument from before determines which core is plotted as a starting point for the correlation. 

The data on the bottom of the plot is from the borehole that is currently selected with the buttons on the right. For longer sequences, it can be useful to zoom in on the region where you are currently working, which you can do using the text boxes on the bottom of the plot. "Undo" removes your last tiepoint, and "Finalize" closes the GUI and builds an affine table. If you loaded in the core photos earlier, you can toggle the "Show Photos" button to display the cropped core photos, scaled to whichever depth scale the builder object is using:

<img width="1482" height="825" alt="image" src="https://github.com/user-attachments/assets/f277f7c2-993d-48db-9b2d-3be0a8a5871e" />


For this demo, I will primarily use the b* and GRAPE WBD data to build the splice since there are pronounced and repeated variations in those data between each of the boreholes. I am going to draw my first tiepoint between 887B 1H (our mudline core) and 887C 1H. To do this, I first left click on the composite at the place where I want to tie in 887C 1H:

<img width="1496" height="812" alt="image" src="https://github.com/user-attachments/assets/28a2f562-79ae-43fa-b1d9-6be0ed963f43" />

The black dashed line shows where the tiepoint is attached to the composite section / splice. Next, right click on the depth interval of 887C 1H you want to tie into the composite section / splice. In my case, I clicked at about 1.25 meters, so the result looks like this:

<img width="1502" height="812" alt="image" src="https://github.com/user-attachments/assets/3ff11ce9-c541-442e-9a2d-516f452c88a5" />

Continue toggling between holes and adding successively deeper cores to build your composite section / splice. Here is what mine looks like:

<img width="1470" height="802" alt="image" src="https://github.com/user-attachments/assets/7719aaa4-6b18-4e56-9fdb-85d938a3470f" />

When you are finished, hit the "Finalize" button. This will pass your affine shifts to Core Composite, which will automatically assign all of the data in the builder object to the composite depth scale and will export the composite core photo, which will appear in a new popup. We can then close the SpliceBuilderGUI popups and review our results in the "ReviewGUI".

<img width="1492" height="816" alt="image" src="https://github.com/user-attachments/assets/dcdb9941-345d-4b87-899a-7f45c433cad8" />

Here, the composite section is plotted at the bottom. The data above it are from each of the parallel boreholes. The blue data are the values that compose the composite section / splice, and the red data are the off-splice data. The program attempts to align the off-splice data with the composite, which you can verify in this GUI. If you are satisified with the alignment, hit "Export and Save." 

Further instructions on how to refine these off-splice alignments can be found in the "Align to Existing Splice" demo. 

## Placing subsamples onto the composite depth (MCD) scale
So now you have a splice, how do you place your samples onto that depth scale? Included in this folder is a short script that calls a function for this in Core Composite. Go ahead and download **"map_subsamples_to_mcd_demo.py"** - this file will use the composite depth scale we just made to assign calcium carbonate wt. % measurements from ODP 887 to the composite depth scale. 

Looking at this script, you will notice that it is very similar to the previous demo. That is because the mapping function requires us to define the builder object. If you are working on your own core, make sure that lines 10-32 match what you did to put together the builder object in your work. Then, at line 35, load in the affine table that you made last time. 

You are now ready to call the function **"map_subsamples_to_mcd"** - this function requires three arguments:
**1). the builder object**

**2). the input file name, as a string**

**3). the output file name, as a string**
