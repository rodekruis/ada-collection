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
import dateparser


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

        from_tile = self.deg2tile(self.extent[0], self.extent[1], z)
        to_tile = self.deg2tile(self.extent[2], self.extent[3], z)
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
        ymin = x / n * 360.0 - 180.0
        ymax = (x + 1) / n * 360.0 - 180
        xmin = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        xmax = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
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


@click.command()
@click.option('--data', default='input', help='input')
@click.option('--date', default='2020-08-04', help='date of the event (to divide pre- and post-disaster images)')
@click.option('--zoom', default=12, help='zoom level of the tiles')
@click.option('--dest', default='tile_index.json', help='output')
def main(data, date, zoom, dest):

    date_event = dateparser.parse(date)

    ## DIVIDE PRE- AND POST-DISASTER IMAGES

    if os.path.exists(os.path.join(data, 'pre-event')) and os.path.exists(os.path.join(data, 'post-event')):
        rasters_pre = get_raster_in_dir(os.path.join(data, 'pre-event'))
        rasters_post = get_raster_in_dir(os.path.join(data, 'post-event'))
    else:
        rasters_all = get_raster_in_dir(data)
        rasters_pre, rasters_post = [], []
        for raster in rasters_all:
            filename = os.path.split(raster)[-1]
            date = parse_date_in_filename(filename)
            if date < date_event:
                rasters_pre.append(raster)
            else:
                rasters_post.append(raster)
    if len(rasters_pre) == 0 or len(rasters_post) == 0:
        print('ERROR: cannot divide pre- and post-event images')
        return 0

    rasters_all = rasters_pre+rasters_post

    ## CALCULATE GEOGRAPHICAL EXTENT OF RASTERS

    # get bounds and CRS of all rasters
    df = pd.DataFrame()
    for raster in rasters_all:
        with rasterio.open(raster) as raster_meta:
            try:
                bounds = raster_meta.bounds
            except:
                print('WARNING: raster has no bounds in tags')
                bounds = np.nan
            try:
                crs = raster_meta.meta['crs']
            except:
                print('WARNING: raster has no CRS in tags')
                crs = np.nan
            if raster in rasters_pre:
                tag = 'pre-event'
            else:
                tag = 'post-event'
            raster_root = os.path.split(raster)[1]
            df = df.append(pd.Series({
                    'file': raster_root,
                    'crs': crs.to_dict()['init'],
                    'geometry': box(*bounds),
                    'pre-post': tag
                }), ignore_index=True)

    if len(df.crs.unique()) > 1:
        print('ERROR: multiple CRS found')
        print(df.crs.unique())
        return 0

    crs_proj = df.crs.unique()[0]
    gdf = gpd.GeoDataFrame({'geometry': df.geometry.tolist(),
                            'file': df.file.tolist(),
                            'pre-post': df['pre-post'].tolist()},
                           crs=crs_proj)

    ## CALCULATE TILES

    # convert to WGS84 (EPSG:4326) to calculate tiles
    gdf_wgs = gdf.to_crs('EPSG:4326')
    total_bounds = box(*gdf_wgs.total_bounds)

    # calculate tiles
    zoom_level = zoom  # default 12, corresponding to tiles of area ~380 km2
    tc = TileCollection()
    tc.generate_tiles(total_bounds, zoom_level)

    # create GeoDataFrame of tiles
    df_tiles = pd.DataFrame()
    for tile in tc:
        bounds_tile = np.array([tile.xmin, tile.ymin, tile.xmax, tile.ymax])
        df_tiles = df_tiles.append(pd.Series({'geometry': box(*bounds_tile),
                                              'tile': str(zoom_level)+'.'+str(tile.x)+'.'+str(tile.y)}),
                                   ignore_index=True)
    gdf_tiles = gpd.GeoDataFrame({'geometry': df_tiles.geometry.tolist(),
                                  'tile': df_tiles.tile.tolist()},
                                 crs='EPSG:4326')
    # convert back to original CRS
    gdf_tiles = gdf_tiles.to_crs(crs_proj)

    ## ASSIGN IMAGES TO TILES

    df_tiles['pre-event'] = [[] for x in range(len(df_tiles))]
    df_tiles['post-event'] = [[] for x in range(len(df_tiles))]
    for ixt, rowt in gdf_tiles.iterrows():
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

    df_tiles = df_tiles[['tile', 'pre-event', 'post-event']]
    df_tiles.index = df_tiles.tile
    df_tiles = df_tiles.drop(columns=['tile'])
    df_tiles.to_json(dest, orient='index', default_handler=str)


if __name__ == "__main__":
    main()