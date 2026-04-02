from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import logging
from uvptoolbox.utils import setup_logger, ACQUISITION_FOLDER_PATTERN


def rename_folder_and_files_UsedForMerge(acq_dir: Path, logger: logging.Logger, overwrite: bool) :
    """Rename acquisition folders and data files with _UsedForMerge suffix if needed."""

    if ACQUISITION_FOLDER_PATTERN.match(acq_dir.name):
        new_dir = acq_dir.with_name(acq_dir.name + "_UsedForMerge")

        if new_dir.exists() :
            if overwrite:
                shutil.rmtree(new_dir)
                acq_dir.rename(new_dir)
                logger.info("Reset acquisition directory %s", new_dir.name)
                acq_dir = new_dir
            else :
                logger.debug("Skipping already renamed folder: %s", new_dir.name)
                acq_dir = new_dir
        else:
            acq_dir.rename(new_dir)
            logger.info("Renamed acquisition directory %s", new_dir.name)
            acq_dir = new_dir

    for file in acq_dir.rglob("*_data.txt"):
        if ACQUISITION_FOLDER_PATTERN.match(file.stem.removesuffix("_data")):  # make sure we don't rename a file already named _UsedForMerge_data.txt
            new_file = file.with_name(file.stem.replace("_data", "_UsedForMerge_data") + file.suffix)
            if overwrite or not new_file.exists() :
                file.rename(new_file)
                logger.info("Renamed data file %s", new_file.name)

def concatenate_data_files(data_files: list[Path], logger: logging.Logger):
    """Concatenate multiple UVP data files into header lines and data lines."""
    if not data_files:
        return [], []

    data_files = sorted(data_files)

    # Find HW and ACQ lines from the first file and build the header from them
    hw_line = acq_line = None
    i=0
    while (not hw_line or not acq_line) and i < len(data_files):
        with open(data_files[i], "r") as f:
            for line in f.read().splitlines():
                if line.startswith("HW"):
                    hw_line = line
                elif line.startswith("ACQ"):
                    acq_line = line
            if hw_line is None or acq_line is None:
                logger.warning("HW or ACQ line not found in %s, trying to get them from next data file", data_files[i])
        i += 1
    
    if hw_line is None or acq_line is None:
        logger.error("Unable to find HW and ACQ lines in input files")
        return [], []

    header_lines = [hw_line, "", acq_line, ""]

    # Extract data lines from all files
    data_lines = []
    for file_path in data_files:
        with open(file_path, "r") as f:
            lines = f.read().splitlines()
            data_lines.extend(line for line in lines if line and not (line.startswith("HW") or line.startswith("ACQ")))

    return header_lines, data_lines

def get_min_datetime_from_data_lines(data_lines: list[str]):
    """Return the earliest datetime found in UVP data lines as YYYYMMDD-HHMMSS."""
    datetimes = []

    for line in data_lines:
        if not line:
            continue
        date_time_str = line.split(",", 1)[0]
        try:
            dt = datetime.strptime(date_time_str, "%Y%m%d-%H%M%S")
        except ValueError:
            try:
                dt = datetime.strptime(date_time_str, "%Y%m%d-%H%M%S-%f")
            except ValueError as e:
                raise ValueError(f"Unsupported datetime format: {date_time_str}") from e
        datetimes.append(dt)

    if not datetimes:
        return None

    return min(datetimes).strftime("%Y%m%d-%H%M%S")



