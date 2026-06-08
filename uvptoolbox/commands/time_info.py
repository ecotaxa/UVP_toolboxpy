from datetime import datetime
from pathlib import Path
import click

from uvptoolbox.utils import setup_logger,ACQUISITION_FOLDER_PATTERN
from uvptoolbox.commands.time_merge import concatenate_data_files



def run(ctx,
        data_dirs: list[Path]):
    """Summarize the time coverage of UVP data files in one or more directories."""

    logger = setup_logger("uvptoolbox.time_merge", debug=ctx.obj.get("debug", False))

    for data_dir in data_dirs:
        click.echo(f"Folder: {data_dir}")

        not_renamed = []
        renamed = []

        for file in data_dir.rglob("*_data.txt"):
            stem = file.stem
            if ACQUISITION_FOLDER_PATTERN.match(stem.removesuffix("_data")):  # not named _UsedForMerge_data.txt
                not_renamed.append(file)
            elif stem.endswith("_UsedForMerge_data") and ACQUISITION_FOLDER_PATTERN.match(stem.removesuffix("_UsedForMerge_data")):
                renamed.append(file)

        data_files = sorted(not_renamed + renamed)
        if not data_files:
            click.echo(f"No data files found in {data_dir}, skipping.")
            continue

        click.echo(
            f"Data files found: {len(data_files)}\n"
            f"  - {len(not_renamed)} acquisition files not yet renamed with _UsedForMerge\n"
            f"  - {len(renamed)} acquisition files already renamed with _UsedForMerge"
        )


        header_lines, data_records = concatenate_data_files(data_files, logger=logger)
        if not header_lines or not data_records:
            click.echo(f"No data found in any files of {data_dir}, skipping.")
            continue

        datetimes = []
        for line, _source in data_records:
            if not line:
                continue
            date_time_str = line.split(",", 1)[0]
            try:
                dt = datetime.strptime(date_time_str, "%Y%m%d-%H%M%S")
            except ValueError:
                try:
                    dt = datetime.strptime(date_time_str, "%Y%m%d-%H%M%S-%f")
                except ValueError as e:
                    raise click.ClickException(
                        f"Unsupported datetime format in {data_dir}: {date_time_str}") from e
            datetimes.append(dt)
        if not datetimes:
            click.echo(f"No valid datetimes found in {data_dir}, skipping.")
            continue

        unique_days = {dt.date() for dt in datetimes}


        click.echo(f"Total number of objects recorded: {len(datetimes)} \n "
                   f"First datetime: { min(datetimes).strftime('%Y%m%d-%H%M%S')} \n "
                   f"Last datetime: {max(datetimes).strftime('%Y%m%d-%H%M%S')} \n "
                   f"Covered days: {len(unique_days)} \n ")
