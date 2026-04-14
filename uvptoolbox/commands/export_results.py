from pathlib import Path
import click
from uvptoolbox.utils import setup_logger, copy_acquisition_folder

def append_processed_acquisitions(processed_file: Path, acquisition_names: set[str]) -> None:
    """Append newly processed acquisition names to the processed acquisitions file."""
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    with open(processed_file, "a") as f:
        for name in sorted(acquisition_names):
            f.write(f"{name}\n")


def run(ctx,
        input_dir: Path,
        output_dir: Path,
        processed_acquisitions_file: Path = None):
    """Export processed data (merged acquisition folders)."""

    logger = setup_logger("uvptoolbox.export_results", debug=ctx.obj.get("debug", False))

    # Make sure we have access to input data
    if not input_dir.exists():
        raise click.ClickException(f"Input directory does not exist: {input_dir}")
    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting export-results")
    logger.info("Input directory: %s", input_dir)
    logger.info("Output directory: %s", output_dir)
    logger.info("Overwrite existing outputs: %s", overwrite)

    merged_folders = [p for p in input_dir.rglob("*_Merged") if p.is_dir()]
    if not merged_folders:
        logger.warning("No merged acquisition data found in %s", input_dir)
        return 
    logger.info("Number of found merged acquisition folders: %d", len(merged_folders))

    counters = {"copied": 0, "skipped": 0, "replaced": 0}
    output_dir.mkdir(parents=True, exist_ok=True)

    for folder in merged_folders:
        relative_path = folder.relative_to(input_dir)
        dest = output_dir / relative_path
        result = copy_acquisition_folder(folder, dest, logger=logger, overwrite=overwrite)
        counters[result] += 1

    logger.info(
        "Exported %s merged data: %d copied, %d skipped, %d replaced",
        input_dir,
        counters["copied"],
        counters["skipped"],
        counters["replaced"])

    if processed_acquisitions_file:
        processed_acquisitions = {folder.name[:15] for folder in input_dir.rglob("*_UsedForMerge") if folder.is_dir() }
        append_processed_acquisitions(processed_acquisitions_file,processed_acquisitions)
        logger.info("Processed acquisitions file updated: %s (%d acquisition names added)",processed_acquisitions_file,len(processed_acquisitions))

    logger.info("Finished export-results")

