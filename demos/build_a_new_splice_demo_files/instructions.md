# Overview
These instructions walk you through how to make a new composite section / splice using Core Composite's SpliceBuilderGUI.

These are the exact same instructions as in the user guide. See the installation guide for help with getting Core Composite running on your device.

## Building a new splice / composite section: SpliceBuilderGUI
SpliceBuilderGUI is a point-and-click interface for manually identifying tiepoints between parallel boreholes at a drill site. The software is set up to conveniently work with DSDP, ODP, and IODP datasets, but can in-principal be used with any type of drilling data provided that you have adequate supporting information about the driller's wire line depth scale and the recovery of sediments within each of the cores taken from a given borehole.

### Necessary Files

All of the files necessary to go through the demo are included in: **core_composite/demos/build_a_new_splice_demo_files**

The magnetic susceptibility and gamma ray attenuation and porosity evaluator (GRAPE) wet bulk density (WBD) data were downloaded from the ODP Janus database (https://www-odp.tamu.edu/database/). *You can access these data using the same procedure outlined in the User Guide and Instructions for the image processing demo, but clicking the links for "Magnetic Susceptibility" and "GRA Bulk Density." 

The color data (L\*, a\*, b\*) were extracted from core photos using Core Composite's CorePhotoDigitizer. These are the exact same files that were produced from **image_processing_demo.py** 
