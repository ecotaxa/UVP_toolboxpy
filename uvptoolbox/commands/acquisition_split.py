import logging
from collections import defaultdict
from pathlib import Path
import pandas as pd
import click
from concurrent.futures import ThreadPoolExecutor
from uvptoolbox.utils import setup_logger, copy_acquisition_folder



def extract_acquisition_parameters(data_files : list[Path], logger : logging.Logger) -> pd.DataFrame:
    """Extract the acquisition parameters in a list of uvp6 data files and returns a dataframe with all the parameters as different columns. 
     Add a 'datetime' column with the acquisition date."""
    acq_header = ["rame", "configuration_name", "pt_mode", "acquisition_frequency", "frames_per_bloc", "blocs_per_pt",
                  "pressure_for_auto_start", "pressure_difference_for_auto_stop",
                  "result_sending", "save_synthetic_data_for_delayed_request", "limit_lpm_detection_size",
                  "save_images", "vignetting_lower_limit_size", "appendices_ratio",
                  "interval_for_measuring_background_noise", "image_nb_for_smoothing", "analog_output_activation",
                  "gain_for_analog_out", "minimum_object_number",
                  "maximal_internal_temperature", "operator_email", "0", "sd_card_mem"]

    rows = []
    for data_file in data_files:
        # Found the acquisition parameter line
        with open(data_file, "r") as f:
            acq_line = next((line for line in f if line.startswith("ACQ")), None)
        if acq_line is None:
            logger.warning("No ACQ line found, skipping: %s", data_file)
            continue

        acq_values = acq_line.strip().split(",")

        # Check that we have all expected acquisition parameters and convert to dict
        if len(acq_values) != len(acq_header):
            logger.warning("Unexpected number of ACQ fields, skipping: %s", data_file)
            continue
        row = dict(zip(acq_header, acq_values))

        # Get date and time from the acquisition file name
        row["datetime"]  = data_file.stem.split("_")[0]

        rows.append(row)

    return pd.DataFrame(rows)



def detect_unique_acquisition_configs(acq_df : pd.DataFrame, logger : logging.Logger) :
    """Get the unique acquisition parameters from a dataframe of acquisition parameters."""
    non_unique_columns = [col for col in acq_df.columns
                          if col not in ["sd_card_mem",
                                         "datetime"]  # Remove date and memory and file_path, because they are not supposed to be constant
                          and acq_df[col].nunique() > 1  # Only keep columns with more than one value
                          ]
    if non_unique_columns:
        unique_configs = acq_df[non_unique_columns].drop_duplicates().copy()
        unique_configs["folder_name"] = unique_configs.apply(
            lambda row: "__".join(
                f"{col.replace(' ', '').replace('_', '')}_{str(val).replace('ACQ_', '').replace('.', 'p').replace(' ', '').replace('_', '')}"
                for col, val in row.items()
            ), axis=1
        )
        return unique_configs
    else:
        logger.info("Only one acquisition configuration detected.")
        return None


def get_provided_acquisition_configs_folders(acq_df : pd.DataFrame, config_file : Path, logger : logging.Logger) -> pd.DataFrame:
    """Assign acquisition folders using a user-provided configuration file."""

    # Read provided config file and check that its has a 'folder_name' column
    try:
        provided_configs = pd.read_csv(config_file, dtype=str)
    except Exception:
        raise click.ClickException(f"Unable to read provided acquisition configurations file, please check its format: {config_file}")
    if "folder_name" not in provided_configs.columns:
        raise click.UsageError("Config file must contain a 'folder_name' column.")

    # Check that all different acquisitions configurations are included in the config file, else notify the user
    unique_configs = detect_unique_acquisition_configs(acq_df, logger)
    if unique_configs is not None:
        unsplit_param = unique_configs.columns.difference(provided_configs.columns)
        if len(unsplit_param) > 0:
            logger.warning("Some varying acquisition parameters are not specified in the config file. "
                           "Different acquisitions may be merged together:\n%s",
                           "\n".join([f"{param} with values: " + ", ".join(unique_configs[param].dropna().astype(str).unique()) for param in unsplit_param]))

    # Assign each acquisition to a folder based on its acquisition config
    match_columns = [col for col in provided_configs.columns if col != "folder_name"]
    merged = acq_df.merge(provided_configs, on=match_columns, how="left")

    # Check that all acquisition are affected to a folder
    if merged["folder_name"].isna().any():
        missing = merged.loc[merged["folder_name"].isna(), match_columns].drop_duplicates()
        logger.error("Detected some acquisition configurations not found in: %s", config_file)
        raise click.ClickException(
            "Unexpected acquisition configuration detected.\n\n"
            f"Config file: {config_file}\n\n"
            "Missing configuration(s):\n"
            f"{missing.to_string(index=False)}\n\n"
            "Stopping process."
        )

    return merged



