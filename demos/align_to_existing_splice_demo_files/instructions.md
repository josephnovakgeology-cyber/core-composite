# Overview
These instructions walk you through how to use Core Composite to align off-splice materials to a published composite section / splice. We are going to use the composite section from ODP 883 of Keigwin (1995, doi:10.2973/odp.proc.sr.145.116.1995) since this is a nice example of a site with multiple parallel holes with substantial unutilized off-splice material.

These are the exact same instructions that appear in the user guide. 

## Required Files
The required files for this demo can be found in **core_composite/demos/align_to_existing_splice_demo_files**

There are a substantial number of files because we are working with data from four holes. We will base our work on gamma ray attenuation porosity evaluator (GRAPE) wet bulk density (WBD) and magnetic susceptibility data. These files are freely available in the Janus web database. The required files are:

**1). The coring summary file for ODP Site 883 ("883_summary.csv")**

**2). The physical properties data files ("883A_GRAPE_WBD.csv", "883A_magsus.csv", etc.)**

**3). The published affine table ("Keigwin_splice.csv")**

## Alignment of off-splice materials to a published composite section / splice
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
