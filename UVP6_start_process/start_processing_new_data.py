# The data downloaded from the UVP6 are presented as "2025.05" which means "the fifth download of 2025",
# inside which you can find sub-folders name "09-11, 09-12, 09-13, 09-14, 09-15, 09-16, 09-17..." 
#each corresponding to an acquisition day. 

# In order to process the data you should copy the downloaded files in the raw folder of the project without the 
# grouping by day.

# First you can choose to erase the files within the raw folder if they have been previously processed
# Secondly you can copy the dowloaded folders to be processed. If a folder is already copy it won't be copy twice 
# Because it is set-up as "Overwritting= False" to avoid conflicts, but you can change this parameter. 


import os 
import shutil
from pathlib import Path

from datetime import datetime

LOG_FILE = "process_log.txt"

def log_message(message):
    """Écrit un message dans un fichier log avec un timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as logf:
        logf.write(f"[{timestamp}] {message}\n")

def actualise_raw_folder(download_folder: str, project_folder: str):
    """
    - Empty the 'raw' folder of the project
    - Copy the contents of the daily subfolders to 'raw'
    """
    download_path = Path(download_folder)
    if not download_path.exists():
        raise FileNotFoundError(f"File {download_folder} does not exist") 

    raw_path = Path(project_folder) / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    ask_delete = input("Do you want to delete the raw content ? (y/n)")

    # Empty raw content (not the folder) if asked to
    if ask_delete.lower() == "y":
        for item in raw_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
            log_message(f"🗑️ Content of {raw_path} deleted")
        print(f"🗑️ Content of {raw_path} deleted")
    else:
        print("⚠️ raw stay untouched")   

def copy_to_raw(src_dir: Path, raw_path: Path, overwrite=False):
    """
    Copy sub-folders from src_dir into raw_path.
    If overwrite=False, skip any folder already present.
    """
    counters = {"copied": 0, "skipped": 0}

    for sub in src_dir.iterdir():
        dest = raw_path / sub.name
        if sub.is_dir():
            if dest.exists() and not overwrite:
                log_message(f"⚠️ Skipped folder (already exists): {dest}")
                counters["skipped"] += 1
            else:
                for root, _, files in os.walk(sub):
                    rel_path = os.path.relpath(root, sub)
                    target_dir = dest / rel_path
                    target_dir.mkdir(parents=True, exist_ok=True)
                    for file in files:
                        src_file = Path(root) / file
                        dst_file = target_dir / file
                        shutil.copyfile(src_file, dst_file)
                        log_message(f"✅ Copied file: {dst_file}")
                        counters["copied"] += 1
                log_message(f"📂 Processed directory: {dest}")

        elif sub.is_file():
            if dest.exists() and not overwrite:
                log_message(f"⚠️ Skipped file (already exists): {dest}")
                counters["skipped"] += 1
            else:
                shutil.copyfile(sub, dest)
                log_message(f"✅ Copied file: {dest}")
                counters["copied"] += 1

    print(f"✅ Copy finished for {sub.name}: {counters['copied']} files copied, {counters['skipped']} skipped")


# ======================
# Call
# ======================
if __name__ == "__main__":
    download_folder = Path(input("Path to the downloaded folder:"))
    project_folder = Path(input("Path to the project folder:"))
    
    actualise_raw_folder(download_folder, project_folder)
    
    raw_path = Path(project_folder) / "raw"
    for sub_dir in download_folder.iterdir():
        if sub_dir.is_dir():
            copy_to_raw(sub_dir, raw_path, overwrite=False)

