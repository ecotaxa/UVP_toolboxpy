import logging
import numpy as np
import pandas as pd
from pathlib import Path
import click
import re
from uvptoolbox.utils import setup_logger


META_COLUMNS = [
    'cruise',
    'ship',
    'filename',
    'profileid',
    'bottomdepth',
    'ctdrosettefilename',
    'latitude',
    'longitude',
    'firstimage',
    'volimage',
    'aa',
    'exp',
    'dn',
    'winddir',
    'windspeed',
    'seastate',
    'nebuloussness',
    'comment',
    'endimg',
    'yoyo',
    'stationid',
    'sampletype',
    'integrationtime',
    'argoid',
    'pixelsize',
    'sampledatetime',
    'constantdepth'
]


def parse_key_value_file(file_path: Path, comment_prefixes: tuple[str, ...] = ("#", "//")) -> dict[str, str]:
    """
    Parse a text file containing lines of the form key=value.
    Ignore empty lines, section headers like [General], and comment lines.
    """
    values = {}

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith(comment_prefixes) or (line.startswith("[") and line.endswith("]")) or  "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    return values

def to_float_or_nan(value):
    if value is None or value == "":
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan

def extract_variable_meta_from_merged_file(merged_file: Path, cruise_value: str, logger: logging.Logger) -> dict:
    """Extract metadata fields that depend on one merged data file."""
    file_stem = merged_file.stem

    matches = re.findall(r"\d{8}-\d{6}", file_stem)
    if not matches:
        raise click.ClickException(f"No datetime found in merged file name: {merged_file}")

    profileid = f"{cruise_value}_{matches[-1][:8]}"

    with open(merged_file, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    data_lines = [line for line in lines if not line.startswith(("HW", "ACQ"))]
    if not data_lines:
        # If no acquisition lines are found, keep processing the file with:
        # - endimg = 0
        # - sampledatetime inferred from the merged file name
        logger.warning("No acquisition data found in merged file: %s", merged_file)
        first_datetime = matches[-1].split("-")
    else:
        first_datetime = data_lines[0].split(",")[0].strip().split("-")

    return {
        "filename": file_stem.removesuffix("_data"),
        "profileid": profileid,
        "endimg": len(data_lines),
        "sampledatetime": first_datetime[0] + "-" + first_datetime[1],
    }

def run(ctx,
        data_dirs: list[Path],
        config_dir: Path,
        output_dir: Path,
        latitude: str = None,
        longitude: str = None,
        constant_depth: str = None,
        station_id: str = None):
    """Create metadata file(s) from merged UVP data files and project configuration files."""

    logger = setup_logger("uvptoolbox.create_meta", debug=ctx.obj.get("debug", False))

    overwrite = ctx.obj.get("overwrite", False)
    
    logger.info("Starting create-meta")
    logger.info("Processing %d data folder(s)", len(data_dirs))
    logger.info("Overwrite existing outputs: %s", overwrite)
    logger.info("Configuration data input directory: %s", config_dir)
    # Create output dir if necessary
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        logger.info("Output directory created: %s", output_dir)
    
    # Search for constant fields values in config files
    raw_config_info = {}

    # in cruise_info.txt
    cruise_info_file = config_dir / 'cruise_info.txt'
    if cruise_info_file.exists():
        logger.info("Using cruise info file: %s", cruise_info_file)
        raw_config_info.update(parse_key_value_file(cruise_info_file))
    else:
        logger.warning("No cruise_info.txt file found in %s", config_dir)

    # in HW_....txt file
    hw_config_file = next(config_dir.rglob("HW_*.txt"), None)
    if hw_config_file is not None:
        logger.info("Using HW config file: %s", hw_config_file)
        raw_config_info.update(parse_key_value_file(hw_config_file))
    else:
        logger.warning("No HW config file found in %s", config_dir)

    constant_fields = {
        "cruise": raw_config_info.get("acron", "UNKNOWN"),
        "ship": "mooring",
        "bottomdepth": np.nan,
        "ctdrosettefilename": np.nan,
        "latitude": to_float_or_nan(latitude),
        "longitude": to_float_or_nan(longitude),
        "firstimage": 0,
        "volimage": to_float_or_nan(raw_config_info.get("Image_volume")),
        "aa": to_float_or_nan(raw_config_info.get("Aa")) / 1_000_000,
        "exp": to_float_or_nan(raw_config_info.get("Exp")),
        "dn": np.nan,
        "winddir": np.nan,
        "windspeed": np.nan,
        "seastate": np.nan,
        "nebuloussness": np.nan,
        "comment": np.nan,
        "yoyo": np.nan,
        "stationid": station_id if station_id else raw_config_info.get("acron", "UNKNOWN"),
        "sampletype": "T",
        "integrationtime": 3600,  # WHY ? 
        "argoid": np.nan,
        "pixelsize": to_float_or_nan(raw_config_info.get("Pixel_Size")) / 1000,
        "constantdepth": to_float_or_nan(constant_depth)
    }
    
    
    for data_dir in data_dirs:
        logger.info("Processing folder: %s", data_dir)
        output_name = f"{raw_config_info.get('acron', 'UNKNOWN')}_{data_dir.stem}_metadata.txt"
        output_file = output_dir / output_name

        # Check that we have to create a metadata file
        if output_file.exists() and not overwrite:
            logger.info("Output file already exists, skipped: %s", output_file)
            continue

        # Make sure we have access to input data
        if not data_dir.exists():
            raise click.ClickException(f"Data directory does not exist: {data_dir}")

        # Create one row for each merged file
        merged_files = sorted(data_dir.rglob("*Merged*_data.txt"))
        if not merged_files:
            logger.warning("No merged acquisition files found in %s", data_dir)
            continue
        logger.info("Number of found merged acquisition files: %d", len(merged_files))

        rows = []
        for merged_file in merged_files:
            # Get metadata fields that depend on one merged data file
            variable_fields = extract_variable_meta_from_merged_file(merged_file, cruise_value=constant_fields.get("cruise"), logger= logger)
            # Create a row with both constant and variable fields
            row = {**constant_fields,  **variable_fields}
            rows.append(row)

        # Convert to Dataframe
        df = pd.DataFrame(rows)
        df = df[META_COLUMNS] # sort columns
        df = df.sort_values(by="sampledatetime") # sort rows

        # Write output
        try:
            df.to_csv(output_file, sep=";", index=False, na_rep="nan")
            logger.info("Metadata file written: %s", output_file)
        except Exception as e:
            raise click.ClickException(f"Unable to write metadata file: {output_file}") from e

    logger.info("Finished create-meta")