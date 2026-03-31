import logging
from pathlib import Path
import re
import shutil


def setup_logger(logger_name: str, debug: bool = False) -> logging.Logger:
    """Create a simple console logger for the command."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger



#def get_dir_size(path: Path) -> int:
#   """Return total size in bytes of all files inside a directory."""
#    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


ACQUISITION_FOLDER_PATTERN = re.compile(r"^\d{8}-\d{6}$")

def find_acquisition_folders(source_root: Path) -> list[Path]:
    """Find all acquisition folders recursively in the source directory."""
    acquisition_folders =  [path for path in source_root.rglob("*") if (path.is_dir() and ACQUISITION_FOLDER_PATTERN.match(path.name))]
    return sorted(acquisition_folders)


def copy_acquisition_folder(src: Path, dest_root: Path, logger: logging.Logger, overwrite: bool = False ) -> str:
    """Copy one acquisition folder into dest_root. Returns: 'copied', 'skipped', or 'replaced' """
    dest = dest_root / src.name

    if dest.exists():

        if overwrite :
            shutil.rmtree(dest)
            shutil.copytree(src, dest)
            logger.info("Replaced acquisition: %s", dest.name)
            return "replaced"

        else:
            logger.debug("Skipped existing acquisition: %s", dest.name)
            return "skipped"

    shutil.copytree(src, dest)
    logger.info("Copied acquisition: %s", dest.name)
    return "copied"


def append_processed_acquisitions(processed_file: Path, acquisition_names: list[str]) -> None:
    """Append newly processed acquisition names to the processed acquisitions file."""
    processed_file.parent.mkdir(parents=True, exist_ok=True)

    with open(processed_file, "a") as f:
        for name in acquisition_names:
            f.write(f"{name}\n")