def copy_acquisitions_to_config_folders(acq_df: pd.DataFrame, input_dir : Path, logger : logging.Logger, overwrite : bool, threads: int = 1) -> dict:
    """Copy each acquisition folder into its corresponding acquisition configuration folder."""
    counters = defaultdict(lambda: {"copied": 0, "skipped": 0, "replaced": 0})

    def copy_one(row) -> tuple[str, str]:
        source = input_dir / row["datetime"]
        folder_name = row["folder_name"]
        dest = Path(row["folder"]) / source.name
        status_result = copy_acquisition_folder(source, dest, logger, overwrite)
        return folder_name, status_result

    rows = [row for _, row in acq_df.iterrows()]

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for folder, status in executor.map(copy_one, rows):
            counters[folder][status] += 1

    return counters

def write_detected_acquisition_configs(unique_configs : pd.DataFrame, config_file : Path, logger : logging.Logger):
    """ Write automatically detected acquisition configurations to a CSV file. """
    config_file.parent.mkdir(parents=True, exist_ok=True)
    unique_configs.to_csv(config_file, index=False)
    logger.info("Wrote detected acquisition configurations to %s", config_file)


def run(ctx,
        input_dir: Path,
        output_dir: Path,
        config_file: Path = None):
    """Split UVP acquisitions folders into one folder per acquisition configuration."""
    
    logger = setup_logger("uvptoolbox.acquisition_split", debug=ctx.obj.get("debug", False))
    
    
    overwrite = ctx.obj.get("overwrite", False)
    threads = ctx.obj.get("threads", 1)

    logger.info("Starting acquisition-split")
    logger.info("Input data folder: %s", input_dir)
    logger.info("Output data folder: %s", output_dir)
    logger.info("Overwriting in output folder: %s", overwrite)
    if threads > 1:
        logger.info("Parallel threads: %d", threads)


    # Make sure we have access to input data
    if not input_dir.exists():
        raise click.ClickException(f"Input directory does not exist: {input_dir}")

    # Check output dir
    if not output_dir.exists():
        logger.info("Output data directory created: %s", output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
    # Check config file
    if config_file is not None:
        if config_file.exists():
            logger.info("Using existing acquisition config file: %s", config_file)
        else:
            logger.info("Acquisition config file not found. A new one will be created if more than one configuration is detected: %s",
            config_file)
    

    data_files = list(input_dir.rglob("*_data.txt"))
    if not data_files:
        logger.warning("No data files found in %s", input_dir)
        return

    acq_df = extract_acquisition_parameters(data_files, logger=logger)
    if acq_df.empty:
        logger.warning("No valid acquisition parameters could be extracted")
        return
    
    if config_file is not None and config_file.exists():
        acq_df = get_provided_acquisition_configs_folders(acq_df, config_file, logger=logger)
    else:
        unique_configs = detect_unique_acquisition_configs(acq_df, logger=logger)
        if unique_configs is None:
            acq_df["folder_name"] = "single_config"
        else:
            acq_df = acq_df.merge(unique_configs, how="left")
            if config_file is not None:
                write_detected_acquisition_configs(unique_configs, config_file, logger)
        

    # Build by-acquisition folders
    acq_df["folder"] = acq_df["folder_name"].apply(lambda x: output_dir / f"{x}")
    for folder in acq_df["folder"].drop_duplicates():
        folder.mkdir(parents=True, exist_ok=True)

    # Copy acquisitions to the appropriate folders
    counters = copy_acquisitions_to_config_folders(acq_df, input_dir, logger, overwrite, threads=threads)

    logger.info("Created / updated by-acquisition folders:")

    for folder_name, stats in counters.items():
        logger.info(
            "  %s -> %d copied, %d skipped, %d replaced.",
            folder_name,
            stats["copied"],
            stats["skipped"],
            stats["replaced"]
        )

    logger.info("Finished acquisition-split")

