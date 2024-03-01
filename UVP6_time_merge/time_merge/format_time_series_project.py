import pathlib
from datetime import datetime
from os import path
from tqdm import tqdm
from usr_input import PathInput
from functions import extract_date
from functions import append_files
from usr_input import StartInput
from usr_input import StepInput
from functions import split_data
from functions import write_splitted_data
from functions import read_acq
from functions import check_acq
from functions import init_folders
from functions import acq_sort
from functions import vig_move

path_to_look_at = PathInput()
print("\nChecking the dates from your data in: ", path_to_look_at)
if not path.isdir(path_to_look_at) :
    print("This path does not exists :", path_to_look_at)


path_tree = pathlib.Path(path_to_look_at)
data_txt_list = path_tree.rglob("*.txt")
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

new_folder= acq_output['folder'].unique()

for i in new_folder:

    path_tree = pathlib.Path(i)
    data_txt_list = path_tree.rglob("*.txt")
    data_txt_string = [str(file_path) for file_path in data_txt_list]
    #Create one file
    my_data = append_files(data_txt_string)

    #Ask for the time step
    step_input = StepInput()

    #Split the long data
    splitted_data = split_data(my_data, step_input, start_input)

    num_time_steps = len(splitted_data)

    print(f"Total Number of Time Steps: {num_time_steps}")

    #Decide the output folder 
    output_folder = i

    #Save all data txt in the folder
    write_splitted_data(splitted_data, output_folder, step_input, start_input)

#Now we check all the "merged" folder and copy the vignettes inside
proj_parent = pathlib.Path(path_to_look_at).parent.absolute()
merged_data_txt_list = proj_parent.rglob("*Merged_data.txt")

path_tree = pathlib.Path(path_to_look_at)
vig_list = path_tree.rglob("*.vig")
vig_string = [str(file_path) for file_path in vig_list]

print(f"\n Copying vignettes into new folders")
for datatxt_merged in tqdm(merged_data_txt_list):
    vig_move(datatxt_merged, vig_string)