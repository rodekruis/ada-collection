from shutil import copyfile
import os
import click
import json
import sys


def create_raster_mosaic(data):
    filenames = os.listdir(os.path.join(data))
    out_file = 'merged.tif'

    if len(filenames) == 1:
        copyfile(os.path.join(data, filenames[0]), os.path.join(data, out_file))
    elif len(filenames) > 1:
        # recursively merge all rasters
        for ix, file in enumerate(filenames):
            if ix == 0:
                os.system('gdalwarp -r average {} {} {}'.format(os.path.join(data, file),
                                                                os.path.join(data, filenames[ix + 1]),
                                                                os.path.join(data, out_file)))
            elif ix == 1:
                continue
            else:
                os.system('gdalwarp -r average {} {} {}'.format(os.path.join(data, file),
                                                                os.path.join(data, out_file),
                                                                os.path.join(data, out_file)))


@click.command()
@click.option('--data', help='input directory')
@click.option('--index', help='index')
@click.option('--id', help='id')
@click.option('--dest', help='output directory')
def main(data, index, id, dest):

    with open(index) as file:
        index = json.load(file)

    if id not in index.keys():
        raise KeyError(f'ERROR: {id} not found in index')

    images = index[id]

    if 'pre-event' not in images.keys() or 'post-event' not in images.keys():
        print('WARNING: no pre- or post-event images, discarding', file=sys.stdout, flush=True)
        exit(0)

    for image in images['pre-event']:
        img_path = os.path.expanduser(os.path.join(dest, 'pre-event'))
        os.makedirs(img_path, exist_ok=True)
        copyfile(os.path.join(data, image), os.path.join(img_path, image))
    for image in images['post-event']:
        img_path = os.path.expanduser(os.path.join(dest, 'post-event'))
        os.makedirs(img_path, exist_ok=True)
        copyfile(os.path.join(data, image), os.path.join(img_path, image))

    create_raster_mosaic(os.path.join(dest, 'pre-event'))
    create_raster_mosaic(os.path.join(dest, 'post-event'))

    print('working directory has been set up', file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()