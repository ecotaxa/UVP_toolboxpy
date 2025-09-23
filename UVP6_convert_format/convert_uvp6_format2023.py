# The new file is copied in the same folder of the original file.
# Change the metaline format of some data.txt from 2023 to fit the 2021 format.
# Save and archive the data.txt to [...]_2023format.txt
# Read the data text file from uvp6
# Change the hwconf line and the acq line :
# add parameters to fit the old format
# The new file is copied in the same folder of the original file.
#
# uvp6 version = 2024.00
#
# Work for all data.txt in a raw folder of a project
#
# WARNING : does not work with taxo
#
# Remastered of C.Catalano matlab version 03/24 by E.Coicaud-T 09/25

import os
from pathlib import Path
import shutil #Move and rename files
import re
from datetime import datetime

## Save and print the steps done by the script and errors if occur
LOG_FILE = "conversion_log.txt"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as logf:
        logf.write(f"[{timestamp}] {message}\n")
    print(message)


## Detection of the key lines
def find_hw_acq_lines(lines):
    """
    Try to detetect liness HW (hardware) and ACQ (acquisition) in a UVP6 file
    Return HWline, ACQline and the separator line (;)
    """
    HWline = ACQline = line_sep = ""
    for idx, l in enumerate(lines):
        if re.search(r'^HW', l, re.IGNORECASE):
            HWline = l
        elif re.search(r'^ACQ', l, re.IGNORECASE):
            ACQline = l
        elif ';' in l:
            line_sep = l
    return HWline, line_sep, ACQline


## File conversion to the old format
def from2023format_to_old_uvp_data(file_path: Path):
    try:
        with open(file_path, 'r') as f:
            lines = f.read().splitlines()

        # Add empty lines after the two first lines
        new_lines = []
        if len(lines) >= 2:
            new_lines.append(lines[0])
            new_lines.append('')
            new_lines.append(lines[1])
            new_lines.append('')
            new_lines.extend(lines[2:])
        else:
            new_lines = lines

        # Detect HWline and ACQline
        HWline, line_sep, ACQline = find_hw_acq_lines(new_lines)

        # Save the original
        old_file_path = file_path.with_name(file_path.stem + '_2023format.txt')
        shutil.move(str(file_path), str(old_file_path))

        # Modify HWline
        HW_parts = HWline.split(',') if HWline else []
        if len(HW_parts) >= 13:
            HW_parts = HW_parts[:7] + ['0'] + HW_parts[7:13] + ['193.49.112.100'] + HW_parts[13:]
        new_HWline = ','.join(HW_parts) if HW_parts else HWline

        # Modify ACQline
        ACQ_parts = ACQline.split(',') if ACQline else []
        if len(ACQ_parts) >= 16:
            ACQ_parts = ACQ_parts[:5] + ['1'] + ACQ_parts[5:9] + ['10'] + ACQ_parts[9:16] + ['0'] + ACQ_parts[16:-5] + ACQ_parts[-2:]
        new_ACQline = ','.join(ACQ_parts) if ACQ_parts else ACQline

        # Write the new file
        rebuilt_lines = []
        if new_HWline:
            rebuilt_lines.append(new_HWline)
#        if line_sep:  # typiquement un ";"
#            rebuilt_lines.append(line_sep)
        if new_ACQline:
            rebuilt_lines.append(new_ACQline)

        rebuilt_lines.extend(new_lines[2:])

        with open(file_path, 'w') as f:
            f.write("\n".join(rebuilt_lines) + "\n")

        log_message(f"✅ Converted: {file_path} (original saved as {old_file_path})")

    except Exception as e:
        log_message(f"⚠️ Error processing {file_path}: {e}")

## Convert all the files in the folders of the raw folder
def convert_all_uvp6(root_folder):
    root_folder = Path(root_folder)
    if LOG_FILE in os.listdir(root_folder):
        os.remove(root_folder / LOG_FILE)
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.endswith('.txt'):
                from2023format_to_old_uvp_data(Path(dirpath) / filename)

# ===========================
# Call
# ===========================
if __name__ == "__main__":
    data_root = input("Enter the path of the raw folder with the old format to be converted:")
    # example of path_to_look_at /home/jhabib/plankton/uvp6_missions/uvp6_sn000123lp/uvp6_sn000123lp_2021_23W0N_830m/raw
    convert_all_uvp6(data_root)
    log_message("🎉 All files processed.")

