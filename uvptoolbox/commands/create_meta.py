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

CONSTANT_FIELDS = [
    "cruise",
    "ship",
    "bottomdepth",
    "ctdrosettefilename",
    "latitude",
    "longitude",
    "firstimage",
    "volimage",
    "aa",
    "exp",
    "dn",
    "winddir",
    "windspeed",
    "seastate",
    "nebuloussness",
    "comment",
    "yoyo",
    "stationid",
    "sampletype",
    "integrationtime",
    "argoid",
    "pixelsize",
    "constantdepth"
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
    HW_line =  [line for line in lines if  line.startswith("HW")][0]
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
        "firstimage":0,
        "volimage": HW_line.split(",")[22],
        "endimg": len(data_lines),
        "sampledatetime": first_datetime[0] + "-" + first_datetime[1],
    }

def merge_metadata(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Merge existing and new metadata rows, keeping one row per filename."""

    # Make sure all columns are present if the existing file is older/incomplete
    for col in META_COLUMNS:
        if col not in existing_df.columns:
            existing_df[col] = np.nan
    existing_df = existing_df[META_COLUMNS]

    df = pd.concat([existing_df, new_df], ignore_index=True)
    # Keep the newest version of a row if the same filename appears twice
    df = df.drop_duplicates(subset=["filename"], keep="last")
    # Restore expected column order when possible
    df = df[META_COLUMNS]
    # Sort rows for readability
    df = df.sort_values(by="sampledatetime")
    return df

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
    if config_dir and config_dir.exists():
        logger.info("Configuration data input directory: %s", config_dir)
    else:
        logger.warning("No configuration directory provided or found. Using only defaults and CLI values.")
    # Create output dir if necessary
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        logger.info("Output directory created: %s", output_dir)

    # Set up constant fields

    #  Default values
    constant_fields = {key: np.nan for key in CONSTANT_FIELDS}
    constant_fields["integrationtime"]= 3600
    constant_fields["sampletype"] = "T"


    # Search for constant fields values in config files
    if config_dir and config_dir.exists():

        # Search for constant fields values in cruise_info.txt
        cruise_info_file = config_dir / 'cruise_info.txt'
        if cruise_info_file.exists():
            logger.info("Using cruise info file: %s", cruise_info_file)
            cruise_infos = parse_key_value_file(cruise_info_file)
            # manual adjustments
            cruise_infos["cruise"] = cruise_infos.get("acron", "UNKNOWN")
            cruise_infos["stationid"] = cruise_infos.get("acron", "UNKNOWN")
            # add to constant_fields
            constant_fields.update({k: v for k, v in cruise_infos.items() if k in CONSTANT_FIELDS})
        else:
            logger.warning("No cruise_info.txt file found in %s", config_dir)

        # Search for constant fields values in HW_....txt file
        hw_config_file = next(config_dir.rglob("HW_*.txt"), None)
        if hw_config_file is not None:
            logger.info("Using HW config file: %s", hw_config_file)
            hw_config = parse_key_value_file(hw_config_file)
            # manual adjustments
            hw_config["aa"]= to_float_or_nan(hw_config.get("Aa")) / 1_000_000 if hw_config.get("Aa") else np.nan
            hw_config["exp"] = to_float_or_nan(hw_config.get("Exp")) if hw_config.get("Exp") else np.nan
            hw_config["pixelsize"] = to_float_or_nan(hw_config.get("Pixel_Size"))/ 1000 if hw_config.get("Pixel_Size") else np.nan
            # add to constant_fields
            constant_fields.update({k: v for k, v in hw_config.items() if k in CONSTANT_FIELDS})
        else:
            logger.warning("No HW config file found in %s", config_dir)

        # Search for constant fields values in meta_constants.txt, overwriting values found in hw_config_file and cruise_info_file
        meta_constants_file = next(config_dir.rglob("meta_constants.txt"), None)
        if meta_constants_file is not None:
            logger.info("Using meta_constants file: %s", meta_constants_file)
            meta_constants = parse_key_value_file(meta_constants_file)
            for k in meta_constants.keys():
                if k not in CONSTANT_FIELDS:
                    logger.warning("Unexpected meta constant %s found in %s, ignored", k, meta_constants_file)
            # add to constant_fields
            constant_fields.update({k: v for k, v in meta_constants.items() if k in CONSTANT_FIELDS})
        else:
            logger.warning("No meta_constants file found in %s", config_dir)

    # Search for constant fields values in cli and overwrite
    if latitude :
        constant_fields["latitude"] = latitude
    if longitude:
        constant_fields["longitude"] = longitude
    if constant_depth:
        constant_fields["constantdepth"] = constant_depth
    if station_id:
        constant_fields["stationid"] = station_id

    
    for data_dir in data_dirs:
        logger.info("Processing folder: %s", data_dir)
        output_name = f"{constant_fields.get('cruise')}_{data_dir.stem}_metadata.txt"
        output_file = output_dir / output_name

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
        df_new = pd.DataFrame(rows)
        df_new = df_new[META_COLUMNS] # sort columns
        df_new = df_new.sort_values(by="sampledatetime") # sort rows

        # If a metadata file already exists:
        # - with --overwrite: rebuild it entirely from current data
        # - without --overwrite: merge existing rows with newly generated rows

        if output_file.exists():
            if overwrite:
                df_final = df_new
                logger.info("Rebuilding metadata file from current data: %s", output_file)
            else:
                try:
                    df_existing = pd.read_csv(output_file, sep=";")
                except Exception as e:
                    raise click.ClickException(f"Unable to read existing metadata file: {output_file}") from e

                df_final = merge_metadata(df_existing, df_new)

                logger.info(
                    "Updated existing metadata file: %s (%d existing rows + %d new rows -> %d rows after removing duplicates)",
                    output_file,len(df_existing),len(df_new),len(df_final))
        else:
            df_final = df_new

        # Write output
        try:
            df_final.to_csv(output_file, sep=";", index=False, na_rep="nan")
            logger.info("Metadata file written: %s", output_file)
        except Exception as e:
            raise click.ClickException(f"Unable to write metadata file: {output_file}") from e


    logger.info("Finished create-meta")
