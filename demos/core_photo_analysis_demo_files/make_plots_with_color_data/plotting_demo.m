%%%% loading in data files %%%%
% Set the working directory
cd('C:/Users/josep/OneDrive/Documents/papers/automated_compsite_section_generator/data analysis/969');

% Read the CSV file into a MATLAB table
L_synthetic_969 = readtable('Site969_Hole_A_Color_Reflectance.csv');

%%% making "thinned" datasets %%%%
% EXPLANATION:
% the command below is taking every 10th row from the synthetic color
% data file and putting them into a new table object. 
%
% We will use this new table object for plotting.
thinned_synth_data = L_synthetic_969(1:10:end, :);

%%%% plotting %%%%
% Create a new figure window
figure;

x_data = thinned_synth_data.Depth_mbsf_; 
y_data = thinned_synth_data.L_;

% Plot the data
plot(x_data, y_data, 'Color', [0.66, 0.66, 0.66], 'LineWidth', 2);

% Add axis labels and limits
xlabel('Depth (mbsf)');
ylabel('Synthetic L*');
xlim([0, 40]);
ylim([0, 80]);
box off;