def split_data(header_lines: list[str], data_lines: list[str], time_step: float, start_datetime: str):
    """Split concatenated data (output from concatenate_data_files function) using a start datetime and a time step in hours."""
    
    # Initialize a dictionary to store data for each time step
    time_steps_data = defaultdict(lambda: header_lines.copy())
    start_datetime = datetime.strptime(start_datetime, '%Y%m%d-%H%M%S')
    time_step = float(time_step)

    for line in data_lines:
        if not line:
            continue
        # Extract the date and time from the line
        date_time_str = line.split(',', 1)[0]
        try:
            date_time = datetime.strptime(date_time_str, '%Y%m%d-%H%M%S')
        except ValueError:
            try:
                date_time = datetime.strptime(date_time_str, "%Y%m%d-%H%M%S-%f")
            except ValueError as e:
                raise ValueError(f"Unsupported datetime format: {date_time_str}") from e

        # Check if aquisition is after start_datetime
        if date_time < start_datetime:
            continue

        # Calculate the difference in hours from the start_datetime
        time_difference = (date_time - start_datetime).total_seconds() / 3600
        # Determine the time step index
        time_step_index = int(time_difference / time_step)
        # Append the data to the corresponding time step in the dictionary
        time_steps_data[time_step_index].append(line)

    return dict(time_steps_data)


def write_splitted_data(splitted_data: dict, output_folder: Path, time_step: float, start_datetime: str, logger: logging.Logger, overwrite: bool):
    """Write merged/split data files into output folders."""
    
    # Write each time step's data to a separate text file
    step_float = float(time_step)
    start_datetime = datetime.strptime(start_datetime, '%Y%m%d-%H%M%S')

    merged_files = []
    
    for time_step_index, data_list in splitted_data.items():
        # Get the datetime of the first data in the time step
        time_step_datetime = start_datetime + timedelta(hours=time_step_index * step_float)
        datetime_str = time_step_datetime.strftime("%Y%m%d-%H%M%S")

        merged_folder = output_folder / f"{datetime_str}_Merged"
        merged_folder.mkdir(parents=True, exist_ok=True)

        output_file = merged_folder / f"{datetime_str}_Merged_data.txt"

        if output_file.exists() and not overwrite:
            logger.info("Merged file already exists, skipped: %s", output_file.name)
        else:
            with open(output_file, "w") as f:
                for value in data_list:
                    f.write(f"{value}\n")
            logger.info("Merged file written: %s", output_file.name)

        merged_files.append(output_file)

    return merged_files
                    
        
def split_data_by_day(data_lines : list[str], header_lines : list[str], start_datetime: str):
    """Split UVP data lines by day."""
    split_data = defaultdict(lambda: header_lines.copy())
    start_datetime = datetime.strptime(start_datetime, '%Y%m%d-%H%M%S')

    for line in data_lines:
        # Extract the date and time from the line
        date_time_str = line.split(',', 1)[0]
        try:
            date_time = datetime.strptime(date_time_str, '%Y%m%d-%H%M%S')
        except ValueError:
            date_time = datetime.strptime(date_time_str, '%Y%m%d-%H%M%S-%f')

        # Check if aquisition is after start_datetime
        if date_time < start_datetime:
            continue

        date_str = line.split(",", 1)[0][:8]  # YYYYMMDD
        split_data[date_str].append(line)

    return dict(split_data)

def write_split_by_day_data(split_data : dict, data_dir : Path , logger: logging.Logger, overwrite : bool):
    """Create one merged data folder per day. Write the appropriate data file and copy associated vignettes in a subfolder named "1"."""

    merged_files = []
    
    for date_str, lines in split_data.items():
        datetime_str = date_str + "-000000"

        # Create daily folder
        merged_folder = data_dir / f"{datetime_str}_Merged"
        merged_folder.mkdir(parents=True, exist_ok=True)

        # Write daily file
        output_file = merged_folder / f"{datetime_str}_Merged_data.txt"
        if overwrite or not output_file.exists():
            with open(output_file, 'w') as file:
                for value in lines:
                    file.write(f'{value}\n')
            logger.info("Merged file created: %s", output_file.name)
        elif output_file.exists():
            logger.info("Merged file already existed, skipped: %s", output_file.name)

        merged_files.append(output_file)

    return merged_files

