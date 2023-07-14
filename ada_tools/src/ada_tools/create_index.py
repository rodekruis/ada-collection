import click
import math
from pathlib import Path
import fiona
import rasterio
import numpy as np
from shapely.geometry import box, mapping
import geopandas as gpd
import pandas as pd
import os
import re
import datetime
import json
from typing import List, Tuple, Optional
import pathlib
from tqdm import tqdm


class Tile():

    def __init__(self, xmin=None, ymin=None, xmax=None, ymax=None, x=None, y=None, z=None):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        if self.is_set():
            bbox = '%s, %s, %s, %s' % (self.xmin, self.ymin, self.xmax, self.ymax)
        else:
            bbox = 'not set'
        return 'Tile[bbox: %s, x: %s, y: %s, z: %s]' % (bbox, self.x, self.y, self.z)

    def is_set(self):
        return self.xmin is not None and self.ymin is not None and self.xmax is not None and self.ymax is not None

    def get_geometry(self):
        return box(self.xmin, self.ymin, self.xmax, self.ymax)

    def get_feature(self):
        pass


class TileCollection(list):

    def __init__(self):
        self.geom = None
        self.extent = None

    def __str__(self):
        return 'TileCollection[tiles: %s]' % len(self)

    def generate_tiles(self, geom, z):
        self.geom = geom
        self.extent = geom.bounds

        from_tile = self.deg2tile(self.extent[1], self.extent[0], z)
        to_tile = self.deg2tile(self.extent[3], self.extent[2], z)
        x_start = min(from_tile[0], to_tile[0])
        x_end = max(from_tile[0], to_tile[0])
        y_start = min(from_tile[1], to_tile[1])
        y_end = max(from_tile[1], to_tile[1])

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                t = self.tileGeometry(x, y, z)
                if t.get_geometry().intersects(geom):
                    self.append(t)

    def export_shapefile(self, filename):
        if len(self) < 1:
            print('no tiles to save')
            return

        schema = {
            'geometry': 'Polygon',
            'properties': {
                'id': 'int',
                'x': 'int',
                'y': 'int',
                'z': 'int'
            },
        }

        with fiona.open(filename, 'w', 'ESRI Shapefile', schema) as c:
            tile_count = 1
            for t in self:
                geom = t.get_geometry()
                c.write({
                    'geometry': mapping(geom),
                    'properties': {
                        'id': tile_count,
                        'x': t.x,
                        'y': t.y,
                        'z': t.z
                    },
                })
                tile_count += 1

    def export_geometry_shapefile(self, filename):
        if self.geom is None:
            print('no tiles to save')
            return

        schema = {
            'geometry': 'Polygon',
            'properties': {'id': 'int'},
        }

        with fiona.open(filename, 'w', 'ESRI Shapefile', schema) as c:
            c.write({
                'geometry': mapping(self.geom),
                'properties': {'id': 0},
            })

    def deg2tile(self, lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return (xtile, ytile)

    def tileGeometry(self, x, y, z):
        n = 2.0 ** z
        xmin = x / n * 360.0 - 180.0
        xmax = (x + 1) / n * 360.0 - 180
        ymin = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        ymax = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
        return Tile(xmin, ymin, xmax, ymax, x, y, z)


def get_raster_in_dir(directory):
    rasters = sorted(Path(directory).rglob('*.tif'))
    if len(rasters) == 0:
        rasters = sorted(Path(directory).rglob('*.TIF'))
    if len(rasters) == 0:
        print('ERROR: no rasters found in', directory)
        return 0
    else:
        return rasters


def parse_date_in_filename(filename):
    pieces = re.findall(r"\d{4}", filename)
    year = pieces[0]
    month = pieces[1][:2]
    day = pieces[1][2:]
    return datetime.datetime(int(year), int(month), int(day))


def divide_images(
    folder: str, date_event: Optional[datetime.datetime]
) -> Tuple[List[str], List[str]]:
    """
    Divide images into pre- and post-disaster images, based on either the folder
    structure or on the date of the disaster. Returns two lists, the first with
    pre-disaster image paths and the second with post-disaster image paths.
    """
    if os.path.exists(os.path.join(folder, 'pre-event')) and os.path.exists(os.path.join(folder, 'post-event')):
        rasters_pre = get_raster_in_dir(os.path.join(folder, 'pre-event'))
        rasters_post = get_raster_in_dir(os.path.join(folder, 'post-event'))
    else:
        rasters_all = get_raster_in_dir(folder)
        rasters_pre, rasters_post = [], []
        for raster in rasters_all:
            filename = os.path.split(raster)[-1]
            date = parse_date_in_filename(filename)
            if date < date_event:
                rasters_pre.append(raster)
            else:
                rasters_post.append(raster)

    if len(rasters_pre) == 0 or len(rasters_post) == 0:
        raise Exception('ERROR: cannot divide pre- and post-event images')

    return rasters_pre, rasters_post


def get_extents(rasters_pre: List[str], rasters_post: List[str], rasters_crs: str) -> gpd.GeoDataFrame:
    """
    Get the geographical boundary of each raster image.

    Arguments:
      rasters_pre: list of pre-disaster image paths
      rasters_post: list of post-disaster image paths

    Returns a Geopandas dataframe with the following columns:
    - geometry: The corner points of the raster as a list of [left, bottom, right, top].
    - file: The path of this raster.
    - pre-post: The string 'pre-event' or 'post-event' indicating when the image was taken.
    """
    rasters_all = rasters_pre + rasters_post
    df = pd.DataFrame()
    crs = ""
    for raster in tqdm(rasters_all):
        with rasterio.open(raster) as raster_meta:
            try:
                bounds = raster_meta.bounds
            except:
                print('WARNING: raster has no bounds in tags')
                bounds = np.nan
            if 'crs' in raster_meta.meta.keys():
                if 'init' in raster_meta.meta['crs'].to_dict().keys():
                    crs = raster_meta.meta['crs'].to_dict()['init']
                else:
                    wkt_str = str(raster_meta.meta['crs'])
                    match_epsg = re.findall(r'\"[0-9]{4}\"|\"[0-9]{5}\"', wkt_str)
                    if len(match_epsg) > 0:
                        crs = f"EPSG:{match_epsg[-1][1:-1]}"
                    else:
                        print(f'WARNING: no EPSG code found in raster CRS, assigning {rasters_crs}')
                        print(wkt_str)
                        crs = rasters_crs
            else:
                print(f'WARNING: raster has no CRS in tags, assigning {rasters_crs}')
                crs = rasters_crs
            if raster in rasters_pre:
                tag = 'pre-event'
            else:
                tag = 'post-event'
            raster_str = str(raster)
            path = pathlib.PurePath(raster_str)
            if 'pre-event' in path.parent.name or 'post-event' in path.parent.name:
                raster_relative_data = os.path.join(path.parent.name, path.name)
            else:
                raster_relative_data = path.name
            raster_relative_data = str(raster_relative_data)
            df = pd.concat([df, pd.DataFrame({
                    'file': raster_relative_data,
                    'crs': crs,
                    'geometry': box(*bounds),
                    'pre-post': tag
                }, index=[0])], ignore_index=True)

    gdf = gpd.GeoDataFrame()
    if df.crs.nunique() > 1:
        print(f'WARNING: multiple CRS found {df.crs.unique()}, reprojecting to {rasters_crs}')
        for crs in df.crs.unique():
            df_crs = df[df['crs'] == crs].copy()
            gdf_crs = gpd.GeoDataFrame({'geometry': df_crs.geometry.tolist(),
                                        'file': df_crs.file.tolist(),
                                        'pre-post': df_crs['pre-post'].tolist()},
                                       crs=crs)
            if crs != rasters_crs:
                gdf_crs = gdf_crs.to_crs(rasters_crs)
            gdf = gdf.append(gdf_crs, ignore_index=True)
    else:
        print(df)
        print(crs)
        gdf = gpd.GeoDataFrame({'geometry': df.geometry.tolist(),
                                'file': df.file.tolist(),
                                'pre-post': df['pre-post'].tolist()},
                               crs=crs)
    return gdf


def generate_dummy_tiles(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Generate dummy tiles based on maxar naming convention
    """

    # Divide the area of `total_bounds` into tiles with their size determined by the
    # `zoom` parameter.

    # create DataFrame of tiles
    df_tiles = pd.DataFrame()
    unique_indices = []
    for ix, row in gdf.iterrows():
        filename = row["file"]
        m = re.search("[0-9]{12}", filename)
        df_tiles = df_tiles.append(pd.Series({'tile': m.group(0)}), ignore_index=True)

    df_tiles['pre-event'] = [[] for x in range(len(df_tiles))]
    df_tiles['post-event'] = [[] for x in range(len(df_tiles))]
    for ixt, rowt in df_tiles.iterrows():
        pre_event_images, post_event_images = [], []
        gdf_ = gdf[gdf["file"].str.contains(rowt["tile"])]
        geom = None
        for ix, row in gdf_.iterrows():
            geom = row["geometry"]
            if row['pre-post'] == 'pre-event':
                pre_event_images.append(row['file'])
            else:
                post_event_images.append(row['file'])
        if len(pre_event_images) > 0:
            df_tiles.at[ixt, 'pre-event'] = pre_event_images
        else:
            df_tiles.at[ixt, 'pre-event'] = np.nan
        if len(post_event_images) > 0:
            df_tiles.at[ixt, 'post-event'] = post_event_images
        else:
            df_tiles.at[ixt, 'post-event'] = np.nan
        df_tiles.at[ixt, 'geometry'] = geom

    # drop tiles that do not contain both pre- and post-event images
    df_tiles = df_tiles[(~pd.isna(df_tiles['pre-event'])) & (~pd.isna(df_tiles['post-event']))]

    # The pre-event and post-event columns contain lists of filenames, but geopandas
    # doesn't allow lists as GeoJSON properties to maintain compatibility with
    # shapefiles. We can work around this by converting them to dictionaries.
    df_tiles.loc[:, "pre-event"] = df_tiles["pre-event"].map(lambda l: dict(enumerate(l)))
    df_tiles.loc[:, "post-event"] = df_tiles["post-event"].map(lambda l: dict(enumerate(l)))

    gdf_tiles = gpd.GeoDataFrame(
        {
            'geometry': df_tiles.geometry.tolist(),
            'tile': df_tiles.tile.tolist(),
            'pre-event': df_tiles['pre-event'].tolist(),
            'post-event': df_tiles['post-event'].tolist()
        },
        crs=gdf.crs,
    )

    return gdf_tiles


def generate_tiles(gdf: gpd.GeoDataFrame, zoom: int) -> gpd.GeoDataFrame:
    """
    Generate tiles over the area spanned by the areas in `gdf`.

    Arguments:
      gdf: A Geopandas dataframe as returned by `get_extents`.
      zoom: Specifies the size of the tiles. The value `12` corresponds to a tilesize of
            around 380 km2. For further details, see the `TileCollection` class.

    Returns a Geopandas dataframe with the following columns:
    - geometry: The bounding box of the tile.
    - tile: A string uniquely defining the tile.
    """
    # Convert to WGS84 (EPSG:4326, the usual degrees of latitude and longitude) and get
    # the total area (i.e. the union of all bounding boxes).
    orig_crs = gdf.crs
    gdf_wgs = gdf.copy() #to_crs('EPSG:4326')
    total_bounds = box(*gdf_wgs.total_bounds)

    # Divide the area of `total_bounds` into tiles with their size determined by the
    # `zoom` parameter.
    zoom_level = zoom  # default 12, corresponding to tiles of area ~380 km2
    tc = TileCollection()
    tc.generate_tiles(total_bounds, zoom_level)

    # create DataFrame of tiles
    df_tiles = pd.DataFrame()
    for tile in tc:
        bounds_tile = np.array([tile.xmin, tile.ymin, tile.xmax, tile.ymax])
        df_tiles = pd.concat([df_tiles,
                              pd.Series(
                                  {
                                      'geometry': box(*bounds_tile),
                                      'tile': str(zoom_level)+'.'+str(tile.x)+'.'+str(tile.y)
                                  }
                              )], axis=1, ignore_index=True)

    print(df_tiles)
    # convert to GeoDataFrame
    gdf_tiles = gpd.GeoDataFrame(
        {'geometry': df_tiles.geometry.tolist(), 'tile': df_tiles.tile.tolist()},
        crs=orig_crs, #'EPSG:4326',
    )

    # convert back from EPSG:4326 to whatever the default was
    # gdf_tiles = gdf_tiles.to_crs(orig_crs)

    return gdf_tiles


def assign_images_to_tiles(
    df_tiles: gpd.GeoDataFrame, gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    For each tile, specify which images it can be obtained from.
    Adds a "pre-event" and "post-event" column to `df_tiles`.

    Arguments:
      df_tiles: The output of `generate_tiles`.
      gdf: The output of `get_extents`.

    Returns the `df_tiles` input argument.
    """
    df_tiles['pre-event'] = [[] for x in range(len(df_tiles))]
    df_tiles['post-event'] = [[] for x in range(len(df_tiles))]
    for ixt, rowt in df_tiles.iterrows():
        pre_event_images, post_event_images = [], []
        for ix, row in gdf.iterrows():
            bounds_image = rasterio.coords.BoundingBox(*row['geometry'].bounds)
            bounds_tile = rasterio.coords.BoundingBox(*rowt['geometry'].bounds)
            if not rasterio.coords.disjoint_bounds(bounds_image, bounds_tile):
                if row['pre-post'] == 'pre-event':
                    pre_event_images.append(row['file'])
                else:
                    post_event_images.append(row['file'])
        if len(pre_event_images) > 0:
            df_tiles.at[ixt, 'pre-event'] = pre_event_images
        else:
            df_tiles.at[ixt, 'pre-event'] = np.nan
        if len(post_event_images) > 0:
            df_tiles.at[ixt, 'post-event'] = post_event_images
        else:
            df_tiles.at[ixt, 'post-event'] = np.nan

    # drop tiles that do not contain both pre- and post-event images
    df_tiles = df_tiles[(~pd.isna(df_tiles['pre-event'])) & (~pd.isna(df_tiles['post-event']))]

    # The pre-event and post-event columns contain lists of filenames, but geopandas
    # doesn't allow lists as GeoJSON properties to maintain compatibility with
    # shapefiles. We can work around this by converting them to dictionaries.
    df_tiles.loc[:, "pre-event"] = df_tiles["pre-event"].map(lambda l: dict(enumerate(l)))
    df_tiles.loc[:, "post-event"] = df_tiles["post-event"].map(lambda l: dict(enumerate(l)))

    return df_tiles


@click.command()
@click.option('--data', default='input', help='input')
@click.option('--crs', default='EPSG:4326', help='imagery CRS')
@click.option('--date', default='2020-08-04', help='date of the event YYYY-MM-DD')
@click.option('--zoom', default=12, help='zoom level of the tiles')
@click.option('--dest', default='tile_index.geojson', help='output')
@click.option('--exte', default='', help='save extents as')
@click.option('--maxar-tiling/--no-maxar-tiling', default=False)
def main(data, crs, date, zoom, dest, exte, maxar_tiling):
    """
    Using the images in the `data` folder, divide the area into tiles.  The output
    written to `dest` is a GeoJSON file containing a collection of tiles, each with a
    unique id and the paths the pre- and post-disaster images overlapping the tile.
    """
    date_event = datetime.datetime.strptime(date, "%Y-%m-%d")
    rasters_pre, rasters_post = divide_images(data, date_event)
    print("getting image extents")
    gdf = get_extents(rasters_pre, rasters_post, crs)
    if exte != '':
        gdf_pre = gdf[gdf['pre-post'] == 'pre-event']
        gdf_pre.to_file(exte.replace('.geojson', '-pre-event.geojson'), driver="GeoJSON")
        gdf_pos = gdf[gdf['pre-post'] == 'post-event']
        gdf_pos.to_file(exte.replace('.geojson', '-post-event.geojson'), driver="GeoJSON")
    if maxar_tiling:
        print("generating dummy tiles")
        df_tiles = generate_dummy_tiles(gdf)
    else:
        print("generating tiles")
        df_tiles = generate_tiles(gdf, zoom)
        print("assigning images to tiles")
        df_tiles = assign_images_to_tiles(df_tiles, gdf)
    print("saving index")
    df_tiles.to_file(dest, driver="GeoJSON")


if __name__ == "__main__":
    main()
