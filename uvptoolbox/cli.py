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
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite acquisition folders already present in destination.")
@click.pass_context
def cli(ctx, debug, overwrite):
    """UVPtoolbox command line interface."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["overwrite"] = overwrite


@cli.command(name="load-new-data")
@click.argument("project", type=click.Path(exists=True, path_type=Path))
@click.argument("source_folder", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def load_new_data_cmd(ctx, project, source_folder):
    """Copy new data from source folder to the 'raw' UVPtoolbox project directory."""
    from uvptoolbox.commands import load_new_data
    load_new_data.run(ctx, project=project, source_folder=source_folder)


@cli.command(name="start-process")
@click.argument("project", type=click.Path(exists=True, path_type=Path))
@click.option("--input-folder", type=click.Path(exists=True, path_type=Path), default=None,
              help="Input folder containing acquisition folders. Defaults to <project>/raw.")
@click.option("--reset-work-dir", is_flag=True, default=False,
              help="Empty the work directory before copying acquisitions.")
@click.option("--skip-processed/--do-not-skip-processed", default=True,
              help="Skip acquisitions listed in <acquisitions-to-skip-file> file.")
@click.option("--acquisitions-to-skip-file", type=click.Path(path_type=Path), default=None,
              help="Path to a text file listing acquisition folder names to skip. "
                   "Defaults to <project>/logs/processed_acquisitions.txt.")
@click.pass_context
def start_process_cmd(ctx, project, input_folder, reset_work_dir, skip_processed, acquisitions_to_skip_file):
    """Prepare the work directory of the UVPtoolbox project and copy unprocessed raw data into work/all."""
    from uvptoolbox.commands import start_process
    start_process.run( ctx, project_folder=project, input_folder=input_folder, reset_work_dir=reset_work_dir,
                       skip_some_acquisitions=skip_processed, acquisitions_to_skip_file=acquisitions_to_skip_file)



@cli.command(name="convert-format")
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path),default=None,
              help="Directory containing UVP data files to convert.")
@click.option("--project", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory. If data-dir is not provided, it is set to <project>/work/all.")
@click.pass_context
def convert_format_cmd(ctx, data_dir, project):
    """Convert UVP data.txt files from 2023 format to the 2021 format expected downstream."""
    from uvptoolbox.commands import convert_format
    if project is None and data_dir is None:
        raise click.UsageError("You must provide either --project or --data-dir.")
    convert_format.run( ctx, project_folder=project, data_dir=data_dir)


@cli.command(name="acquisition-split")
@click.option("--input-dir", type=click.Path(exists=True, path_type=Path),default=None,
              help="Input directory containing acquisition folders to split.")
@click.option("--output-dir", type=click.Path(path_type=Path),default=None,
              help="Output directory where one folder per acquisition configuration will be created and the data will be sorted.")
@click.option("--project", type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory. If input-dir or output-dir is not provided, it is set to <project>/work/all for input and <project>/work/by_acquisition for output.")
@click.option("--config-file", type=click.Path(exists=True, path_type=Path), default=None,
              help="Optional CSV file defining expected acquisition configurations and their folder_name. "
                   "If not provided and --project is set, the command looks for <project>/config/acquisition_configs.csv. "
                   "If no config file is found, configurations are detected automatically and saved there when --project is set.",)
@click.pass_context
def acquisition_split_cmd(ctx, project, input_dir, output_dir, config_file):
    """Split UVP acquisitions folders into one folder per acquisition configuration."""
    from uvptoolbox.commands import acquisition_split
    if project is None and (input_dir is None or output_dir is None):
        raise click.UsageError( "You must provide either --project, or both --input-dir and --output-dir.")
    acquisition_split.run(ctx, project_folder=project, input_dir=input_dir, output_dir=output_dir, config_file=config_file)


@cli.command(name="time-merge")
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path), default=None,
              help="Path to a folder containing acquisition folders to process.")
@click.option("--project",type=click.Path(exists=True, path_type=Path),default=None,
              help="Project directory. If data-dir is not provided, all folders in <project>/work/by_acquisition will be processed.")
@click.option("--time-step",type=float,default=None,
              help="Time step in hours used to merge and split data. "
                   "Use either --time-step or --by-day.")
@click.option("--by-day",is_flag=True,default=False,help="Merge acquisitions by day instead of using a fixed time step.")
@click.option("--start-datetime", default=None,
              help="Optional start datetime in format YYYYMMDD-HHMMSS. Acquisitions before this datetime are ignored. "
                   "If not provided, the earliest datetime found in the data is used.")
@click.pass_context
def time_merge_cmd(ctx, data_dir, project, time_step, by_day, start_datetime):
    """Merge acquisitions by time step or by day, and copy corresponding vignettes."""
    from uvptoolbox.commands import time_merge

    if project is None and data_dir is None:
        raise click.UsageError("You must provide either --project or --data-dir.")

    if by_day and time_step is not None:
        raise click.UsageError("Use either --by-day or --time-step, not both.")

    if not by_day and time_step is None:
        raise click.UsageError("You must provide either --by-day or --time-step.")

    time_merge.run(ctx, project_folder=project, data_dir=data_dir, start_datetime=start_datetime, time_step=time_step, by_day=by_day)


def main(argv=None):
    cli(prog_name="uvptoolbox", args=argv)


if __name__ == "__main__":
    main()
