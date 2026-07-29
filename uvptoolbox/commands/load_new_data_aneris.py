from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import shutil
import zipfile

from uvptoolbox.utils import setup_logger, find_acquisition_folders, copy_acquisition_folder


def safe_extract_zip(zip_path: Path, extract_dir: Path):
    """Extract zip safely, avoiding path traversal."""
    extract_dir = extract_dir.resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = (extract_dir / member.filename).resolve()
            if not str(target).startswith(str(extract_dir)):
                raise RuntimeError(f"Unsafe path in zip: {member.filename}")

        zf.extractall(extract_dir)


def copy_found_acquisitions(acquisition_folders, output_dir, logger, overwrite, threads):
    counters = {"copied": 0, "skipped": 0, "replaced": 0}

    with ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(
            lambda folder: copy_acquisition_folder(
                folder,
                output_dir / folder.name,
                logger=logger,
                overwrite=overwrite
            ),
            acquisition_folders
        )

        for result in results:
            counters[result] += 1

    return counters


def add_counters(total, new):
    for key in total:
        total[key] += new.get(key, 0)


def run(ctx, input_dir: Path, output_dir: Path):
    """Copy acquisition folders named YYYYMMDD-HHMMSS from input directory and ZIP files."""

    logger = setup_logger("uvptoolbox.load_new_data", debug=ctx.obj.get("debug", False))

    overwrite = ctx.obj.get("overwrite", False)
    threads = ctx.obj.get("threads", 1)

    logger.info("Starting load-new-data")
    logger.info("Input directory: %s", input_dir)
    logger.info("Output directory: %s", output_dir)
    logger.info("Overwriting already present acquisition: %s", overwrite)

    if threads > 1:
        logger.info("Parallel threads: %d", threads)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    total_counters = {"copied": 0, "skipped": 0, "replaced": 0}

    # 1. Copy acquisition folders already present unzipped
    logger.info("Searching acquisition folders in input directory tree...")
    acquisition_folders = find_acquisition_folders(input_dir)
    logger.info("Finished searching acquisition folders: %d found", len(acquisition_folders))


    if acquisition_folders:
        logger.info("Found %d acquisition folders directly in input directory", len(acquisition_folders))

        counters = copy_found_acquisitions(
            acquisition_folders,
            output_dir,
            logger,
            overwrite,
            threads
        )

        add_counters(total_counters, counters)
    else:
        logger.info("No direct acquisition folders found in %s", input_dir)

    # 2. Process ZIP files one by one
    logger.info("Searching ZIP files in input directory tree...")

    zip_files = sorted(input_dir.rglob("*.zip"))

    logger.info("Found %d zip files", len(zip_files))

    if not zip_files:
        logger.info("No ZIP files found in %s", input_dir)
    else:
        logger.info("Found %d ZIP files", len(zip_files))

    for zip_path in zip_files:
        logger.info("Processing ZIP: %s", zip_path)

        with tempfile.TemporaryDirectory(prefix="uvp_unzip_") as tmp:
            tmp_dir = Path(tmp)

            try:
                safe_extract_zip(zip_path, tmp_dir)
            except zipfile.BadZipFile:
                logger.warning("Bad ZIP file, skipping: %s", zip_path)
                continue
            except Exception as e:
                logger.warning("Could not extract ZIP %s: %s", zip_path, e)
                continue

            zip_acquisition_folders = find_acquisition_folders(tmp_dir)

            if not zip_acquisition_folders:
                logger.info("No acquisition folders found in ZIP: %s", zip_path)
                continue

            logger.info(
                "Found %d acquisition folders in ZIP: %s",
                len(zip_acquisition_folders),
                zip_path
            )

            counters = copy_found_acquisitions(
                zip_acquisition_folders,
                output_dir,
                logger,
                overwrite,
                threads
            )

            add_counters(total_counters, counters)

        logger.info("Temporary extraction removed for ZIP: %s", zip_path)

    logger.info(
        "Finished load-new-data: %d copied, %d skipped, %d replaced",
        total_counters["copied"],
        total_counters["skipped"],
        total_counters["replaced"],
    )