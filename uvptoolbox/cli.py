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

@click.pass_context
def cli(ctx, debug):
    """UVPtoolbox command line interface."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

@cli.command(name="load-new-data")
@click.argument("project", type=click.Path(path_type=Path))
@click.argument("source_folder", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def load_new_data_cmd(ctx, project, source_folder):
    """Copy new data from source folder to the 'raw' UVPtoolbox project directory."""
    from uvptoolbox.commands import load_new_data
    load_new_data.run(ctx, project=project, source_folder=source_folder)

#@cli.command(name="start-process")
#@click.argument("project", type=click.Path(path_type=Path))
#@click.pass_context
#def start_process_cmd(ctx, project):
#    """Prepare the work directory of the UVPtoolbox project and copy unprocessed raw data into work/all."""
#    from uvptoolbox.commands import start_process
#    start_process.run(ctx, project=project)


def main(argv=None):
    cli(prog_name="uvptoolbox", args=argv)


if __name__ == "__main__":
    main()
