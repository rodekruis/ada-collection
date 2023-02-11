# Importing required module
import subprocess
from pathlib import Path
import os
import click


@click.command()
@click.option('--dir', help='directory with jp2 images')
@click.option('--dest', default="", help='target directory for geotiffs')
def main(dir, dest):

    for AOI in ['AOI3', 'AOI2', 'AOI4', 'AOI5']:
        os.makedirs(os.path.join(dir, AOI), exist_ok=True)
        for prepost in ['pre', 'post']:
            os.makedirs(os.path.join(dir, AOI, prepost+'-event'), exist_ok=True)
            for path in Path(os.path.join(dir, prepost+'-event')).rglob('*.zip'):
                if AOI in path.name:
                    target_path = os.path.join(dir, AOI, prepost+'-event', str(path.name))
                    subprocess.run(f"cp {str(path)} {target_path}", shell=True)
                    subprocess.run(f"unzip {target_path} -d {os.path.join(dir, AOI, prepost+'-event')}", shell=True)

            if dest == "":
                dest = os.path.join(dir, AOI, prepost+'-event')
            for path in Path(os.path.join(dir, AOI, prepost+'-event')).rglob('*.JP2'):
                path_jp2 = str(path)
                if dest == "":
                    path_tif = str(path).replace('.JP2', '.tif')
                else:
                    path_tif = os.path.join(dest, str(path.name).replace('.JP2', '.tif'))
                print(path.name)
                subprocess.run(f"gdal_translate -of GTiff -co TILED=YES {path_jp2} {path_tif}", shell=True)


if __name__ == "__main__":
    main()