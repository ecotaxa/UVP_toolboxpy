# UVPtoolbox

Python package and command-line tool to process UVP6 mooring data.

Following a long acquisition with the UVP6, you may need to create samples grouping data by time or acquisition parameters. 
`UVPtoolbox` helps simplify these operations and prepare UVP6 acquisitions for downstream workflows by:
- loading new acquisition folders from a source into a project,
- preparing a working directory and copying the folders to be processed into it,
- converting `data.txt` files from the 2023 format to the 2021 format expected by downstream tools,
- splitting acquisitions by acquisition configuration,
- merging acquisitions by time step or by day, with associated vignette copying,
- creating the metadata dataframe associated with the processed data,
- exporting processed merged results to a final directory.


## Installation

`UVPtoolbox` should preferably be installed in a virtual environment (venv/conda). 

For development or local use:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Once installed, the command-line interface should be available. To try it and output the help message:
```
uvptoolbox 
```

We plan to make a stable version available via pip once a stable version is operational:
```
pip install uvptoolbox
```
Not implemented yet. 

# Usage
The package is designed around the concept of a **project**, but most commands can also be used in **standalone mode** by explicitly providing input and output directories.
In project mode, arguments are automatically derived from the standard project structure, but they can still be overridden explicitly.

## Naming conventions

Raw acquisition folders are expected to follow the naming convention `YYYYMMDD-HHMMSS` (ex: `20250709-090000`).

## Command-line interface

A UVPtoolbox command line looks like :
```
uvptoolbox [GLOBAL_OPTIONS] command [COMMAND_OPTIONS]
```

Global options currently include:
```
  --debug       Show debugging messages.
  --overwrite   Overwrite existing outputs.
  --threads/-T  Number of parallel threads to use. Default: 1.
```

To see the list of available commands:
```
uvptoolbox --help
```

To see the options of a specific command:
```
uvptoolbox command --help
```


## Usage in project mode

### Project Structure
A project corresponds conceptually to a cruise, a time series, etc. In practice, it is a directory containing all files related to this dataset, organized with the standard structure expected by the processing commands.

Typical structure:
```
my_project/
    raw/                                folders storing all raw acquisitions 
    work/                               data created by the various processing steps
        all/                            acquisitions selected for processing
        by_acquisition/                 acquisitions split by acquisition configuration
    processed/                          exported merged acquisition folders
    config/                             configuration files
        acquisition_configs.csv         optional acquisition split configuration file
        cruise_info.txt                 optional file containing general mooring informations
        HW_[...].txt                    optional file containing hardware acquisition configuration parameters
        meta_constants.txt              optional file containing constant metadata fields (see seciion create-meta)
    logs/                               optional log and bookkeeping files
    meta/                               metadata outputs 
```
### Minimal workflow in project mode

A default end-to-end workflow command looks like:
```
uvptoolbox run-default-pipeline -p /path/to/project -i /path/to/source --by-day
```

The commands underlying this automatic processing pipeline can be run step by step independently in a project:
```
# Copy acquisition folders from a source input directory to the raw directory of a project (<project>/raw`).
uvptoolbox load-new-data -i /path/to/source -p /path/to/project

# Prepare a work directory and copy acquisitions not already processed from `<project>/raw` to `<project>/work/all`.
uvptoolbox start-process -p /path/to/project

# Convert UVP6 data.txt files in `<project>/work/all` from the 2023 format to the 2021 format expected downstream.
uvptoolbox convert-format -p /path/to/project

# Split acquisitions in `<project>/work/all` into one folder per acquisition configuration and store them in `<project>/work/by_acquisition`.
uvptoolbox acquisition-split -p /path/to/project

# Merge acquisitions in each `<project>/work/by_acquisition` by day, and copy corresponding vignettes.
uvptoolbox time-merge -p /path/to/project --by-day 

# Create or update metadata file(s) in `<project>/meta` from merged UVP data files and project configuration files.
uvptoolbox create-meta -p /path/to/project 

