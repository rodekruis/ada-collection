# Importing required module
import subprocess
from pathlib import Path
import os
import click


@click.command()
@click.option('--dir', help='directory with jp2 images')
@click.option('--dest', default="", help='target directory for geotiffs')
def main(dir, dest):
    for path in Path(dir).rglob('*.JP2'):
        path_jp2 = str(path)
        if dest == "":
            path_tif = str(path).replace('.JP2', '.tif')
        else:
            path_tif = os.path.join(dest, str(path.name).replace('.JP2', '.tif'))
        print(path.name)
        print(path_jp2)
        print(path_tif)

        subprocess.run(f"gdal_translate -of GTiff -co TILED=YES {path_jp2} {path_tif}", shell=True)


if __name__ == "__main__":
    main()