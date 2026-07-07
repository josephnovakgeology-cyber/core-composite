# Overview
If you are struggling to figure out how to install Core Composite, please check out the installation guide :)

This doc will walk you through how to use the three major tools within Core Composite:

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
