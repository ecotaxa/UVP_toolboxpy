import shutil
from pathlib import Path
import click
from concurrent.futures import ThreadPoolExecutor

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


def run(ctx, 
        input_dir : Path,
        output_dir : Path,
        reset_work_dir : bool =False,
        skip_some_acquisitions: bool = True,
        acquisitions_to_skip_file: Path = None):
    
    """Prepare work/all and copy selected acquisition folders into it."""

    logger = setup_logger("uvptoolbox.start_process", debug=ctx.obj.get("debug", False))

    # Make sure we have access to input data
    if not input_dir.exists():
        raise click.ClickException(f"Input directory does not exist: {input_dir}")

    # Store the name of acquisition to skip (because they have already been processed for example) if needed
    acq_to_skip = set()
    if skip_some_acquisitions :
        if acquisitions_to_skip_file is not None and acquisitions_to_skip_file.exists():
            acq_to_skip = read_acquisitions_to_skip(acquisitions_to_skip_file)
        else :
            logger.warning("File containing the names of acquisitions to skip not found: %s", acquisitions_to_skip_file)
            logger.warning("All acquisitions will be processed.")

    # work_dir = output_dir / "work"
    work_dir = output_dir / "raw"
    work_all_dir = work_dir / "all"
    overwrite = ctx.obj.get("overwrite", False)
    threads = ctx.obj.get("threads", 1)

    logger.info("Starting start-process")
    logger.info("Raw input directory: %s", input_dir)
    logger.info("Output directory: %s", output_dir)
    logger.info("Work directory: %s", work_dir)
    logger.info("Reset work directory: %s", reset_work_dir)
    if not reset_work_dir:
        logger.info("Overwriting already present acquisitions: %s", overwrite)
    if acq_to_skip :
        logger.info("Skipping acquisitions: %s", ", ".join(sorted(acq_to_skip)))
    if threads > 1:
        logger.info("Parallel threads: %d", threads)

    # Create or clean work and work/all directories if needed
    if reset_work_dir:
        empty_folder(work_dir)
        logger.info("Emptied work directory: %s", work_dir)
    else :
        work_dir.mkdir(parents=True, exist_ok=True)
    work_all_dir.mkdir(parents=True, exist_ok=True)

    acquisition_folders = find_acquisition_folders(input_dir)
    if not acquisition_folders:
        logger.warning("No acquisition folders found in %s", input_dir)
        return
    if acq_to_skip:
        acquisition_folders = [folder for folder in acquisition_folders if folder.name not in acq_to_skip]
    if not acquisition_folders:
        logger.info("No new acquisition folders to process.")
        return
    else:
        logger.info("Found %d acquisition folders to process", len(acquisition_folders))

    counters = {"copied": 0, "skipped": 0, "replaced": 0}
    with ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(lambda folder: copy_acquisition_folder(folder, work_all_dir / folder.name, logger=logger,
                                                                      overwrite=overwrite), acquisition_folders)
        for result in results:
            counters[result] += 1

    logger.info(
        "Acquisitions import completed: %d copied, %d skipped, %d replaced",
        counters["copied"],
        counters["skipped"],
        counters["replaced"],
    )

    logger.info("Finished start-process")

