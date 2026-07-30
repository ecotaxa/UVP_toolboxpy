import logging
from pathlib import Path
import click
from concurrent.futures import ThreadPoolExecutor
from uvptoolbox.utils import setup_logger, copy_acquisition_folder
# from uvptoolbox.utils import setup_logger, copy_acquisition_folder_to_processed


def append_processed_acquisitions(processed_file: Path, acquisition_names: set[str]) -> None:
    """Append newly processed acquisition names to the processed acquisitions file."""
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    with open(processed_file, "a") as f:
        for name in sorted(acquisition_names):
            f.write(f"{name}\n")


def rename_data_file_to_match_folder(dest: Path, logger: logging.Logger) -> None:
    """Rename the *_data.txt file directly under dest so its name matches dest's folder name."""
    data_files = [f for f in dest.iterdir() if f.is_file() and f.name.endswith("_data.txt")]
    if not data_files:
        logger.warning("No _data.txt file found to rename in %s", dest)
        return
    if len(data_files) > 1:
        logger.warning("Multiple _data.txt files found in %s, renaming only: %s", dest, data_files[0].name)

    new_path = dest / f"{dest.name}_data.txt"
    if data_files[0] != new_path:
        data_files[0].rename(new_path)
        logger.debug("Renamed %s -> %s", data_files[0].name, new_path.name)


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
    threads = ctx.obj.get("threads", 1)

    logger.info("Starting export-results")
    logger.info("Input directory: %s", input_dir)
    logger.info("Output directory: %s", output_dir)
    logger.info("Overwrite existing outputs: %s", overwrite)
    if threads > 1:
        logger.info("Parallel threads: %d", threads)

    export_folders = [p for p in input_dir.rglob("*") if p.is_dir() and ("_Merged" in p.name or p.name.endswith("_UsedForMerge"))]

    if not export_folders:
        logger.warning("No merged or UsedForMerge acquisition folders found in %s", input_dir)
        return 
    logger.info("Number of folders to export: %d", len(export_folders))

    output_dir.mkdir(parents=True, exist_ok=True)

    counters = {"copied": 0, "skipped": 0, "replaced": 0}

    def dest_path_for(folder: Path) -> Path:
        # folder.relative_to(input_dir) is e.g. "OBSEA_Off/20250817-000000_Merged-019"
        rel = folder.relative_to(input_dir)
        site_name = rel.parent.name          # "OBSEA_Off"
        acquisition_name = folder.name        # "20250817-000000_Merged-019"
        return output_dir / f"{acquisition_name}_{site_name}"

    def export_one_folder(folder: Path) -> str:
        dest = dest_path_for(folder)
        result = copy_acquisition_folder(folder, dest, logger=logger, overwrite=overwrite)
        if result in ("copied", "replaced"):
            rename_data_file_to_match_folder(dest, logger)
        return result

    with ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(export_one_folder, export_folders)
        for result in results:
            counters[result] += 1

    # # copied directly to processed/ and file name == file_name_acquisition_name (ie file_name_folder.relative_to(input_dir))
    # with ThreadPoolExecutor(max_workers=threads) as executor:
    #     results = executor.map(
    #                 lambda folder: copy_acquisition_folder_to_processed(
    #                     folder,
    #                     output_dir,
    #                     acquisition_name=folder.name,  # or folder.name[:15] if that's the true acquisition id
    #                     logger=logger,
    #                     overwrite=overwrite,
    #                 ),
    #                 export_folders,
    #             )
        
    #     for result in results:
    #         counters[result] += 1


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

