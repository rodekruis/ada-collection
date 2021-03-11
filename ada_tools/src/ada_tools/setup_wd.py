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
from typing import Callable, List, NamedTuple
import rasterio
from rasterio.enums import Resampling
import numpy as np
from tqdm import tqdm


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


def first_non_nan_pixel(img: np.ndarray) -> np.ndarray:
    "Aggregation function returning the first pixel value that's not nan."
    out = np.zeros(img.shape[1:])
    out[...] = np.nan
    for i in range(img.shape[0]):
        mask = np.isnan(out)
        out[mask] = img[i, mask]

    return out


def create_raster_mosaic(
    tile: Tile,
    data: str,
    agg: Callable[[np.ndarray], np.ndarray] = first_non_nan_pixel
) -> None:
    """
    Create a mosaic of multiple raster images, cropped to a given tile.

    Args:
      tile: The tile to crop to.
      data: A folder containing the tif files to be mosaiced.
      agg: An aggregation function to combine the partially-overlapping rasters. If the
           `data` folder contains n images from which an (c, h, w) shaped window is read
           (c being the number of color channels, h the width and w the height), the
           input to the aggregation function will be an (n, c, h, w) shaped array
           containing NaN values for cases where part of a window fell outside of the
           image. The output of the function should then be (c, h, w). While it's
           tempting to use the average pixel value (i.e. np.nanmean), this is a bad
           idea; a pixel that's for example blue in one image because it's water could
           be white in another image because there's a cloud covering it. In this case,
           taking the mean will result in an unnatural gray color that would never be
           the true pixel color.
    """
    filenames = os.listdir(os.path.join(data))

    src_files = [os.path.join(data, name) for name in filenames]
    out_file = os.path.join(data, "merged.tif")

    rasters = []

    # The array size (out_shape) will be taken from the first image, along with a
    # corresponding profile (the set of metadata particular to that image) and. 
    # `transform` refers to an affine transformation matrix mapping pixel coordinates to
    # world coordinates, and will be calculated once the first window is generated.
    out_shape = None
    profile = None
    transform = None

    for path in tqdm(src_files, desc="Reading tif files"):
        with rasterio.open(path, "r") as f:
            # Calculate the boundary of the tile in pixel coordinates.
            window =f.window(
                tile.left, tile.bottom, tile.right, tile.top
            )

            # Read image data from the given window.
            # When `boundless` is True, parts of the window that fall outside of the
            # raster are given the `fill_value` value; this gives us consistently-sized
            # arrays to work with. When the image's dtype is uint8, which Maxar images
            # generally seem to be, there is no available fill_value that couldn't also
            # be a valid pixel value. Therefore we read it as a float and set the
            # fill_value to np.nan so that we can easily disregard them when generating
            # the mosaic.
            #
            # The images also tend to have slight differences in resolution, leading to
            # different array sizes. With the `out_shape` explicitly set, it rescales
            # the image to fit that shape.
            raster = f.read(
                window=window,
                boundless=True,
                out_shape=out_shape,
                fill_value=np.nan,
                out_dtype=np.float32,
                resampling=Resampling.lanczos,
            )

            if out_shape is None:
                out_shape = raster.shape
                profile = f.profile
                transform = f.window_transform(window)
            rasters.append(raster)

    # create the mosaic and convert it from float back to the original dtype
    mosaic = agg(np.stack(rasters, axis=0))
    mosaic = mosaic.astype(profile["dtype"])

    # update the profile with the new shape and affine transform
    profile.update(height=mosaic.shape[1], width=mosaic.shape[2], transform=transform)

    with rasterio.open(out_file, "w", **profile) as f:
        f.write(mosaic)


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
        copyfile(os.path.join(data, image), os.path.join(img_path, image))
    for image in tile.post_event:
        img_path = os.path.expanduser(os.path.join(dest, 'post-event'))
        os.makedirs(img_path, exist_ok=True)
        copyfile(os.path.join(data, image), os.path.join(img_path, image))

    create_raster_mosaic(tile, os.path.join(dest, 'pre-event'))
    create_raster_mosaic(tile, os.path.join(dest, 'post-event'))

    print('working directory has been set up', file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()