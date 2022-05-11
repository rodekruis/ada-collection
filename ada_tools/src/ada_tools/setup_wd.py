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
import shutil
import sys
from typing import Callable, List, NamedTuple
import rasterio
from rasterio.enums import Resampling
from rasterio.errors import DatasetIOShapeError
import numpy as np
from tqdm import tqdm
import re
from datetime import datetime


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


def first_non_nan_pixel(img: object) -> object:
    "Aggregation function returning the first pixel value that's not nan."
    out = np.zeros(img.shape[1:])
    out[...] = np.nan
    for i in range(img.shape[0]):
        mask = np.isnan(out)
        out[mask] = img[i, mask]
    return out


def create_raster_mosaic_simple(
        data: str
) -> None:
    """
    Create a mosaic of multiple raster images.
    Args:
      data: A folder containing the tif files to be mosaiced.
    """
    filenames = os.listdir(os.path.join(data))
    src_files = [os.path.join(data, name) for name in filenames if "merged" not in name]
    out_file = os.path.join(data, "merged.tif")

    if len(src_files) == 1:
        # just copy
        copyfile(os.path.join(src_files[0]), os.path.join(out_file))
    else:
        # create mosaic
        out_shape = None
        profile = None
        rasters = []

        try:
            src_files.sort(key=lambda x: datetime.strptime(re.search(r'\d{4}-\d{2}-\d{2}', x).group(), "%Y-%m-%d"),
                           reverse=True)
        except:
            pass

        for num_path, path in enumerate(tqdm(src_files, total=len(src_files))):
            src = rasterio.open(path, "r")
            try:
                raster = src.read(
                    boundless=True,
                    out_shape=out_shape,
                    fill_value=np.nan,
                    out_dtype=np.float32,
                    resampling=Resampling.lanczos,
                )
            except DatasetIOShapeError:
                continue
            if raster.shape[0] < 3:
                continue
            if out_shape is None:
                out_shape = raster.shape

            # update the profile with the new shape and affine transform
            if profile is None:
                profile = src.meta.copy()
                profile.update(dtype=rasterio.uint8,
                               compress='lzw')
            rasters.append(raster)

            if num_path > 0:

                # raster_mosaic = agg(np.stack(rasters, axis=0))
                raster_mosaic = rasters[0]
                raster_mosaic[np.isnan(raster_mosaic)] = rasters[1][np.isnan(raster_mosaic)]

                if num_path == len(src_files) - 1:
                    with rasterio.open(out_file, "w", **profile) as dst:
                        dst.write(raster_mosaic.astype(rasterio.int8))
                else:
                    num_path
                    rasters.clear()
                    rasters = [raster_mosaic.copy()]


