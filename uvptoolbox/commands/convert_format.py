# The new file is copied in the same folder of the original file.
# Change the metaline format of some data.txt from 2023 to fit the 2021 format.
# Save and archive the data.txt to [...]_2023format.txt
# Read the data text file from uvp6
# Change the hwconf line and the acq line :
# add parameters to fit the old format
# The new file is copied in the same folder of the original file.
#
# uvp6 version = 2024.00
#
# Work for all data.txt in the provided folder
#
# WARNING : does not work with taxo


from pathlib import Path
import shutil 
import re
import click
from uvptoolbox.utils import setup_logger



def convert_hw_line(hw_line: str, logger) -> str:
    """
    Convert a UVP6 HW line from 2023 format to the 2021 format expected by downstream tools.
    The function modifies specific fields by inserting required values at fixed positions in the comma-separated line.
    If the line does not match the expected format, return None.
    """
    parts = hw_line.split(",")
    if len(parts) != 43:
        logger.warning("Unexpected number of elements in HW line, skipping line conversion: %s", hw_line)
        return None
    parts = parts[:7] + ["0"] + parts[7:13] + ["193.49.112.100"] + parts[13:]
    return ",".join(parts)


def convert_acq_line(acq_line: str, logger) -> str:
    """
    Convert a UVP6 ACQ line from 2023 format to the 2021 format expected by downstream tools.
    The function modifies specific fields by inserting required values at fixed positions in the comma-separated line.
    If the line does not match the expected format, return None.
    """
    parts = acq_line.split(",")
    if len(parts) != 23:
        logger.warning("Unexpected number of elements in ACQ line, skipping line conversion: %s", acq_line)
        return None
    parts = parts[:5] + ["1"] + parts[5:9] + ["10"] + parts[9:16] + ["0"] + parts[16:-5] + parts[-2:]
    return ",".join(parts)


def standardize_uvp_data_format(file_path: Path, logger):
    """
    Standardize a UVP6 data.txt file by converting its header format from the 2023 version to a 2021 format.
    The function:
        - identifies HW and ACQ lines in the file
        - converts them using dedicated helper functions
        - inserts an empty line after each of these lines (format requirement)
        - saves the original file as *_2023format.txt
        - writes the converted file under the original name
    """
    try:
        with open(file_path, "r") as f:
            lines = f.read().splitlines()

        hw_line = acq_line = None
        data_lines = list()
        for line in lines:
            if re.search(r'^HW', line, re.IGNORECASE):
                hw_line = convert_hw_line(line, logger)
            elif re.search(r'^ACQ', line, re.IGNORECASE):
                acq_line = convert_acq_line(line, logger)
            elif line != "":
                data_lines.append(line)

        if hw_line is None or acq_line is None:
            logger.warning("HW or ACQ lines not found or with unexpected format, skipping: %s", file_path)
            return None

        old_file_path = file_path.with_name(file_path.stem + "_2023format.txt")
        shutil.move(file_path, old_file_path)

        with open(file_path, "w") as f:
            f.write(hw_line + "\n")
            f.write("\n")
            f.write(acq_line + "\n")
            f.write("\n")
            f.write("\n".join(data_lines) + "\n")

        logger.debug("Converted: %s", file_path.name)
    except Exception as e:
        logger.error("Error processing %s: %s", file_path, e)


def run(ctx, data_dir: Path):
    """Convert UVP data.txt files from 2023 format to the 2021 format expected downstream. Conversion is done in place."""
    logger = setup_logger("uvptoolbox.convert_format", debug=ctx.obj.get("debug", False))
    
    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting convert-format")
    logger.info("Working on files in: %s", data_dir)
    logger.info("Overwriting (re-converting already converted files from archives when possible): %s", overwrite)

    # Check that we have access to the data
    if not data_dir.exists():
        raise click.ClickException(f"Provided directory does not exist: {data_dir}")

    counters = {"converted": 0, "skipped": 0, "reconverted": 0}

    data_files = list(data_dir.rglob("*_data.txt"))

    if not data_files:
        logger.warning("No acquisition data files found in %s", data_dir)
        return

    for file_path in data_files:
        archived_file = file_path.with_name(file_path.stem + "_2023format.txt")
        if not archived_file.exists(): 
            standardize_uvp_data_format(file_path, logger=logger)
            counters["converted"] += 1
        elif overwrite:
            logger.info("Re-converting from archived original: %s", archived_file.name)
            shutil.copyfile(archived_file, file_path)
            standardize_uvp_data_format(file_path, logger=logger)
            counters["reconverted"] += 1
        else:
            logger.debug("Skipping already converted file: %s", file_path.name)
            counters["skipped"] += 1

    logger.info(
        "Finished convert-format: %d converted, %d skipped, %d re-converted",
        counters["converted"],
        counters["skipped"],
        counters["reconverted"],
    )


