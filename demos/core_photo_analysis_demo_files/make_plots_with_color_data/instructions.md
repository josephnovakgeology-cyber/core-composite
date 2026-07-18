# Overview
So, you extracted your color data, but how do you make a decent looking figure with it? 

A problem you may have noticed is that the color data files are really big, especially when working on long sediment successions. It can quickly become 
possible to have files with too many points for you to make .pdf files for publication since the number of data points will exceed the limits of what 
a .pdf renderer will allow. The R, MATLAB, and python code in this folder give examples of how I prefer to deal with this problem. 
## Solution 
The way I prefer to handle this is to subsample my color data before plotting. The easiest way is to create a dataframe of every 10th data point in your 
color data file. This will retain the same structures as the full data file since the color data are at the pixel level (which corresponds to the mm length scale)
but will substantially reduce the number of points that need to be rendered, which lowers the final .pdf file size and makes it possible to load your .pdf files
into applications like Adobe Illustrator for making your figures nice and fancy prior to publication.

The specific instructions for the R and python version of the code are included as comments in the .R or .py files. 
