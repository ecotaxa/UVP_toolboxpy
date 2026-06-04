import logging
from pathlib import Path
import re
import shutil

ACQUISITION_FOLDER_PATTERN = re.compile(r"^\d{8}-\d{6}$")


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


def find_acquisition_folders(source_root: Path) -> list[Path]:
    """Find all acquisition folders recursively in the source directory."""
    acquisition_folders =  [path for path in source_root.rglob("*") if (path.is_dir() and ACQUISITION_FOLDER_PATTERN.match(path.name))]
    return sorted(acquisition_folders)


# def copy_acquisition_folder(src: Path, dest: Path, logger: logging.Logger, overwrite: bool = False ) -> str:
#     """Copy one acquisition folder src to dest. Returns: 'copied', 'skipped', or 'replaced' """

#     if dest.exists():

#         if overwrite :
#             shutil.rmtree(dest)
#             shutil.copytree(src, dest,
#             copy_function=shutil.copyfile,
#             ignore_dangling_symlinks=True
#         )
#             logger.debug("Replaced acquisition: %s", dest.name)
#             return "replaced"

#         else:
#             logger.debug("Skipped existing acquisition: %s", dest.name)
#             return "skipped"

#     shutil.copytree(src, dest,
#             copy_function=shutil.copyfile,
#             ignore_dangling_symlinks=True
#         )
#     logger.debug("Copied acquisition: %s", dest.name)
#     return "copied"

def copytree_content_only(src: Path, dest: Path):
    src = Path(src)
    dest = Path(dest)

    dest.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        target = dest / item.name

        if item.is_dir():
            copytree_content_only(item, target)

        elif item.is_file():
            shutil.copyfile(item, target)


def copy_acquisition_folder(src, dest, logger, overwrite=False):
    src = Path(src)
    dest = Path(dest)

    if dest.exists():
        if overwrite:
            shutil.rmtree(dest)
            copytree_content_only(src, dest)
            logger.debug("Replaced acquisition: %s", dest.name)
            return "replaced"

        logger.debug("Skipped existing acquisition: %s", dest.name)
        return "skipped"

    copytree_content_only(src, dest)
    logger.debug("Copied acquisition: %s", dest.name)
    return "copied"


def append_processed_acquisitions(processed_file: Path, acquisition_names: list[str]) -> None:
    """Append newly processed acquisition names to the processed acquisitions file."""
    processed_file.parent.mkdir(parents=True, exist_ok=True)

    with open(processed_file, "a") as f:
        for name in acquisition_names:
            f.write(f"{name}\n")