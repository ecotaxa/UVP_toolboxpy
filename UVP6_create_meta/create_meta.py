# Script to create the meta of a UVP mooring project
#14.03.2024 J.H.
#you should have the directory of the file, your Lon and lat to insert 
#for now the script saves the txt file in your repertory, and you should put it in the folder manually 
#
# author : Joelle Habib, 2024
 

# libraries
import re
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from os import path
import pathlib

#the constants that you have to insert manually 
sampletype='T' 
integrationtime=3600 #always 3600
first_image=0
ship='mooring'

#you should add the path without ' '  and until folder raw where the merged file are present
#from youre home directory
path_merged_data = input("Enter the path of the folder where the merged data is stored: ")

# example of path_to_look_at /home/jhabib/plankton/uvp6_missions/uvp6_sn000123lp/uvp6_sn000123lp_2021_23W0N_830m/raw


print("\nChecking the dates from your data in: ", path_merged_data)
if not path.isdir(path_merged_data) :
    print("This path does not exists :", path_merged_data)

#insert lat, lon 
print("\nLongitude positive to Est, Latitude positive to North")
print("Longitude and latitude in decimal degrees")
longitude = float(input("Enter the longitude of the mooring, beware if it's negative: "))
latitude = float(input("Enter the latitude of the mooring, beware if it's negative: "))

#longitude=-23.07
#latitude=0.00  

#determine constantdepth from the name of the file 
# the name of the uvp6 project must finish by the depth and "m" as in "_37m"
# Split the path by '/' or '\'
splited_path_merged_data = os.path.split(path_merged_data)

# Iterate through the components of the path to find the depth
constantdepth = None
for part_path in splited_path_merged_data:
    if part_path.endswith("m"):
        depth_str = part_path[:-1]  # Remove 'm'
        depth_parts = depth_str.split('_')
        constantdepth = int(depth_parts[-1])
                

if constantdepth is not None:
    print("\nDepth:", constantdepth)
else:
    print("\nDepth not found in the path, you should add it manually.")
    depth_input = input("Enter the depth of the samples : ")
    try:
        constantdepth = float(depth_input)
    except:
        print("\nNo valid depth input: no constant depth for those samples")
        constantdepth = np.nan


    
# Find the component of the path containing 'uvp6_sn' and extract the relevant part
station_id = None
for path_part in splited_path_merged_data:
    if 'uvp6_sn' in path_part and path_part.endswith("m"):
        station_id = '_'.join(path_part.split('_')[-2:])
        break

if station_id is not None:
    print("\nstationid:", station_id)
    stationid = 'Mooring_' + station_id
else:
    print("\nStation ID not found in the path, you should add it manually.")
    stationid = input("Enter the station id: ")
  

#open the file of txt HW in config
path_uvp_project = os.path.dirname(path_merged_data)  # Extract the parent directory one levels up
path_config = os.path.join(path_uvp_project, 'config')


path_tree = pathlib.Path(path_config)
config_txt_list = path_tree.rglob("HW*.txt") #choose HW file in config for the volima, aa and exp
config_txt_string = [str(file_path) for file_path in config_txt_list]

for input_file_path in config_txt_string:
    
    # Open the input file for reading
    with open(input_file_path, 'r') as input_file:
    # Read all lines from the input file, skipping the first two rows
    
        lines = input_file.readlines()[:]
        # Extract values for "Pixel_Size", "Exp", and "Image_volume", "Aa"
        for line in lines:
            line = line.strip()
            if "Pixel_Size = " in line:
                pixel_size_value = float(line.split('=')[1].strip())
                pixel_size_value=pixel_size_value/1000
        
            elif "Exp = " in line:
                exp_value = float(line.split('=')[1].strip())
               
            elif "Image_volume = " in line:
                image_volume_value = float(line.split('=')[1].strip())
            
            elif "Aa = " in line:
                Aa_value = float(line.split('=')[1].strip())
                Aa_value=Aa_value/1000000    

                #open cruise 
cruise_list = path_tree.rglob("cruise*.txt") #choose HW file for the volima, aa and exp
cruise_string = [str(file_path) for file_path in cruise_list]

for input_file_path in cruise_string:
    
    # Open the input file for reading
    with open(input_file_path, 'r') as input_file:
    # Read all lines from the input file, skipping the first two rows
        lines = input_file.readlines()[:]
        for line in lines:
            line = line.strip()
            if "acron=" in line:
                cruise_value = line.split('=')[1].strip()

                