def build_vig_index(vig_paths: list[Path]):
    """
    Index vignettes by acquisition datetime (YYYYMMDD-HHMMSS).
    Example: 20250207-090016-2.vig -> key = 20250207-090016
    """
    index = defaultdict(list)
    for path in vig_paths:
        filename = path.name
        key = filename[:15]
        index[key].append(path)
    return index



def copy_vignettes_for_merged_file(merged_data_file: Path, vig_index: dict, logger: logging.Logger, overwrite: bool):
    """Copy vignettes corresponding to identifiers contained in one merged data file."""
    merged_data_file = Path(merged_data_file)
    output_vig_dir = merged_data_file.parent / "1"
    output_vig_dir.mkdir(parents=True, exist_ok=True)
    
    # list all datetimes
    datetime_list = []
    with open(merged_data_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(("HW", "ACQ")):
                continue
            datetime_list.append(line.split(",")[0][:15])

    vignettes = []
    for datetime_key in datetime_list:
        if datetime_key in vig_index:
            vignettes.extend(vig_index[datetime_key])

    if not vignettes:
        logger.warning("No vignette to copy for %s", merged_data_file.name)
        return

    copied = skipped = replaced = 0

    for vig in vignettes:
        dst_file = output_vig_dir / vig.name
        if dst_file.exists():
            if overwrite:
                shutil.copyfile(vig, dst_file)
                replaced += 1
            else:
                skipped += 1
        else:
            shutil.copyfile(vig, dst_file)
            copied += 1

    logger.info("Vignettes for %s: %d copied, %d skipped, %d replaced",
                merged_data_file.parent.name,
                copied,
                skipped,
                replaced)


def run(ctx,
        data_dirs: list[Path],
        by_day: bool = True,
        start_datetime: str = None,
        time_step: float = None):
    """Merge acquisitions by time step or by day, and copy corresponding vignettes."""

    logger = setup_logger("uvptoolbox.time_merge", debug=ctx.obj.get("debug", False))

    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting time-merge")
    logger.info("Processing %d acquisition setup folder(s)", len(data_dirs))
    logger.info("Overwrite existing outputs: %s", overwrite)
    if time_step :
        logger.info("Merging acquisitions by time step: %s hours", time_step)
    else:
        logger.info("Merging acquisitions by day.")
    if start_datetime:
        logger.info("Acquisitions before %s will not be considered.", start_datetime)
    
    for data_dir in data_dirs:
        logger.info("Processing folder: %s", data_dir)
        for acq_dir in data_dir.iterdir():
            rename_folder_and_files_UsedForMerge(acq_dir,logger=logger,overwrite=overwrite)
        data_files = sorted(data_dir.rglob("*_UsedForMerge_data.txt"))
        if not data_files:
            logger.warning("No data files found in %s, skipping.", data_dir)
            continue
        
        header_lines, data_lines = concatenate_data_files(data_files, logger=logger)
        if not header_lines or not data_lines:
            logger.warning("No mergeable data found in %s, skipping.", data_dir)
            continue

        current_start_datetime = start_datetime # don't modify start_datetime of other directories to be treated
        if current_start_datetime is None:
            current_start_datetime = get_min_datetime_from_data_lines(data_lines)


        if by_day:
            split_dict = split_data_by_day(data_lines, header_lines,current_start_datetime)
            merged_files = write_split_by_day_data(split_dict, data_dir, logger=logger,overwrite=overwrite)

        else:
            split_dict = split_data(header_lines, data_lines, time_step, current_start_datetime)
            merged_files = write_splitted_data(split_dict, data_dir, time_step, current_start_datetime, logger=logger,overwrite=overwrite)
        
        vig_list = list(data_dir.rglob("*.vig"))
        vig_index = build_vig_index(vig_list)

        for merged_file in merged_files:
            copy_vignettes_for_merged_file(merged_file,vig_index,logger=logger,overwrite=overwrite)

    logger.info("Finished time-merge")

