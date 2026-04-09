#
# Command line interface for UVPtoolbox
#
# This consists of a main command (uvptoolbox) with subcommands for each processing step.
#

import click
from pathlib import Path
#TODO from uvptoolbox.utils import setup_logging

# List commands in the order they appear in this file
class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()

@click.group(cls=NaturalOrderGroup)
@click.option("--debug", is_flag=True, default=False, help="Show debugging messages.")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing outputs.")
@click.pass_context
def cli(ctx, debug, overwrite):
    """UVPtoolbox command line interface."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["overwrite"] = overwrite


@cli.command(name="load-new-data")
@click.option("--input-dir","-i", type=click.Path(exists=True, path_type=Path), required=True,
              help="Input folder containing acquisition folders to load.")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=None,
              help="Folder where new acquisition folders will be copied.")
@click.option("--project","-p", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory for project mode. If output-dir is not provided, it is set to <project>/raw.")
@click.pass_context
def load_new_data_cmd(ctx, input_dir, output_dir, project):
    """Copy acquisition folders named YYYYMMDD-HHMMSS from an input directory to an output directory. 
    Only new acquisitions are copied unless --overwrite is specified."""
    from uvptoolbox.commands import load_new_data
    if output_dir is None:
        if  project is not None :
            output_dir = project / "raw"
        else:
            raise click.UsageError("You must provide either --project or --output-dir.")
    load_new_data.run(ctx, input_dir=input_dir, output_dir=output_dir)


@cli.command(name="start-process")
@click.option("--input-dir","-i", type=click.Path(exists=True, path_type=Path), default=None,
              help="Input folder containing acquisition folders to be processed.")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=None,
              help="Root folder where the work directory will be created.")
@click.option("--reset-work-dir", is_flag=True, default=False,
              help="Empty the work directory before copying acquisitions.")
@click.option("--skip-processed/--do-not-skip-processed", default=True,
              help="Skip acquisitions listed in the <acquisitions-to-skip-file> file if provided. Default :--skip-processed.")
@click.option("--acquisitions-to-skip-file","-s", type=click.Path(path_type=Path), default=None,
              help="Path to a text file listing acquisition folder names to skip (ex : already processed acquisitions).")
@click.option("--project","-p", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory for project mode. If not provided explicitly: "
                   "--input-dir is set to <project>/raw, --output-dir is set to <project>, --acquisitions-to-skip-file is set to <project>/logs/processed_acquisitions.txt")
@click.pass_context
def start_process_cmd(ctx, input_dir, output_dir, reset_work_dir, skip_processed, acquisitions_to_skip_file, project):
    """Prepare a work directory and copy unprocessed raw data into work/all."""
    from uvptoolbox.commands import start_process
    
    if input_dir is None:
        if  project is not None :
            input_dir = project / "raw"
        else:
            raise click.UsageError("You must provide either --project or --input-dir.")
    
    if output_dir is None:
        if project is not None :
            output_dir = project 
        else:
            raise click.UsageError("You must provide either --project or --output-dir.")
        
    if acquisitions_to_skip_file is None and project is not None :
        acquisitions_to_skip_file = project / "logs/processed_acquisitions.txt"
    
    start_process.run(ctx, input_dir=input_dir, output_dir=output_dir, reset_work_dir=reset_work_dir,
                       skip_some_acquisitions=skip_processed, acquisitions_to_skip_file=acquisitions_to_skip_file)



@cli.command(name="convert-format")
@click.option("--data-dir", "-d", type=click.Path(exists=True, path_type=Path),default=None,
              help="Directory containing UVP data files to convert in place.")
@click.option("--project","-p", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory for project mode. If --data-dir is not provided, it is set to <project>/work/all.")
@click.pass_context
def convert_format_cmd(ctx, data_dir, project):
    """Convert UVP data.txt files from 2023 format to the 2021 format expected downstream. Conversion is done in place."""
    from uvptoolbox.commands import convert_format
    
    if data_dir is None:
        if project is not None :
            data_dir = project / "work" / "all"
        else:
            raise click.UsageError("You must provide either --project or --data-dir.")

    convert_format.run( ctx, data_dir=data_dir)


@cli.command(name="acquisition-split")
@click.option("--input-dir", "-i", type=click.Path(exists=True, path_type=Path), default=None,
              help="Input directory containing acquisition folders to split.")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=None,
              help="Output directory where one folder per acquisition configuration will be created.")
@click.option("--config-file", "-c", type=click.Path( path_type=Path), default=None,
              help="Optional CSV file defining acquisition configurations and their folder_name."
                   "If the file exists, it is used. If it does not exist, configurations are detected automatically and the file is created.\n"
                   "ex : "
                   "     configuration_name,acquisition_frequency,folder_name\n"
                   "     ACQ_obsea_off,0.100,OBSEA_Off\n"
                   "     ACQ_obsea_off,2.000,OBSEA_Off\n"
                   "     ACQ_obsea_on,0.100,OBSEA_On\n"
                   "     ACQ_obsea_on,2.000,OBSEA_On")
@click.option("--project", "-p", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory for project mode. If not provided explicitly: "
                   "--input-dir is set to <project>/work/all, --output-dir is set to <project>/work/by_acquisition, --config-file is set to <project>/config/acquisition_configs.csv")
@click.pass_context
def acquisition_split_cmd(ctx, input_dir, output_dir, config_file, project):
    """Split UVP acquisitions folders into one folder per acquisition configuration."""
    from uvptoolbox.commands import acquisition_split
    
    if input_dir is None:
        if project is not None :
            input_dir = project / "work" / "all"
        else:
            raise click.UsageError("You must provide either --project or --input-dir.")
    
    if output_dir is None:
        if project is not None :
            output_dir = project / "work" / "by_acquisition"
        else:
            raise click.UsageError("You must provide either --project or --output-dir.")
    
    if config_file is None and project is not None :
        config_file = project / "config" / "acquisition_configs.csv"
    
    acquisition_split.run(ctx, input_dir=input_dir, output_dir=output_dir, config_file=config_file)


@cli.command(name="time-merge")
@click.option("--data-dir","-d", type=click.Path(exists=True, path_type=Path), default=None,
              help="Path to a folder containing acquisition folders to process.")
@click.option("--by-day",is_flag=True,default=False,
              help="Merge acquisitions by day. Default mode if the time step is not specified.")
@click.option("--time-step","-t",type=float,default=None,
              help="Time step in hours used to merge the data. Use either --time-step or --by-day.")
@click.option("--start-datetime","-s", default=None,
              help="Optional start datetime in format YYYYMMDD-HHMMSS. Acquisitions before this datetime are ignored. "
                   "If not provided, the earliest datetime found in the data is used.")
@click.option("--project","-p", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory for project mode. If data-dir is not provided explicitly, all folders in <project>/work/by_acquisition will be processed.")
@click.pass_context
def time_merge_cmd(ctx, data_dir, by_day, time_step, start_datetime, project):
    """Merge acquisitions by time step or by day, and copy corresponding vignettes."""
    from uvptoolbox.commands import time_merge

    data_dirs =[]
    if data_dir is not None:
        data_dirs = [data_dir]
    else:
        if project is not None :
            base_dir = project / "work" / "by_acquisition"
            if base_dir.exists():
                data_dirs = [p for p in base_dir.iterdir() if p.is_dir()]
            if not base_dir.exists() or not data_dirs:
                raise click.ClickException(f"No data split by acquisition found in directory: {base_dir}")
        else:
            raise click.UsageError("You must provide either --project or --data-dir.")

    if time_step is None:
        by_day = True

    time_merge.run(ctx, data_dirs=data_dirs, by_day=by_day, time_step=time_step, start_datetime=start_datetime)



@cli.command(name="create-meta")
@click.option("--data-dir", "-d",type=click.Path(exists=True, path_type=Path), default=None,
              help="Directory containing merged UVP data files for one acquisition configuration.")
@click.option("--config-dir", "-c",type=click.Path(exists=True, path_type=Path),default=None,
              help="Directory containing project configuration files such as cruise_info.txt and HW_*.txt.")
@click.option("--output-dir", "-o",type=click.Path(path_type=Path),default=None,
              help="Output directory where metadata file(s) will be writen.")
@click.option("--latitude",type=str,default=None,help="Latitude of the mooring in decimal degrees.")
@click.option("--longitude",type=str,default=None,help="Longitude of the mooring in decimal degrees.")
@click.option("--constant-depth",type=str,default=None,help="Constant depth of the mooring in m.")
@click.option("--station-id",type=str,default=None, help="Station identifier. If not provided, the cruise acronym is used as fallback.")
@click.option("--project", "-p", type=click.Path(exists=True, path_type=Path), default=None,
              help="Project directory for project mode. If data-dir is not provided explicitly, one metadata file is created "
                   "for each acquisition-configuration subdirectory in <project>/work/by_acquisition."
              "If not provided explicitly: "
                   "--config-dir is set to <project>/config, --output-dir is set to <project>/meta")
@click.pass_context
def create_meta_cmd(ctx,data_dir,config_dir,output_dir,latitude,longitude,constant_depth,station_id,project):
    """Create metadata file(s) from merged UVP data files and project configuration files."""
    from uvptoolbox.commands import create_meta


    data_dirs = []
    if data_dir is not None:
        data_dirs = [data_dir]
    else:
        if project is not None:
            base_dir = project / "work" / "by_acquisition"
            if base_dir.exists():
                data_dirs = [p for p in base_dir.iterdir() if p.is_dir()]
            if not base_dir.exists() or not data_dirs:
                raise click.ClickException(f"No data split by acquisition found in directory: {base_dir}")
        else:
            raise click.UsageError("You must provide either --project or --data-dir.")
        
    if config_dir is None:
        if project is not None :
            config_dir = project / "config"
        else:
            raise click.UsageError("You must provide either --project or --config-dir.")

    if output_dir is None:
        if project is not None:
            output_dir = project / "meta"
        else:
            raise click.UsageError("You must provide either --project or --output-dir.")

    create_meta.run(ctx,data_dirs=data_dirs,config_dir=config_dir,output_dir=output_dir,
                    latitude=latitude, longitude=longitude,constant_depth=constant_depth,station_id=station_id)


def main(argv=None):
    cli(prog_name="uvptoolbox", args=argv)


if __name__ == "__main__":
    main()
