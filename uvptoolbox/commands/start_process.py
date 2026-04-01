import shutil
from pathlib import Path
from uvptoolbox.utils import setup_logger, find_acquisition_folders, copy_acquisition_folder

def empty_folder(folder_path: Path):
    """ Empty a folder of the project or create it if it doesn't exist """

    # Create the folder if it does not already exist
    folder_path.mkdir(parents=True, exist_ok=True)

    # Empty content (not the folder)
    for item in folder_path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def read_acquisitions_to_skip(file: Path) -> set[str]:
    """Read the set of acquisition folder names to not process."""
    if not file.exists():
        return set()

    with open(file, "r") as f:
        return {line.strip() for line in f if line.strip()}


def run(ctx, project_folder: Path,
        input_folder : Path = None,
        reset_work_dir : bool =False,
        skip_some_acquisitions: bool = True,
        acquisitions_to_skip_file: Path = None):
    
    """Prepare work/all and copy selected acquisition folders into it."""
    logger = setup_logger("uvptoolbox.start_process", debug=ctx.obj.get("debug", False))
    
    # Check that we have access to the raw input data
    if input_folder is None:
        input_folder = project_folder / "raw"
    if not input_folder.exists():
        logger.error("Raw input directory does not exist: %s", input_folder)
        raise FileNotFoundError(f"Raw input directory does not exist: {input_folder}")

    # Store the name of acquisition to skip (because they have already been processed for example) if needed
    acq_to_skip = set()
    if skip_some_acquisitions :
        if acquisitions_to_skip_file is None:
            acquisitions_to_skip_file = project_folder / "logs/processed_acquisitions.txt"
        if acquisitions_to_skip_file.exists():
            acq_to_skip = read_acquisitions_to_skip(acquisitions_to_skip_file)
        else :
            logger.warning("File containing the names of acquisitions to skip not found: %s", acquisitions_to_skip_file)
            logger.warning("All acquisitions will be processed")

    work_dir = project_folder / "work"
    work_all_dir = work_dir / "all"
    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting start-process")
    logger.info("Project directory: %s", project_folder)
    logger.info("Raw input directory: %s", input_folder)
    logger.info("Work directory: %s", work_dir)
    logger.info("Work directory reset: %s", reset_work_dir)
    if not reset_work_dir:
        logger.info("Overwriting already present acquisition: %s", overwrite)
    if acq_to_skip :
        logger.info("Skipping acquisitions: %s", ", ".join(acq_to_skip))

    if reset_work_dir:
        empty_folder(work_dir)
        logger.info("Emptied work directory: %s", work_dir)
    else :
        work_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Prepared work directory: %s", work_dir)


    work_all_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Prepared work/all directory: %s", work_all_dir)

    acquisition_folders = find_acquisition_folders(input_folder)
    if not acquisition_folders:
        logger.warning("No acquisition folders found in %s", input_folder)
        return
    if acq_to_skip:
        acquisition_folders = [folder for folder in acquisition_folders if folder.name not in acq_to_skip]
    if not acquisition_folders:
        logger.info("No new acquisition folders to process")
        return

    logger.info("Found %d acquisition folders to process", len(acquisition_folders))

    counters = {"copied": 0, "skipped": 0, "replaced": 0}

    for folder in acquisition_folders:
        dest = work_all_dir / folder.name
        result = copy_acquisition_folder(folder, dest, logger=logger, overwrite=overwrite)
        counters[result] += 1

    logger.info(
        "Acquisitions import completed: %d copied, %d skipped, %d replaced",
        counters["copied"],
        counters["skipped"],
        counters["replaced"],
    )

    logger.info("Finished start-process")


    
    
        