# Export processed data to `<project>/processed`
uvptoolbox export-results -p /path/to/project
```

## Detail commands usage

All commands can also be used in a **standalone mode**  without a project architecture or in a **project mode** where arguments are automatically set based on project standard structure but can be overwritten if explicitly provided.  

### load-new-data
Copy acquisition folders named with the convention `YYYYMMDD-HHMMSS` from an input source directory to an output directory. Only acquisitions not already present in the output folder are copied unless --overwrite is specified.

#### Standalone mode:
```
uvptoolbox load-new-data -i /path/to/source -o /path/to/output
```

#### Project mode:
```
uvptoolbox load-new-data -i /path/to/source -p /path/to/project
```
Default output directory in project mode is set to `<project>/raw`.

#### Notes : 
The source directory containing UVP6 downloads can be organized in an arborescence such as:
```
2025.05/                        meaning "the fifth download of 2025"
    09-11/                      an acquisition day
        20250911-000000/
        20250911-010000/
        ...
    09-12/                      another acquisition day
        20250912-000000/
        20250912-010000/
        ...
```
The command searches recursively through all directories and subdirectories to find acquisition folders named `YYYYMMDD-HHMMSS`, 
and copies them into the output directory without preserving the original grouping.

### start-process
Prepare a working directory named `work` for the upcoming processing steps and copy unprocessed raw data into `work/all`.

#### Standalone mode:
```
uvptoolbox start-process -i /path/to/input -o /path/to/output_root
```
This creates `<output_root>/work/all` and copy acquisition folders into it. 

Options:
- `--reset-work-dir` Empty the work directory before copying acquisitions. If you want to work on a new set of data to be processed you should reset the work folder whose output have already been archived. However, if you want to process data loaded in the work directory through multiple runs at the same time, you have to do multiple copy without erasing the work folder. Default: False
- `--skip-processed / --do-not-skip-processed` Skip acquisitions listed in the <acquisitions-to-skip-file> file if provided. Default:--skip-processed.
- `--acquisitions-to-skip-file` Path to a text file listing acquisition folder names to skip (ex  already processed acquisitions).

#### Project mode:
```
uvptoolbox start-process -p /path/to/project
```
In project mode, the command creates `<project>/work/all` and copy acquisition folder from `<project>/raw` into it. 
By default, `acquisitions-to-skip-file` is search in `<project>/logs/processed_acquisitions.txt` and acquisition folders listed in this file are not considered to avoid processing already processed data. 

### convert-format
Convert UVP data.txt files from 2023 format to the 2021 format expected downstream. This command changes the HW and ACQ lines by inserting the fields required by the older format. 

Conversion is done in place:
- the original file is archived as *_2023format.txt,
- the converted content is written back under the original *_data.txt name,
- existing archived originals (*_2023format.txt) are used to regenerate 2021 formatted files when --overwrite is enabled.

#### Standalone mode:
```
uvptoolbox convert-format -d /path/to/data_dir
```

#### Project mode:
```
uvptoolbox convert-format -p /path/to/project
```
Default working directory in project mode is set to `<project>/work/all`.

### acquisition-info
Inspect acquisition configurations found in UVP data files. It is mainly intended as a helper command to inspect available acquisition settings before running `acquisition-split`. It can also help prepare an acquisition_configs.csv file.

This command does not create or modify any file.

This command reads `*_data.txt` files recursively, extracts their acquisition parameters from the `ACQ` line, and reports the unique acquisition configurations detected in the input directory.

#### Standalone mode:
```
uvptoolbox acquisition-info -i /path/to/data_dir
```
#### Project mode:
```
uvptoolbox acquisition-info -p /path/to/project
```
In project mode the input directory defaults to `<project>/work/all.

### acquisition-split
Split UVP acquisitions folders into one folder per acquisition configuration.

The user can optionally provide the path to a CSV "configuration file" to define expected acquisition configurations and the corresponding `folder_name`.
If the file:
- exists: it is used,
- does not exist but the path is provided: configurations are detected automatically and the file is created.

This makes it possible to reuse the same grouping logic for later incoming data.

If some varying acquisition parameters are not listed in the config file, the command will warn that different acquisitions may be merged together.

Example of configuration file:
```
configuration_name,acquisition_frequency,folder_name
ACQ_obsea_off,0.100,OBSEA_Off
ACQ_obsea_on,0.100,OBSEA_On
ACQ_obsea_off,2.000,OBSEA_Off
ACQ_obsea_on,2.000,OBSEA_On
```
In this example, acquisitions with both 0.100 and 2.000 acquisition frequencies are grouped into OBSEA_Off and OBSEA_On folders according to their configuration names.

