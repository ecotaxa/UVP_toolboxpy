from pathlib import Path
from uvptoolbox.utils import setup_logger, find_acquisition_folders, copy_acquisition_folder


def run(ctx, input_dir: Path, output_dir: Path):
    """Copy acquisition folders named YYYYMMDD-HHMMSS from an input directory to an output directory.
    Only new acquisitions are copied unless --overwrite is specified."""
    logger = setup_logger("uvptoolbox.load_new_data", debug=ctx.obj.get("debug", False))

    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting load-new-data")
    logger.info("Input directory: %s", input_dir)
    logger.info("Output directory: %s", output_dir)
    logger.info("Overwriting already present acquisition: %s", overwrite)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        logger.info("Output directory created: %s", output_dir)

    acquisition_folders = find_acquisition_folders(input_dir)

    if not acquisition_folders:
        logger.warning("No acquisition folders found in %s", input_dir)
        return

    logger.info("Found %d acquisition folders", len(acquisition_folders))

    counters = {"copied": 0, "skipped": 0, "replaced": 0}

    for folder in acquisition_folders:
        dest = output_dir / folder.name
        result = copy_acquisition_folder(folder, dest, logger=logger, overwrite=overwrite)
        counters[result] += 1

    logger.info(
        "Finished load-new-data: %d copied, %d skipped, %d replaced",
        counters["copied"],
        counters["skipped"],
        counters["replaced"],
    )
