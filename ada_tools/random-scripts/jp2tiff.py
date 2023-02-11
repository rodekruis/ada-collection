# Importing required module
import subprocess
from pathlib import Path

import click


@click.command()
@click.option('--dir', help='directory with jp2 images')
def main(dir):
    for path in Path(dir).rglob('*.JP2'):
        path_jp2 = str(path)
        path_tif = str(path).replace('.JP2', '.tif')
        print(path_jp2, '-->', path_tif)

        # subprocess.run([
        #     "gdal_translate",
        #     "-of", "GTiff",
        #     "-co", "TILED=YES",
        #     f'"{path_jp2}"', f'"{path_tif}"'
        # ], shell=True)


if __name__ == "__main__":
    main()