#### Standalone mode:
```
# without config file
uvptoolbox acquisition-split -i /path/to/input -o /path/to/output

# with config file
uvptoolbox acquisition-split -i /path/to/input -o /path/to/output -c /path/to/config.csv
```

#### Project mode:
```
uvptoolbox acquisition-split -p /path/to/project
```
Default arguments in project mode:
- input : `<project>/work/all`
- output : `<project>/work/by_acquisition`
- config file : `<project>/config/acquisition_configs.csv`

### time-info
Summarize the time coverage of UVP data files in a directory. It is mainly intended as a helper command to inspect available data and choose suitable arguments for running `time-merge`.

This command does not create or modify any file.

This command inspects `*_data.txt` files and reports:
- the number of data files found,
- how many correspond to raw acquisition files,
- how many are already renamed with `_UsedForMerge`,
- the total number of records found,
- the first and last datetimes,
- the number of covered days.

#### Standalone mode:
```
uvptoolbox time-info -d /path/to/data_dir
```
#### Project mode:
```
uvptoolbox time-info -p /path/to/project
```
In project mode all folders inside `<project>/work/by_acquisition` are inspected individually.

### time-merge
Merge acquisitions by time step or by day, and copy corresponding vignettes.
This step creates in the provided data folder merged folders such as `YYYYMMDD-HHMMSS_Merged/` containing:
- a `merged *_Merged_data.txt` file,
- a `1/` directory with copied vignettes.

#### Standalone mode:
```
# to merge by day
uvptoolbox time-merge -d /path/to/data_folder --by-day

# to merge by fixed XX-hours time step bins
uvptoolbox time-merge -d /path/to/data_folder -t XX
```
If neither --by-day nor --time-step is explicitly provided, daily merging is used by default.

Optional argument:   

`--start-datetime` Time in format `YYYYMMDD-HHMMSS`. 

- In `--time-step` mode, binning starts from this datetime. Default : the earliest datetime found in the data. 
- In `--time-step` or `--by-day` mode, acquisitions before this datetime are ignored. 


#### Project mode:
```
# to merge by day
uvptoolbox time-merge -p /path/to/project --by-day

# to merge by fixed XX-hours time step bins
uvptoolbox time-merge -p /path/to/project -t XX
```
In project mode all folders inside `<project>/work/by_acquisition` are processed.


### create-meta
Create or update metadata file(s) from merged UVP data files and project configuration files.

This step searches for merged acquisition files (`*Merged*_data.txt`). For each merged file, the command extracts variable fields such as `filename`, `profileid`, `endimg`, and `sampledatetime`, and combines them with constant fields read from:
- configuration files (`meta_constants.txt`, `cruise_info.txt`, and `HW_*.txt`)
- command-line arguments such as `--latitude`, `--longitude`, `--constant-depth`, and `--station-id`

The command creates a metadata table in which each row corresponds to one merged acquisition and includes fields such as `filename`, `profileid`, `endimg`, `sampledatetime`, `pixelsize`, `latitude`, `longitude`, and `constantdepth`.

If the metadata file already exists:
- with `--overwrite`, it is fully rebuilt from the current data
- without `--overwrite`, new rows are merged with the existing file and duplicate entries are updated

#### Standalone mode:

```
uvptoolbox create-meta -d /path/to/data_folder  -c /path/to/config_folder  -o /path/to/output_folder 
```
- `-d/--data-dir` must point to one folder containing merged UVP data files,
- `-c/--config-dir` must point to the folder containing configuration file: `meta_constants.txt` , `cruise_info.txt` and `HW_*.txt`
- `-o/--output-dir` is the directory where the metadata file will be written.

Output metadata files are named as: `<cruise>_<data_folder_name>_metadata.txt`. For example, processing the folder `OBSEA_Off` with `cruise=anerisvilanova` creates: `anerisvilanova_OBSEA_Off_metadata.txt`

