# UVP6_time_merge
Merge different acquisition sequences on a constant time step.

## How to use it

Download this repo with git clone.
```
git clone git@github.com:Flavi1P/UVP6_time_merge.git
```
Launch time_merge/format_time_series_project.py.py
```
/usr/bin/pyton UVP6_time_merge/time_merge/format_time_series_project.py
```
Look at your terminal to give the input needed (input folder, start date time, time step, output folder)

## What does it do ?

While the time_merge/functions.py can help you formatting your project "by hand" the time_merge/format_time_series_project.py is a workflow easy to use that will do it for you. Here is the few step it goes through.

### Invite the user to specify the project, date range and time step of the split/merge to execute

When you will execute format_time_series_project.py a message will prompt you to provide the path of a UVP project with a time series acquisition. The project should be organise as a standard UVP6 project, with a "raw" folder that includes different data.txt and associated vignettes. 
The user will then chose when he wants to start the split/merge operation.

### Split your project into different project depending on acquisition configuration

One important prerequisite of merging and splitting acquisition is to make sure that we merge data that have been acquired with the same method. The package is thus designed to split your original project in as much project as there is unique acquisition configuration. Each new project will be name "project_a", "project_b" etc... 
The original datatxt will be copied in the new project. 

### Merge and/or split the data

Once we are sure that our projects have the same acquisition parameters we can proceed to data manipulation. The user will input a time step on which he want to reshape the new projects (one per acq conf). The new datatxt will be name like "'%Y%m%d-%H%M%Smerged_data.txt". 

### Moving vignette to new project

Finally, the vig will be copied from the old project, based on the different dates of the merged_data.txt dates.
