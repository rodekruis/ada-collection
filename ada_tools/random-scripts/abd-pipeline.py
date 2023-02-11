# Importing required module
import subprocess
from pathlib import Path
import os
import click


@click.command()
@click.option('--dir', help='input directory')
@click.option('--dest', help='output directory')
@click.option('--config', help='config directory')
def main(dir, dest, config):

    for AOI in ['AOI3', 'AOI2', 'AOI4', 'AOI5']:
        dir = os.path.join(dir, AOI, 'pre-event')
        dest = os.path.join(dest, AOI)
        subprocess.run(f"abd cover --raster {dir}/*.tif --zoom 17 --out {dest}/cover.csv --crs EPSG:32630", shell=True)
        subprocess.run(f"abd tile --raster {dir}/*.tif --zoom 17 --cover {dest}/cover.csv --config {config}/config.toml --out {dest}/images --format tif --keep_borders", shell=True)
        subprocess.run(f"abd predict --cover {dest}/cover.csv --config {config}/config.toml --dataset {dest} --checkpoint {config}/neat-fullxview-epoch75.pth --out {dest}/predictions --metatiles --keep_borders", shell=True)
        subprocess.run(f"abd vectorize --config {config}/config.toml --masks {dest}/predictions --out {dest}/buildings.geojson --type Building", shell=True)


if __name__ == "__main__":
    main()