Optional argument:   
- `--latitude` latitude of the mooring in decimal degrees,
- `--longitude` longitude of the mooring in decimal degrees,
- `--constant-depth` constant depth of the mooring in meters,
- `--station-id` station identifier. If not provided, the cruise acronym is used as a fallback.

Optional configuration file: `meta_constants.txt`:

An optional file named `meta_constants.txt` can be placed in the configuration directory to define or override constant metadata fields. It uses a simple key=value format, for example:
```
ship=mooring
sampletype=T
integrationtime=3600
stationid=OBSEA
constantdepth=20
comment=OBSEA mooring time series
latitude=43.318
longitude=5.353
```
Only constant metadata fields in the following list are taken into account (unknown keys are ignored with a warning) :

cruise, ship, bottomdepth, ctdrosettefilename, latitude, longitude, firstimage, volimage, aa, exp, dn, winddir, windspeed, seastate, nebuloussness, comment, yoyo, stationid, sampletype, integrationtime, argoid, pixelsize, constantdepth

Priority between sources is:
1. command-line arguments
2. meta_constants.txt
3. HW_*.txt and cruise_info.txt
4. built-in default values

#### Project mode:
```
uvptoolbox create-meta -p /path/to/project
```
In project mode:
- all folders inside `<project>/work/by_acquisition` are processed. One metadata file is created for each acquisition-configuration subdirectory. For example, if `<project>/work/by_acquisition` contains `OBSEA_Off/` and `OBSEA_On/` the command will generate one metadata file for each of these folders.
- the configuration directory defaults to `<project>/config`,
- the output directory defaults to `<project>/meta`.

Metadata files are written in the output directory with names of the form: `<cruise>_<acquisition_folder_name>_metadata.txt`. For example, with `cruise=anerisvilanova` the following files will be created: `anerisvilanova_OBSEA_Off_metadata.txt`, `anerisvilanova_OBSEA_On_metadata.txt`.

#### Notes
- cruise is read from the acron field in cruise_info.txt when available.
- volimage, aa, exp, and pixelsize are converted to the units expected in the metadata file if read from the `HW_*.txt` configuration file.
- integrationtime is by default kept to 3600 (value used in the original workflow) when not provided in `meta_constants.txt`.
- If no acquisition lines are found in a merged file, the file is still processed with endimg = 0.

### export-results
Export processed data by copying merged acquisition folders to a destination directory.

This step searches recursively for folders named `*_Merged` in the input directory and copies them to the output directory while preserving their relative tree structure.  
Folders named `*_UsedForMerge` are not exported.

Optionally, the command can also update a text file listing the raw acquisition folders that have already been processed and exported.

#### Standalone mode:
```
uvptoolbox export-results -i /path/to/input -o /path/to/output
```
In standalone mode:
- `-i/--input-dir` must point to a directory containing merged acquisition folders,
- `-o/--output-dir` is the directory where merged folders will be copied.

Optional argument:
- `--processed-acquisitions-file` path to a text file that will be updated with processed acquisition names. If --processed-acquisitions-file is provided, the command searches for folders named *_UsedForMerge in the input directory and appends their corresponding raw acquisition names (YYYYMMDD-HHMMSS) to the file. This can be useful to keep track of acquisitions already exported and avoid reprocessing them in future runs.

#### Project mode:

```
uvptoolbox export-results -p /path/to/project
```

In project mode:
- the input directory defaults to `<project>/work/by_acquisition`,
- the output directory defaults to `<project>/processed`,
- the processed acquisitions file defaults to `<project>/logs/processed_acquisitions.txt`.

#### Notes
The command preserves the relative tree structure of the input directory.

For example, if the input directory contains:
```
work/by_acquisition/
    OBSEA_Off/
        20250709-000000_Merged/
        20250709-000000_UsedForMerge/
        20250709-010000_UsedForMerge/
        20250710-000000_Merged/
        20250710-000000_UsedForMerge/
        20250710-010000_UsedForMerge/
    OBSEA_On/
        20250709-000000_Merged/
        ...
```

the exported output directory will contain:
```
processed/
    OBSEA_Off/
        20250709-000000_Merged/
        20250710-000000_Merged/
    OBSEA_On/
        20250709-000000_Merged/
        ...
```


## Current limitations
The package is under active refactoring; command names and options may still evolve.