path_tree = pathlib.Path(path_merged_data)
data_txt_list = path_tree.rglob("*Merged_data.txt")
data_txt_string = [str(file_path) for file_path in data_txt_list]

file_header = ['cruise','ship','filename','profileid','bottomdepth','ctdrosettefilename'	,'latitude',	'longitude',	'firstimage',
               'volimage','aa','exp','dn','winddir','windspeed','seastate','nebuloussness','comment',	'endimg','yoyo',	'stationid','sampletype',
               'integrationtime','argoid','pixelsize','sampledatetime','constantdepth']
 
file_df = pd.DataFrame(columns = file_header)
filename_list = []
profileid_list= []
endimg_list=[]
sampledatetime_list=[]

#filename corresponds to the name of the file I will open 
for input_file_path in data_txt_string:  
    # Extract the file name without extension
    file_name_without_extension = pathlib.Path(input_file_path).stem
    folder_name = os.path.basename(os.path.dirname(input_file_path)) #NEW
    # Find matches in the file name
    matches = re.findall("[0-9]{8}-[0-9]{6}", file_name_without_extension)
    
    if matches:
        match_result = cruise_value+"_"+matches[-1][:8]
        filename_list.append(folder_name)
        profileid_list.append(match_result)
    
    # Open the input file for reading
    with open(input_file_path, 'r') as input_file:
     # Read all lines from the input file, skipping the first two rows
          lines = input_file.readlines()[4:]
                   
          #find the number of the last image 
          endimg=float(np.size(lines)-1)/2
          endimg_list.append(endimg)
          
          #take the first value in the first string before the comma in each row
          first_string = lines[0].split(',')[0].strip()
          date_time_millisec = first_string.split('-')  #careful to the different format in uvp data
          date_time = date_time_millisec[0] + '-' + date_time_millisec[1]
          sampledatetime_list.append(date_time)
        
# Creating a dictionary with the lists
print('create dic with lists')
data = {
    'filename': filename_list,
    'profileid': profileid_list,
    'endimg': endimg_list,
    'sampledatetime': sampledatetime_list
}


# Creating a DataFrame from the dictionary
df = pd.DataFrame(data)    


#find the shape so I can duplicate the rest 
n=df.shape[0]


#create df to facilitate repeat
cst_variables= {
    'cruise': cruise_value,
    'ship': ship,
    'latitude':latitude,
    'longitude':longitude,
    'firstimage':first_image,
    'volimage':image_volume_value,
    'aa': Aa_value, 
    'exp': exp_value,
    'sampletype':sampletype,
    'integrationtime':integrationtime,
    'pixelsize':pixel_size_value,
    'constantdepth':constantdepth,
    'stationid':stationid}  

# Creating a DataFrame from the dictionary
df_cst = pd.DataFrame([cst_variables])    

# using repeat() to repeatedly print number    
df_repeat=pd.concat([df_cst] * n, ignore_index=True)

# Combine df and df_repeat
df_combined = pd.concat([df, df_repeat], axis=1)

# Create new columns with NaN values
new_columns = ['bottomdepth', 'ctdrosettefilename', 'dn', 'winddir', 'windspeed', 'seastate', 'nebuloussness', 'comment', 'yoyo', 'argoid']
df_combined[new_columns] = np.nan

# Replace the column names with the actual names in your DataFrame
df_combined = df_combined[['cruise', 'ship', 'filename', 'profileid', 'bottomdepth', 'ctdrosettefilename', 
                           'latitude', 'longitude', 'firstimage', 'volimage', 'aa', 'exp', 'dn', 'winddir', 
                           'windspeed', 'seastate', 'nebuloussness', 'comment', 'endimg', 'yoyo', 'stationid', 
                           'sampletype', 'integrationtime', 'argoid', 'pixelsize', 'sampledatetime', 'constantdepth']]


print('finished combined dataframe')
#bottomdepth ctdrosettefilename dn winddir windspeed seastate nebuloussness comment yoyo argoid 


df_combined = df_combined.sort_values(by='sampledatetime')

df_combined['endimg'] = df_combined['endimg'].astype(int)


####Create text file 
#save the combined file in your folder on the server 
home_path = str(pathlib.Path.home())
uvp_project_name = os.path.split(path_uvp_project)[1]
parts = uvp_project_name.split("_", 1)  # Split the string into two parts at the first underscore
file_name = parts[0] +'_header_'+ parts[1] + ".txt"

file_path = os.path.join(home_path, file_name)

print(file_path)
df_combined.to_csv(file_path, sep=';', index=False, na_rep='nan')
