# This import is unused. However, there is a long-standing bug on MacOS where loading a
# GeoJSON file fails with a bunch of "Shell is not a LinearRing" errors:
# https://github.com/geopandas/geopandas/issues/556
# In my particular case, using python 3.8 on MacOS 11 Big Sur with all packages
# installed through pip, importing shapely.geometry before importing geopandas is the
# magic fix.
import shapely.geometry

import geopandas as gpd
from shutil import copyfile
import os
import click
import json
import sys
from typing import List, NamedTuple


class Tile(NamedTuple):
    """
    Represents a tile with its bounding box coordinates and the list of corresponding
    pre/post event images.
    """
    pre_event: List[str]
    post_event: List[str]
    left: float
    bottom: float
    right: float
    top: float


def create_raster_mosaic(tile: Tile, data: str) -> None:
    filenames = os.listdir(os.path.join(data))
    out_file = os.path.join(data, "merged.tif")

    # clip using gdalwarp's -te flag, which takes a bounding box in x_min, y_min, x_max,
    # y_max format
    clip_str = f"-te {tile.left} {tile.bottom} {tile.right} {tile.top}"
    src_files = " ".join(os.path.join(data, name) for name in filenames)
    os.system(f"gdalwarp {clip_str} -r average {src_files} {out_file}")


def get_tile(df: gpd.GeoDataFrame, id: str) -> Tile:
    matches = df[df.tile == id]
    if len(matches) != 1:
        raise KeyError(f'ERROR: {id} not found in index')

    feature = matches.iloc[0, :]
    return Tile(
        list(feature["pre-event"].values()),
        list(feature['post-event'].values()),
        *feature.geometry.bounds # minx, miny, maxx, maxy
    )


@click.command()
@click.option('--data', help='input directory')
@click.option('--index', help='index')
@click.option('--id', help='id')
@click.option('--dest', help='output directory')
def main(data, index, id, dest):
    """
    Create `dest`/pre-event/merged.tif and `dest`/post-event/merged.tif for the given
    tile id. Any tif files overlapping the tile's area are mosaic'ed together, using the
    average pixel value where they overlap, and the resulting tif file is cropped to the
    area spanned by the tile.
    """
    index_df = gpd.read_file(index)
    tile = get_tile(index_df, id)

    for image in tile.pre_event:
        img_path = os.path.expanduser(os.path.join(dest, 'pre-event'))
        os.makedirs(img_path, exist_ok=True)
        copyfile(os.path.join(data, "pre-event", image), os.path.join(img_path, image))
    for image in tile.post_event:
        img_path = os.path.expanduser(os.path.join(dest, 'post-event'))
        os.makedirs(img_path, exist_ok=True)
        copyfile(os.path.join(data, "post-event", image), os.path.join(img_path, image))

    create_raster_mosaic(tile, os.path.join(dest, 'pre-event'))
    create_raster_mosaic(tile, os.path.join(dest, 'post-event'))

    print('working directory has been set up', file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()
