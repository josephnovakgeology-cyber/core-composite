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

This guide is intended for folks who have no experience with Python but are interested in using Core Composite. Let me walk you through how to get Core Composite running on your computer.

#### Step 1: Download the Software

1. Go to the main page of this GitHub repository.
2. Click the green **Code** button near the top right of the page.
3. Click **Download ZIP**.
4. Locate the downloaded ZIP file in your Downloads folder.
5. Extract (unzip) the folder and move it to a safe location on your computer, such as your Documents folder. 

#### Step 2: Install Python
To run Core Composite, you need Python installed on your computer. The safest and easiest way to do this is by downloading Anaconda, which is a free package manager built specifically for scientists.

1. Go to [Anaconda's official website](https://www.anaconda.com/download) and download the installer for your operating system (Windows or Mac).
2. Run the installer and click "Next" through the default setup options.

#### Step 3: Create a Python Environment
We will install Core Composite within a dedicated Python virtual environment. This avoids any potential future conflicts with libraries you install for later projects. 

1. Open your computer's application search bar. 
2. If you are on Windows, search for and open **Anaconda Prompt**. If you are on a Mac, search for and open **Terminal**.
3. Type the following command exactly as written and press **Enter**: 
   `conda create --name core_composite python=3.10 -y`
4. Wait a few moments for it to finish setting up the sandbox. 
5. Next, "enter" the sandbox by typing this command and pressing **Enter**: 
   `conda activate core_composite`
*(You should now see `(core_composite)` at the beginning of the text line in your terminal.)*

#### Step 4: Install Core Composite
Now you need to install Core Composite into your Python environment.

1. In that same Anaconda Prompt / Terminal, type `cd` followed by a space, and then type the file path to the folder you unzipped in Step 1. 
   *(Example: `cd C:\Users\YourName\Documents\core_composite-main`)*
2. Press **Enter**.
3. Type the following command exactly as written (do not forget the period at the end): 
   `pip install .`
4. Press **Enter**.

Your screen will print out a lot of text as it automatically downloads all the necessary background tools. Once it stops, Core Composite is installed and ready to use.

#### Step 5: Install and Open Spyder
Lastly, we will need to install Spyder so that we have an easy way to run code that uses Core Composite. Spyder is a user-friendly application where you can read, edit, and run Python scripts. 

1. While still in your `(core_composite)` terminal, type the following command and press **Enter**:
   `conda install spyder -y`
2. Wait a minute or two for Spyder to download and install into your sandbox.
3. Once it is finished, simply type `spyder` and press **Enter**.
