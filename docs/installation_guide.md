# Overview
Core Composite (`core_composite`) is a Python library for stratigraphic correlation of scientific drilling materials. The library includes three main tools:

**1) CorePhotoDigitizer** is an interactive GUI for processing legacy core photographs from the DSDP, ODP, and IODP contained within the `image.py` module. 
CorePhotoDigitizer allows geoscientists to extract L*, a*, and b* from analog and digital core photos, which is especially useful when working on drilling sites with no other useful archived stratigraphic information. 
CorePhotoDigitizer also allows users to convert L* values to % reflectance. 

**2) CompositeBuilder** is an algorithm that takes new or published affine shifts and uses them as the basis for automated centimeter-scale dynamic stretching or squeezing of off-splice drilling materials so that they are aligned to the main composite section for a set of parallel boreholes within the `builder.py` module. 
This algorithm is particularly useful for maximizing the scientific lifespan of very heavily sampled drill sites with preexisting composite stratigraphies and age models that need to be applied to off-splice cores that still have unsampled material.

**3) SpliceBuilderGUI** is an interactive GUI that enables users to generate new composite sections from physical properties data within the `gui.py` module. 

## Getting Started
### Installation

Core Composite is installable via pip and is written for use in the Spyder integrated development environment. 

This guide is intended for folks who have no experience with Python but are interested in using Core Composite. Let me walk you through how to get Core Composite running on your computer. If you run into trouble, please email me. I am happy to help and want to make this guide useful to the most number of people possible.

#### Step 1: Download the Software

1. Go to the main page of this GitHub repository.
2. Click the green **Code** button near the top right of the page.
3. Click **Download ZIP**.
4. Locate the downloaded ZIP file in your Downloads folder.
5. Extract (unzip) the folder and move it to a safe location on your computer, such as your Documents folder. 

#### Step 2: Install Miniconda 
To run Core Composite, you need install miniconda on your computer. Miniconda is a tool that allows you to set up isolated python environments so that different projects do not interfere with each other. 

1. Go to [Anaconda's official website](https://www.anaconda.com/download) and download the installer for your operating system (Windows or Mac).
2. Run the installer and click "Next" through the default setup options.
3. Paths diverge here for Windows vs. Mac:
   - Windows: click the start menu, type Anaconda Prompt, and open the application
   - Mac: Open your standard terminal application

#### Step 3: Set up the Spyder Environment
It is best practice to install the Spyder application, which runs Core Composite, in a dedicated and separate python environment to prevent software conflicts. 

1. In your Anaconda Prompt or Terminal, type the following command exactly as written and press **Enter** to create a new environment named "workstation," which will house Spyder:
    **conda create -n worstation python=3.12 -y**
2. Activate the new environment:
   **conda activate workstation**
3. Install the Spyder application into this environment:
   **conda install -c conda-forge spyder -y**

#### Step 4: Create the Core Composite Environment
Now you will create a completely separate environment for Core Composite. This prevents conflicts between the software's dependencies and those of Spyder.

1. Type the following command exactly as written and press **Enter**: 
   `conda create --name core_composite -c conda-forge python=3.12 spyder pyqt -y`
2. Next, activate the new envionment: 
   `conda activate core_composite`
*(You should now see `(core_composite)` at the beginning of the text line in your terminal.)*

#### Step 5: Install Core Composite
Now you need to install Core Composite into your core_composite Python environment.

*(the following should be done inside the core_composite environment, meaning you should still see core_composite at the beginning of the test line in your terminal / anaconda prompt)*

1. Type `cd` followed by a space, and then type the file path to the folder you unzipped in Step 1. 
   *(Example: `cd C:\Users\YourName\Documents\core_composite-main`)*
2. Press **Enter**.
3. Type the following command exactly as written (do not forget the period at the end): 
   `pip install -e .[dev,qt]`
4. Press **Enter**.

**TROUBLESHOOTING**
If you get the "pip not found" error, try this:
Windows: py -m pip install .
Mac / Linux: python3 -m pip install .

Your screen will print out a lot of text as it automatically downloads all the necessary background tools. Once it stops, Core Composite is installed and ready to use.

#### Step 6: Connect Spyder to the core_composite environment
Lastly, we will need to open Spyder and connect it to your python environment. 

1. Type: **conda deactivate core_composite** and press Enter
2. Type: **conda activate workstation** and press Enter
3. Type: **spyder** and press Enter

You should see the following open after a few moments:

<img width="1535" height="907" alt="image" src="https://github.com/user-attachments/assets/da4d4c20-e4f7-40a9-9ae1-f4572fe7bf28" />

**Note: you may see a warning that "Spyder has encountered an internal problem. This is a well-known issue with the most recent version of Spyder and it will be addressed when the developer of the application releases their next update.**

4. In Spyder, press the "Tools" button on the top ribbon.
5. Select "Preferences"
6. Select "Python Interpreter"
7. Select the file path to the core_composite environment. On my computer, this is: C:\Users\josep\anaconda3\envs\core_composite\python.exe
8. Select "Apply"
9. Select "Ok"
10. In the Spyder interface, select this button:

<img width="1548" height="907" alt="image" src="https://github.com/user-attachments/assets/d1ea39f7-e997-43ae-9464-f1461797f24a" />

11. Select "Restart Kernel"

You may see the "Spyder has encountered an internal problem" warning again. 

12. You have successfully installed Core Composite! Congratulations and thank you for sticking with it. 
