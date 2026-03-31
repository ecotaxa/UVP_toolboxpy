from pathlib import Path
from uvptoolbox.utils import setup_logger, find_acquisition_folders, copy_acquisition_folder


def run(ctx, project: Path, source_folder: Path):
    """Copy new UVP acquisition folders from a source directory into project/raw."""
    logger = setup_logger("uvptoolbox.load_new_data", debug=ctx.obj.get("debug", False))

    raw_dir = project / "raw"
    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting load-new-data")
    logger.info("Project directory: %s", project)
    logger.info("Source directory: %s", source_folder)
    logger.info("Overwriting already present acquisition: %s", overwrite)

    raw_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Raw directory: %s", raw_dir)

    acquisition_folders = find_acquisition_folders(source_folder)

    if not acquisition_folders:
        logger.warning("No acquisition folders found in %s", source_folder)
        return

    logger.info("Found %d acquisition folders", len(acquisition_folders))

    counters = {"copied": 0, "skipped": 0, "replaced": 0}

    for folder in acquisition_folders:
        result = copy_acquisition_folder(folder, raw_dir, logger=logger, overwrite=overwrite)
        counters[result] += 1

    logger.info(
        "Finished load-new-data: %d copied, %d skipped, %d replaced",
        counters["copied"],
        counters["skipped"],
        counters["replaced"],
    )
