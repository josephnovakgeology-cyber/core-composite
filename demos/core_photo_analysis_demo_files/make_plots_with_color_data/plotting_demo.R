#### loading in data files ####
setwd("C:/Users/josep/OneDrive/Documents/papers/automated_compsite_section_generator/data analysis/969")
L_synthetic_969 = read.csv('Site969_Hole_A_Color_Reflectance.csv')

### making "thinned" datasets ####
# EXPLANATION:
# the command below is taking every 10th row from the synthetic color
# data file and putting them into a new data frame object. 
#
# We will use this new data frame object for plotting.
thinned_synth_data <- L_synthetic_969[seq(1, nrow(L_synthetic_969), by=10), ]

#### plotting ####

plot(thinned_synth_data$Depth..mbsf., thinned_synth_data$L., type = 'l', col = 'darkgray', 
     xlab = 'Depth (mbsf)', ylab = 'Synthetic L*', bty = 'n', lwd = 2,xlim = c(0, 40), ylim = c(0, 80))
