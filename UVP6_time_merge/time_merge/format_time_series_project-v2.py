# Main script for UVP6_time_merge modify with a better performance to copy vignettes
#
# author : Flavien Petit, 2024, modified by : Ema Coicaud-Tournois, 10-2025

import pathlib
from datetime import datetime
from os import path
from tqdm import tqdm
from usr_input import PathInput
import zipfile
from functionsv2 import extract_date
from functionsv2 import append_files
from usr_input import StartInput
from usr_input import StepInput
from functionsv2 import split_data
from functionsv2 import write_splitted_data
from functionsv2 import read_acq
from functionsv2 import check_acq
from functionsv2 import init_folders
from functionsv2 import acq_sort
from functionsv2 import vig_move
from functionsv2 import copy_tree_safe

# -----------------------------
# User parameters
# -----------------------------

#path_to_look_at = "/home/ecoicaud/plankton_rw/uvp6_missions/uvp6_sn000237lp/uvp6_sn000237lp_2024_anerissmartbay/raw"  
#start_input = "20250208-000000"
#step_input = "24"  # heures

# -----------------------------
# Checking available data
# -----------------------------
print("\nChecking the dates from your data in: ", path_to_look_at)
if not path.isdir(path_to_look_at):
    raise FileNotFoundError(f"This path does not exist: {path_to_look_at}")

path_tree = pathlib.Path(path_to_look_at)
data_txt_list = path_tree.rglob('*_data.txt')
data_txt_string = [str(file_path) for file_path in data_txt_list]

date_strings = list()
for i in tqdm(data_txt_string):
    date_t = extract_date(i)
    date_strings.append(date_t)
# Convert strings to datetime objects
date_objects = [datetime.strptime(date_str, "%Y%m%d-%H%M%S") for date_str in date_strings]

# Find the minimum and maximum dates
min_date = min(date_objects)
max_date = max(date_objects)

# Convert back to string format
min_date_str = min_date.strftime("%Y-%m-%d %H:%M:%S")
max_date_str = max_date.strftime("%Y-%m-%d %H:%M:%S")

# Print the range
print(f"\nYou have data that goes from: {min_date_str} to: {max_date_str}")

# -----------------------------
# Copy folders to be merged
# -----------------------------

#Ask when the user wants to start 
start_input = StartInput()
start_input_obj = datetime.strptime(start_input, "%Y%m%d-%H%M%S")

print(f"\nChecking the ACQ configuration")

acq_df = read_acq(data_txt_string)
acq_df['datetime_obj'] = acq_df['datetime'].apply(lambda x: datetime.strptime(x, "%Y%m%d-%H%M%S"))

acq_df_filtered = acq_df[(acq_df['datetime_obj'] > start_input_obj)]
acq_df_filtered = acq_df_filtered.drop('datetime_obj', axis = 1)
result = check_acq(acq_df_filtered)

if result:
    print("Non-constant columns:")
    for column, values in result.items():
        unique_values = set(values)
        print(f"{column}: {unique_values}")
    
else:
    print("All columns have constant values.")

print(f"\nMoving the files into the right directories (i.e. one directory per ACQ configuration)")
acq_output = init_folders(acq_df_filtered, path_to_look_at)
acq_sort(acq_output, path_to_look_at)

# -----------------------------
# Merging folders
# -----------------------------

new_folder= acq_output['folder'].unique()

for i in new_folder:

    path_tree = pathlib.Path(i)
    data_txt_list = sorted(path_tree.rglob("*data.txt"))
    data_txt_string = [str(file_path) for file_path in data_txt_list]
    #Create one file
    my_data = append_files(data_txt_string)

    #Ask for the time step
    print(f"\nFor the config in {path.split(i)[-1]}")
   step_input = StepInput()

    #Split the long data
    splitted_data = split_data(my_data, step_input, start_input)

    num_time_steps = len(splitted_data)

    print(f"Total Number of Time Steps: {num_time_steps}")

    #Decide the output folder 
    output_folder = i

    #Save all data txt in the folder
    write_splitted_data(splitted_data, output_folder, step_input, start_input)

# ---------------------------------------
# Copy vignettes into the Merged folders
# ---------------------------------------
print(f"\n Copying vignettes into new folders")

#Unzip image folders
print(f"Unziping images...")
base_path = pathlib.Path(path_to_look_at)
zip_list = list(base_path.rglob("*.zip"))
for file_path in tqdm(zip_list, desc="Unzipping"):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(file_path.parent)

#Create vignettes index
print("Indexation of the vignettes...")
vig_list = list(base_path.rglob("*.vig"))
vig_string = [str(v) for v in vig_list]

vig_index = build_vig_index(vig_string)

#Now we check all the "merged" folder and copy the vignettes inside
merged_data_txt_list = list(base_path.rglob("*Merged_data.txt"))

#Copy corresponding vignettes into sequences folder
for data_txt in tqdm(merged_data_txt_list, desc="Processing Merged_data.txt"):
    vig_move_indexed(data_txt, vig_index)