def create_raster_mosaic_tiled(
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
    src_files = [os.path.join(data, name) for name in filenames if "merged" not in name]
    out_file = os.path.join(data, "merged.tif")

    # windows = [
    #     [tile.left, (tile.top+tile.bottom)/2, (tile.right+tile.left)/2, tile.top],
    #     [(tile.right+tile.left)/2, (tile.top+tile.bottom)/2, tile.right, tile.top],
    #     [tile.left, tile.bottom, (tile.right+tile.left)/2, (tile.top+tile.bottom)/2],
    #     [(tile.right+tile.left)/2, tile.bottom, tile.right, (tile.top+tile.bottom)/2]
    # ]
    wind_extr = [tile.left, tile.bottom, tile.right, tile.top]

    if len(src_files) == 1:
        # just crop
        src = rasterio.open(src_files[0], "r")
        window = src.window(wind_extr[0], wind_extr[1], wind_extr[2], wind_extr[3])
        try:
            raster = src.read(
                window=window,
                boundless=True,
                fill_value=np.nan,
                out_dtype=np.int8
            )
        except DatasetIOShapeError:
            pass
        if raster.shape[0] < 3:
            pass
        out_shape = raster.shape

        # update the profile with the new shape and affine transform
        profile = src.meta.copy()
        profile.update(height=window.height,
                       width=window.width,
                       transform=rasterio.windows.transform(window, src.transform),
                       dtype=np.int8)
        raster = raster.astype(np.int8)

        with rasterio.open(out_file, "w", **profile) as dst:
            dst.write(raster)
    else:
        # The array size (out_shape) will be taken from the first image, along with a
        # corresponding profile (the set of metadata particular to that image) and.
        # `transform` refers to an affine transformation matrix mapping pixel coordinates to
        # world coordinates, and will be calculated once the first window is generated.
        out_shape = None
        profile = None
        rasters = []

        try:
            src_files.sort(key=lambda x: datetime.strptime(re.search(r'\d{4}-\d{2}-\d{2}', x).group(), "%Y-%m-%d"),
                           reverse=True)
        except:
            pass

        for num_path, path in enumerate(tqdm(src_files, total=len(src_files))):
            src = rasterio.open(path, "r")
            window = src.window(wind_extr[0], wind_extr[1], wind_extr[2], wind_extr[3])
            try:
                raster = src.read(
                    window=window,
                    boundless=True,
                    out_shape=out_shape,
                    fill_value=np.nan,
                    out_dtype=np.float32,
                    resampling=Resampling.lanczos,
                )
            except DatasetIOShapeError:
                continue
            if raster.shape[0] < 3:
                continue
            if out_shape is None:
                out_shape = raster.shape

            # update the profile with the new shape and affine transform
            if profile is None:
                profile = src.meta.copy()
                profile.update(height=window.height,
                               width=window.width,
                               transform=rasterio.windows.transform(window, src.transform),
                               dtype=np.int8)
            rasters.append(raster)

            if num_path > 0 and len(rasters) > 0:
                raster_mosaic = rasters[0]
                try:
                    raster_mosaic[np.isnan(raster_mosaic)] = rasters[1][np.isnan(raster_mosaic)]

                    if num_path == len(src_files) - 1:
                        raster_mosaic = raster_mosaic.astype(np.int8)
                        with rasterio.open(out_file, "w", **profile) as dst:
                            dst.write(raster_mosaic)
                    else:
                        rasters.clear()
                        rasters = [raster_mosaic.copy()]
                except:
                    raster_mosaic = raster_mosaic.astype(np.int8)
                    with rasterio.open(out_file, "w", **profile) as dst:
                        dst.write(raster_mosaic)

    # rasters = {0: [], 1: [], 2: [], 3: []}
    # profiles = {0: [], 1: [], 2: [], 3: []}

    # for num_wind, wind_extr in enumerate(windows):
    #     if os.path.exists(out_file.replace('.tif', f'-{num_wind}.tif')):
    #         os.remove(out_file.replace('.tif', f'-{num_wind}.tif'))
    #
    # for num_path, path in enumerate(src_files):
    #
    #     src = rasterio.open(path, "r")
    #
    #     for num_wind, wind_extr in enumerate(windows):
    #         print(num_wind, wind_extr[0], wind_extr[1], wind_extr[2], wind_extr[3])
    #         window = src.window(wind_extr[0], wind_extr[1], wind_extr[2], wind_extr[3])
    #
    #         raster = src.read(
    #             window=window,
    #             boundless=True,
    #             out_shape=out_shape,
    #             fill_value=np.nan,
    #             out_dtype=np.float32,
    #             resampling=Resampling.lanczos,
    #         )
    #         if out_shape is None:
    #             out_shape = raster.shape
    #
    #         print(f'WINDOW {num_wind}: {raster.shape}')
    #
    #         # update the profile with the new shape and affine transform
    #         profile = src.meta.copy()
    #         profile.update(height=window.height,
    #                        width=window.width,
    #                        transform=rasterio.windows.transform(window, src.transform),
    #                        dtype=np.float32)
    #
    #         # with rasterio.open(out_file.replace('.tif', f'-{num_path}-{num_wind}.tif'), "w", **profile) as dst:
    #         #     dst.write(raster)
    #
    #         rasters[num_wind].append(raster)
    #         profiles[num_wind].append(profile)
    #
    # for num_wind in rasters.keys():
    #     raster_mosaic = agg(np.stack(rasters[num_wind], axis=0))
    #     profile = profiles[num_wind][0]
    #     # profile.update(dtype=np.float64)
    #
    #     with rasterio.open(out_file.replace('.tif', f'-{num_wind}.tif'), "w", **profile) as dst:
    #         dst.write(raster_mosaic)

    # for ix in tqdm(range(len(src_files)), desc="Reading tif files"):
    #     if ix == 0:
    #         src_files_ = src_files[:2]
    #         add_out_file = False
    #     elif ix == 1:
    #         continue
    #     else:
    #         src_files_ = [src_files[ix]]
    #         add_out_file = True
    #
    #     rasters = {0: [], 1: [], 2: [], 3: []}
    #
    #     for path in src_files_:
    #         with rasterio.open(path, "r") as f:
    #             # Calculate the boundary of the tile in pixel coordinates.
    #             # window =f.window(
    #             #     tile.left, tile.bottom, tile.right, tile.top
    #             # )
    #
    #             for num_wind, wind_extr in enumerate(windows):
    #                 print(num_wind, wind_extr[0], wind_extr[1], wind_extr[2], wind_extr[3])
    #                 window = f.window(wind_extr[0], wind_extr[1], wind_extr[2], wind_extr[3])
    #                 # Read image data from the given window.
    #                 # When `boundless` is True, parts of the window that fall outside of the
    #                 # raster are given the `fill_value` value; this gives us consistently-sized
    #                 # arrays to work with. When the image's dtype is uint8, which Maxar images
    #                 # generally seem to be, there is no available fill_value that couldn't also
    #                 # be a valid pixel value. Therefore we read it as a float and set the
    #                 # fill_value to np.nan so that we can easily disregard them when generating
    #                 # the mosaic.
    #                 #
    #                 # The images also tend to have slight differences in resolution, leading to
    #                 # different array sizes. With the `out_shape` explicitly set, it rescales
    #                 # the image to fit that shape.
    #                 raster = f.read(
    #                     window=window,
    #                     boundless=True,
    #                     out_shape=out_shape,
    #                     fill_value=np.nan,
    #                     out_dtype=np.float32,
    #                     resampling=Resampling.lanczos,
    #                 )
    #
    #                 if out_shape is None:
    #                     out_shape = raster.shape
    #                     profile = f.profile
    #                     transform = f.window_transform(window)
    #                 rasters[num_wind].append(raster)
    #                 # rasters_name[num_wind].append(path)
    #
    #                 if add_out_file:
    #                     rasters[num_wind].append(mosaics[num_wind])
    #                     # rasters_name[num_wind].append(out_file.replace('.tif', f'-{num_wind}.tif'))
    #
    #     # create the mosaic and convert it from float back to the original dtype
    #     # print(f"iteration {ix}, rasters {rasters_name[0]}")
    #     for num_wind in rasters.keys():
    #         mosaic = agg(np.stack(rasters[num_wind], axis=0))
    #         mosaic = mosaic.astype(profile["dtype"])
    #
    #         # update the profile with the new shape and affine transform
    #         profile.update(height=mosaic.shape[1], width=mosaic.shape[2], transform=transform)
    #
    #         with rasterio.open(out_file.replace('.tif', f'-{num_wind}.tif'), "w", **profile) as f:
    #             f.write(mosaic)
    #         if ix == 0:
    #             mosaics_path.append(out_file.replace('.tif', f'-{num_wind}.tif'))
    #             with rasterio.open(out_file.replace('.tif', f'-{num_wind}.tif'), "r") as f:
    #                 mosaics.append(f.read(
    #                         window=window,
    #                         boundless=True,
    #                         out_shape=out_shape,
    #                         fill_value=np.nan,
    #                         out_dtype=np.float32,
    #                         resampling=Resampling.lanczos,
    #                     ))

    # # merge all mosaics
    # os.system(r'gdalbuildvrt "{}" "{}" "{}" "{}" "{}"'.format(out_file.replace('.tif', '.vrt'),
    #                                                           os.path.join(data, "merged-0.tif"),
    #                                                           os.path.join(data, "merged-1.tif"),
    #                                                           os.path.join(data, "merged-2.tif"),
    #                                                           os.path.join(data, "merged-3.tif")))
    # os.system(r'gdal_translate "{}" "{}"'.format(out_file.replace('.tif', '.vrt'), out_file))
    # for path in mosaics_path:
    #     os.remove(path)


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
@click.option('--maxar-tiling/--no-maxar-tiling', default=False)
def main(data, index, id, dest, maxar_tiling):
    """
    Create `dest`/pre-event/merged.tif and `dest`/post-event/merged.tif for the given
    tile id. Any tif files overlapping the tile's area are mosaic'ed together, using the
    average pixel value where they overlap, and the resulting tif file is cropped to the
    area spanned by the tile.
    """

    index_df = gpd.read_file(index)
    if maxar_tiling:
        tile = index_df[index_df["tile"] == id].iloc[0]
        for image in tile['pre-event'].values():
            # image = image.replace(":", "%3A")
            img_path = os.path.expanduser(os.path.join(dest, 'pre-event'))
            os.makedirs(img_path, exist_ok=True)
            if 'pre-event' in image:
                img_path = os.path.expanduser(dest)
            copyfile(os.path.join(data, image), os.path.join(img_path, image))
        for image in tile['post-event'].values():
            # image = image.replace(":", "%3A")
            img_path = os.path.expanduser(os.path.join(dest, 'post-event'))
            os.makedirs(img_path, exist_ok=True)
            if 'post-event' in image:
                img_path = os.path.expanduser(dest)
            copyfile(os.path.join(data, image), os.path.join(img_path, image))

        create_raster_mosaic_simple(os.path.join(dest, 'pre-event'))
        create_raster_mosaic_simple(os.path.join(dest, 'post-event'))

    else:
        tile = get_tile(index_df, id)

        for image in tile.pre_event:
            img_path = os.path.expanduser(os.path.join(dest, 'pre-event'))
            os.makedirs(img_path, exist_ok=True)
            if 'pre-event' in image:
                img_path = os.path.expanduser(dest)
            copyfile(os.path.join(data, image), os.path.join(img_path, image))
        for image in tile.post_event:
            img_path = os.path.expanduser(os.path.join(dest, 'post-event'))
            os.makedirs(img_path, exist_ok=True)
            if 'post-event' in image:
                img_path = os.path.expanduser(dest)
            copyfile(os.path.join(data, image), os.path.join(img_path, image))

        create_raster_mosaic_tiled(tile, os.path.join(dest, 'pre-event'))
        create_raster_mosaic_tiled(tile, os.path.join(dest, 'post-event'))

    print('working directory has been set up', file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()
