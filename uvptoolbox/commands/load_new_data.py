import re
import shutil
import logging
from pathlib import Path


ACQUISITION_FOLDER_PATTERN = re.compile(r"^\d{8}-\d{6}$")


def setup_logger(debug: bool = False) -> logging.Logger:
    """Create a simple console logger for the command."""
    logger = logging.getLogger("uvptoolbox.load_new_data")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger



def find_acquisition_folders(source_root: Path) -> list[Path]:
    """Find all acquisition folders recursively in the source directory."""
    acquisition_folders =  [path for path in source_root.rglob("*") if (path.is_dir() and ACQUISITION_FOLDER_PATTERN.match(path.name))]
    return sorted(acquisition_folders)


def get_dir_size(path: Path) -> int:
    """Return total size in bytes of all files inside a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

def copy_acquisition_folder(src: Path, dest_root: Path, logger: logging.Logger) -> str:
    """Copy one acquisition folder into dest_root. Returns: 'copied', 'skipped', or 'replaced' """
    # TODO: verifier la logique
    # même taille → skip
    # destination plus grosse → skip
    # destination plus petite → replace

    dest = dest_root / src.name

    if dest.exists():
        src_size = get_dir_size(src)
        dest_size = get_dir_size(dest)

        if src_size == dest_size:
            logger.debug("Skipped existing acquisition: %s", dest.name)
            return "skipped"

        elif dest_size > src_size:
            logger.warning("Destination already exists with a bigger size than source: skipped acquisition %s", dest.name)
            return "skipped"

        else:
            logger.warning("Destination already exists but with a smaller size, replacing: %s", dest.name)
            shutil.rmtree(dest)
            shutil.copytree(src, dest)
            logger.warning("Re-copied acquisition: %s", dest.name)
            return "replaced"

    shutil.copytree(src, dest)
    logger.info("Copied acquisition: %s", dest.name)
    return "copied"


def run(ctx, project: Path, source_folder: Path):
    """Copy new UVP acquisition folders from a source directory into project/raw."""
    logger = setup_logger(debug=ctx.obj.get("debug", False))

    raw_dir = project / "raw"

    logger.info("Starting load-new-data")
    logger.info("Project directory: %s", project)
    logger.info("Source directory: %s", source_folder)

    raw_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Raw directory: %s", raw_dir)

    acquisition_folders = find_acquisition_folders(source_folder)

    if not acquisition_folders:
        logger.warning("No acquisition folders found in %s", source_folder)
        return

    logger.info("Found %d acquisition folders", len(acquisition_folders))

    counters = {"copied": 0, "skipped": 0, "replaced": 0}

    for folder in acquisition_folders:
        result = copy_acquisition_folder(folder, raw_dir, logger)
        counters[result] += 1

    logger.info(
        "Finished load-new-data: %d copied, %d skipped, %d replaced",
        counters["copied"],
        counters["skipped"],
        counters["replaced"],
    )
