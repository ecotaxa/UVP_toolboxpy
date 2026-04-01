from collections import defaultdict
from pathlib import Path
import pandas as pd
from uvptoolbox.utils import setup_logger, copy_acquisition_folder
import click


def extract_acquisition_parameters(data_files, logger):
    """Extract the acquisition parameters in a list of uvp6 data files and returns a dataframe with all the parameters as different columns. 
     Add a 'datetime' column with the acquisition date.

    Args:
        data_files : The path of the UVP data files to be examined
    Returns:
        A pandas dataframe.
    """
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



def detect_unique_acquisition_configs(acq_df, logger):
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
        logger.info("All acquisitions have the same configuration")
        return None


def get_provided_acquisition_configs_folders(acq_df, config_file, logger):
    try:
        provided_configs = pd.read_csv(config_file, dtype=str)
    except Exception as e:
        raise ValueError( f"Unable to read provided acquisition configurations file, please check its format: {config_file}") from e

    if "folder_name" not in provided_configs.columns:
        raise ValueError("Config file must contain a 'folder_name' column")


    match_columns = [col for col in provided_configs.columns if col != "folder_name"]
    merged = acq_df.merge(provided_configs, on=match_columns, how="left")

    # check that all acquisition are affected to a folder
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



def copy_acquisitions_to_config_folders(acq_df, input_dir, logger, overwrite):
    """ Copy each acquisition folder into its corresponding config folder and rename it for merge processing. """
    counters = defaultdict(lambda: {"copied": 0, "skipped": 0, "replaced": 0, "renamed_data_files": 0})
    for _, row in acq_df.iterrows():
        source =  input_dir/ row["datetime"]
        folder_name = row["folder_name"]
        dest = Path(row["folder"]) / source.name
        #dest = Path(row["folder"]) / f"{row['datetime']}_UsedForMerge" 

        status = copy_acquisition_folder(source, dest, logger, overwrite)
        counters[folder_name][status] += 1

        #for file in dest.rglob("*_data.txt"):
        #    if re.match(r"^\d{8}-\d{6}_data\.txt$", file.name): # make sure we don't rename a file already named _UsedForMerge_data.txt
        #        new_name = file.with_name(file.stem.replace("_data", "_UsedForMerge_data") + file.suffix)
        #        if not new_name.exists() or overwrite:
        #            file.rename(new_name)
        #            counters[folder_name]["renamed_data_files"] += 1
    return counters

def write_detected_acquisition_configs(unique_configs, config_file, logger):
    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        unique_configs.to_csv(config_file, index=False)
        logger.info("Wrote detected acquisition configurations to %s", config_file)


def run(ctx,
        project_folder: Path = None,
        input_dir: Path = None,
        output_dir: Path = None,
        config_file: Path = None):
    logger = setup_logger("uvptoolbox.acquisition_split", debug=ctx.obj.get("debug", False))

    # Check that we have access to the data
    if input_dir is None :
        input_dir = project_folder / "work" / "all"
    if not input_dir.exists():
        logger.error("Input data directory does not exist: %s", input_dir)
        raise FileNotFoundError(f"Input data directory does not exist: {input_dir}")

    # Check output dir
    if output_dir is None and project_folder:
        output_dir = project_folder / "work" / "by_acquisition"
    if not output_dir.exists():
        logger.info("Output data directory does not exist, creating it: %s", output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Check config file
    if config_file is None and project_folder:
        default_config_file = project_folder / "config" / "acquisition_configs.csv"
        if default_config_file.exists():
            config_file = default_config_file
            logger.info("Using existing acquisition config file: %s", config_file)
    if config_file is None:
        default_config_file = None
        logger.info("No acquisition config file detected.")

    overwrite = ctx.obj.get("overwrite", False)

    logger.info("Starting acquisition-split")
    logger.info("Input data folder: %s", input_dir)
    logger.info("Output data folder: %s", output_dir)
    logger.info("Overwriting in output folder: %s", overwrite)

    data_files = list(input_dir.rglob("*data.txt"))
    if not data_files:
        logger.warning("No data files found in %s", input_dir)
        return

    acq_df = extract_acquisition_parameters(data_files, logger=logger)
    if acq_df.empty:
        logger.warning("No valid acquisition parameters could be extracted")
        return

    if config_file is None:
        unique_configs = detect_unique_acquisition_configs(acq_df, logger=logger)
        if unique_configs is None:
            acq_df["folder_name"] = "single_config"
        else:
            acq_df = acq_df.merge(unique_configs, how="left")
            if default_config_file is not None:
                write_detected_acquisition_configs(unique_configs, default_config_file, logger)
    else:
        acq_df = get_provided_acquisition_configs_folders(acq_df, config_file, logger=logger)

    # build folders
    acq_df["folder"] = acq_df["folder_name"].apply(lambda x: output_dir / f"{x}")
    for folder in acq_df["folder"].drop_duplicates():
        folder.mkdir(parents=True, exist_ok=True)
    
    counters = copy_acquisitions_to_config_folders(acq_df, input_dir, logger, overwrite)

    logger.info("Created / updated acquisition split folders:")

    for folder_name, stats in counters.items():
        logger.info(
            "  %s -> %d copied, %d skipped, %d replaced.",
            folder_name,
            stats["copied"],
            stats["skipped"],
            stats["replaced"]
        )

    logger.info("Finished acquisition-split")

