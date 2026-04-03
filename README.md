# UVPtoolbox

Python package and command-line tool to process UVP6 mooring data.

Following a long acquisition with the UVP6, you may need to create samples grouping data by time or acquisition parameters. 
`UVPtoolbox` helps simplify these operations and prepare UVP6 acquisitions for downstream workflows by:
- loading new acquisition folders from a source into a project,
- preparing a working directory and copy the folders to be processed into it,
- converting `data.txt` files from the 2023 format to the 2021 format expected by downstream tools,
- splitting acquisitions by acquisition configuration,
- merging acquisitions by time step or by day, with associated vignette copying,

The following steps are planned but not fully implemented yet:
- creating the metadata dataframe associated with the processed data,
- exporting results to other UVP projects.

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
  --debug      Show debugging messages.
  --overwrite  Overwrite existing outputs.
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
    raw/                                folders storing all raw acquisition 
    work/                               data created by the various processing steps
        all/                            acquisitions selected for processing
        by_acquisition/                 acquisitions split by acquisition configuration
    config/                             configuration files
        by_acquisition_configs.csv      optional acquisition split configuration file
    logs/                               optional log and bookkeeping files
    meta/                               metadata outputs (planned / in progress)
```
### Minimal workflow in project mode

To run the current processing pipeline step by step in a project:
```
# Copy acquisition folders from a source input directory to the raw directory of a project (<project>/raw`).
uvptoolbox load-new-data -i /path/to/source -p /path/to/project

# Prepare a work directory and copy acquisitions not already processed from `<project>/raw` to `<project>/work/all.
uvptoolbox start-process -p /path/to/project

# Convert UVP6 data.txt files in `<project>/work/all` from the 2023 format to the 2021 format expected downstream.
uvptoolbox convert-format -p /path/to/project

# Split acquisitions into one folder per acquisition configuration.
uvptoolbox acquisition-split -p /path/to/project

# Merge acquisitions by day or by fixed time step, and copy corresponding vignettes.
uvptoolbox time-merge -p /path/to/project --by-day 
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
- config file : `<project>/config/by_acquisition_configs.csv`


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

`--start-datetime` Time in format `YYYYMMDD- HHMMSS`. 

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

## Current limitations

Metadata generation Export/copy commands to external “final” UVP projects are still under development. 
The package is under active refactoring; command names and options may still evolve.

