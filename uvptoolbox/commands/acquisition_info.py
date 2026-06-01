from pathlib import Path
import click

from uvptoolbox.utils import setup_logger
from uvptoolbox.commands.acquisition_split import extract_acquisition_parameters, detect_unique_acquisition_configs

## prout prout
def run(ctx,
        input_dir: Path):
    """Inspect acquisitions folders acquisition configuration."""

    logger = setup_logger("uvptoolbox.acquisition_info", debug=ctx.obj.get("debug", False))

    # Make sure we have access to input data
    if not input_dir.exists():
        raise click.ClickException(f"Input directory does not exist: {input_dir}")
    click.echo(f"Inspecting acquisitions in: {input_dir}")


    data_files = list(input_dir.rglob("*_data.txt"))
    if not data_files:
        click.echo(f"No data files found in {input_dir}")
        return

    acq_df = extract_acquisition_parameters(data_files, logger=logger)
    if acq_df.empty:
        click.echo(f"No valid acquisition parameters could be extracted from files in {input_dir}")
        return

    unique_configs = detect_unique_acquisition_configs(acq_df, logger=logger)
    if unique_configs is not None:
        click.echo("Detected acquisition configurations:")
        click.echo(unique_configs.to_string(index=False))

    



