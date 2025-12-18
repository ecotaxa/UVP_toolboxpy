import pathlib
import shutil
from concurrent.futures import ThreadPoolExecutor
import os
from tqdm import tqdm

def copy_merged_to_project(src_root, dst_root, workers=8, dry_run=False):
    """
    Copies only files from *_Merged folders to the destination.
    - Ignore *_UsedForMerge folders
    - Keeps the complete tree structure
    - Don't copy identical files (which have the same size)
    - dry_run=True : Only show what would be copied
    """
    src_root = pathlib.Path(src_root)
    dst_root = pathlib.Path(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    # Listing of all files of *_Merged folders
    all_files = [
        f for f in src_root.rglob('*')
        if f.is_file()
    ]

    print(f"\nTotal number of files to copy found in *_Merged : {len(all_files)}")
    files_to_copy = []

    # Set-up the "files to copy" list 
    for src_file in all_files:
        rel_path = src_file.relative_to(src_root)
        dst_file = dst_root / rel_path
        if not dst_file.exists() or os.path.getsize(dst_file) != os.path.getsize(src_file):
            files_to_copy.append((src_file, dst_file))

    print(f"Files to copy : {len(files_to_copy)}\n")

    if dry_run:
        for src_file, dst_file in files_to_copy:
            print(f"[DRY RUN] {src_file} -> {dst_file}")
        if len(files_to_copy) > 10:
            print(f"... et {len(files_to_copy) - 10} autres fichiers")
        print("\nNo files have been copied (dry run activated).")
        return

    # Copy function
    def copy_one(pair):
        src_file, dst_file = pair
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_file, dst_file)

    # Copy with progress bar
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(tqdm(executor.map(copy_one, files_to_copy), total=len(files_to_copy), desc="Copie en cours"))

    print(f"\n✅ Copie terminée : {len(files_to_copy)} fichiers copiés.")

# --- Execution ---
#src = "/home/ecoicaud/plankton_rw/uvp6_missions/uvp6_sn000238lp/uvp6_sn000238lp_2024_anerisvilanova/raw_b"
src = input("Enter the path of the folder where files to copy are stored: ")
#dst = "/home/ecoicaud/plankton_rw/uvp6_missions/uvp6_sn000238lp/uvp6_sn000238lp_2024_anerisvilanova_UVon/raw"
dst = input("Enter the path of the folder where you want to copy the files: ")

# dry_run=True → to try what could be copied
copy_merged_to_project(src, dst, dry_run=False)


