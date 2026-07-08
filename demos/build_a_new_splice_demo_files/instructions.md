# Overview
These instructions walk you through how to make a new composite section / splice using Core Composite's SpliceBuilderGUI.

These are the exact same instructions as in the user guide. See the installation guide for help with getting Core Composite running on your device.

## Building a new splice / composite section: SpliceBuilderGUI
SpliceBuilderGUI is a point-and-click interface for manually identifying tiepoints between parallel boreholes at a drill site. The software is set up to conveniently work with DSDP, ODP, and IODP datasets, but can in-principal be used with any type of drilling data provided that you have adequate supporting information about the driller's wire line depth scale and the recovery of sediments within each of the cores taken from a given borehole.

### Required Files
**The files required to use SpliceBuilderGUI are:**

**1). At least one set of physical properties data that was measured at each of the boreholes that will be included in your splice / composite section.**

**2). The coring summary, which specifies the cored length of each core recovered from the drill site.**

All of the files necessary to go through the demo are included in: **core_composite/demos/build_a_new_splice_demo_files**

The magnetic susceptibility, gamma ray attenuation and porosity evaluator (GRAPE) wet bulk density (WBD), and coring summary were downloaded from the ODP Janus database (https://www-odp.tamu.edu/database/). *You can access these data using the same procedure outlined in the User Guide and Instructions for the image processing demo, but clicking the links for "Magnetic Susceptibility (sections)" ; "GRA Bulk Density (sections)" or ; "Hole / Core Summary (cores)."

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

