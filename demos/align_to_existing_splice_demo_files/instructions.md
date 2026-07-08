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
Like with the other functions in Core Composite, all of the data files should be in the same folder as your script. Set your working directory in spyder to that folder and open the file "compositebuilder_demo.py" - if you are following along with the demo, the script should be ready to run. Your screen should look like this:

<img width="1902" height="1125" alt="image" src="https://github.com/user-attachments/assets/9e03204a-5b31-44b2-b469-2d565ce18ace" />

Here, I am going to walk you through what each part of this code does so that you can modify it for your own projects. This content will be very similar to the instructions for the **SpliceBuilderGUI** because both of these modules use the same data structures. 

