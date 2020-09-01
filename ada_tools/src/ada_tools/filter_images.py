import click
import os
import glob
import fiona
import rasterio
from rasterio.windows import get_data_window
from tqdm import tqdm
from shapely.geometry import box
import geopandas as gpd
from fiona.crs import from_epsg
from rasterio.mask import mask
from shutil import copyfile
import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]


def create_raster_mosaic(data, dest):
    for prepost in ['pre', 'post']:
        filenames = os.listdir(os.path.join(data, prepost + '-event'))
        tuples = []

        for filename in filenames:
            name = filename.split('-')[1]
            same = sorted([x for x in filenames if x.split('-')[1] == name])
            if same not in tuples and len(same) > 1:
                tuples.append(same)
        for tuple in tuples:
            out_file = tuple[0].split('.')[0] + '-merged.tif'
            for ix, file in enumerate(tuple):
                if ix == 0:
                    os.system('gdalwarp -r average {} {} {}'.format(os.path.join(data, prepost + '-event', file),
                                                                    os.path.join(data, prepost + '-event',
                                                                                 tuple[ix + 1]),
                                                                    os.path.join(dest, prepost + '-event', out_file)))
                elif ix == 1:
                    continue
                else:
                    os.system('gdalwarp -r average {} {} {}'.format(os.path.join(data, prepost + '-event', file),
                                                                    os.path.join(dest, prepost + '-event', out_file),
                                                                    os.path.join(dest, prepost + '-event', out_file)))
        # copy all the other rasters to dest
        for file in [x for x in filenames if x not in [item for tuple in tuples for item in tuple]]:
            copyfile(os.path.join(data, prepost + '-event', file), os.path.join(dest, prepost + '-event', file))


def filter_by_bbox(bbox, dest):
    bbox_tuple = [float(x) for x in bbox.split(',')]
    bbox = box(bbox_tuple[0], bbox_tuple[1], bbox_tuple[2], bbox_tuple[3])
    geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0], crs=from_epsg(4326))
    coords = getFeatures(geo)
    logger.info('filtering on bbox:')
    logger.info(coords)

    # loop over images and filter
    for raster in tqdm(glob.glob(dest + '/pre-event/*.tif')):
        raster = raster.replace('\\', '/')
        raster_or = raster
        out_name = raster.split('.')[0] + '-bbox.tif'
        with rasterio.open(raster) as src:
            logger.info('cropping on bbox')

            try:
                out_img, out_transform = mask(dataset=src, shapes=coords, crop=True)
                out_meta = src.meta.copy()
                out_meta.update({
                    'height': out_img.shape[1],
                    'width': out_img.shape[2],
                    'transform': out_transform})

                logger.info(f'saving {out_name}')
                with rasterio.open(out_name, 'w', **out_meta) as dst:
                    dst.write(out_img)
            except Exception as e:
                logger.info(f"Exception occurred: {e}.\nDiscarding.")

        os.remove(raster_or)


def filter_by_ntl(country, ntl_shapefile, dest):
    # filter mask by country (if provided)
    if country != '':
        country_ntl_shapefile = ntl_shapefile.split('.')[0] + '_' + country.lower() + '.shp'
        if not os.path.exists(country_ntl_shapefile):
            ntl_world = gpd.read_file(ntl_shapefile)
            ntl_world.crs = {'init': 'epsg:4326'}
            ntl_world = ntl_world.to_crs("EPSG:4326")
            world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
            country_shape = world[world.name == country]
            if country_shape.empty:
                logger.info(f"WARNING: country {country} not found!!!")
                logger.info('available countries:')
                logger.info(world.name.unique())
                logger.info('proceeding with global mask')
                country_ntl_shapefile = ntl_shapefile
            else:
                country_shape = country_shape.reset_index()
                country_shape.at[0, 'geometry'] = box(*country_shape.at[0, 'geometry'].bounds)
                country_shape.geometry = country_shape.geometry.scale(xfact=1.1, yfact=1.1)
                ntl_country = gpd.clip(ntl_world, country_shape)
                ntl_country.to_file(country_ntl_shapefile)
        with fiona.open(country_ntl_shapefile, "r") as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]
    else:
        with fiona.open(ntl_shapefile, "r") as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]

    # loop over images and filter
    for raster in tqdm(glob.glob(dest + '/pre-event/*.tif')):
        raster = raster.replace('\\', '/')
        raster_or = raster
        out_name = raster.split('.')[0] + '-ntl.tif'
        if 'ntl' in raster:
            continue
        crop_next = True

        logger.info(f'processing {raster}')
        out_name_ntl = raster.split('.')[0] + '-ntl-mask.tif'
        try:
            with rasterio.open(raster) as src:
                shapes_r = [x for x in shapes if
                            not rasterio.coords.disjoint_bounds(src.bounds, rasterio.features.bounds(x))]
                if len(shapes_r) == 0:
                    logger.info('no ntl present, discard')
                    crop_next = False
                else:
                    logger.info('ntl present, creating mask')
                    out_image, out_transform = rasterio.mask.mask(src, shapes_r, crop=True)
                    out_meta = src.meta

                    out_meta.update({"driver": "GTiff",
                                     "height": out_image.shape[1],
                                     "width": out_image.shape[2],
                                     "transform": out_transform})
                    # save temporary ntl file
                    logger.info(f'saving mask {out_name_ntl}')
                    with rasterio.open(out_name_ntl, "w", **out_meta) as dst:
                        dst.write(out_image)
                    crop_next = True
                raster = out_name_ntl
            if crop_next:
                with rasterio.open(raster) as src:
                    logger.info(f'cropping nan on {raster}')
                    window = get_data_window(src.read(1, masked=True))

                    kwargs = src.meta.copy()
                    kwargs.update({
                        'height': window.height,
                        'width': window.width,
                        'transform': rasterio.windows.transform(window, src.transform)})

                    logger.info(f'saving {out_name}')
                    try:
                        with rasterio.open(out_name, 'w', **kwargs) as dst:
                            dst.write(src.read(window=window))
                    except Exception as e:
                        logger.info(f"Exception occurred: {e}.\nDiscarding.")

                # remove temporary ntl file
                os.remove(raster)
                # remove original raster
                os.remove(raster_or)
        except Exception as e:
            logger.info(f"Exception occurred: {e}.\nDiscarding.")


@click.command()
@click.option('--mosaic', default=True, help='merge overlapping rasters')
@click.option('--data', default='input', help='original images')
@click.option('--dest', default='output', help='destination folder')
@click.option('--ntl', default=False, help='filter pre-event images by night-time lights (yes/no)')
@click.option('--bbox', default='', help='filter pre-event images by bounding box (CSV format)')
@click.option('--country', default='Philippines', help='country')
def main(mosaic, data, dest, ntl, bbox, country):

    os.makedirs(dest, exist_ok=True)
    os.makedirs(dest+'/pre-event', exist_ok=True)
    os.makedirs(dest+'/post-event', exist_ok=True)

    # create raster mosaic for rasters with same name (~ same area)
    print('creating mosaic of overlapping rasters')
    if mosaic:
        create_raster_mosaic(data, dest)

    # filter pre-event rasters

    print('filtering pre-event rasters')

    # filter by bounding box (if provided)
    if bbox != '':
        bbox_tuple = [float(x) for x in bbox.split(',')]
        bbox = box(bbox_tuple[0], bbox_tuple[1], bbox_tuple[2], bbox_tuple[3])
        geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0], crs=from_epsg(4326))
        coords = getFeatures(geo)
        print('filtering on bbox:')
        print(coords)

        # loop over images and filter
        for raster in tqdm(glob.glob(dest + '/pre-event/*.tif')):
            raster = raster.replace('\\', '/')
            raster_or = raster
            out_name = raster.split('.')[0] +'-bbox.tif'
            with rasterio.open(raster) as src:
                print('cropping on bbox')

                try:
                    out_img, out_transform = mask(dataset=src, shapes=coords, crop=True)
                    out_meta = src.meta.copy()
                    out_meta.update({
                        'height': out_img.shape[1],
                        'width': out_img.shape[2],
                        'transform': out_transform})

                    print('saving', out_name)
                    with rasterio.open(out_name, 'w', **out_meta) as dst:
                        dst.write(out_img)
                except:
                    print('empty raster, discard')

            os.remove(raster_or)

    # filter by nighttime lights

    # load nighttime light mask
    ntl_shapefile = 'input/ntl_mask_extended.shp'
    if ntl:
        # filter mask by country (if provided)
        if country != '':
            country_ntl_shapefile = ntl_shapefile.split('.')[0] + '_' + country.lower() + '.shp'
            if not os.path.exists(country_ntl_shapefile):
                ntl_world = gpd.read_file(ntl_shapefile)
                ntl_world.crs = {'init': 'epsg:4326'}
                ntl_world = ntl_world.to_crs("EPSG:4326")
                world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
                country_shape = world[world.name == country]
                if country_shape.empty:
                    print('WARNING: country', country, 'not found!!!')
                    print('available countries:')
                    print(world.name.unique())
                    print('proceeding with global mask')
                    country_ntl_shapefile = ntl_shapefile
                else:
                    country_shape = country_shape.reset_index()
                    country_shape.at[0, 'geometry'] = box(*country_shape.at[0, 'geometry'].bounds)
                    country_shape.geometry = country_shape.geometry.scale(xfact=1.1, yfact=1.1)
                    ntl_country = gpd.clip(ntl_world, country_shape)
                    ntl_country.to_file(country_ntl_shapefile)
            with fiona.open(country_ntl_shapefile, "r") as shapefile:
                shapes = [feature["geometry"] for feature in shapefile]
        else:
            with fiona.open(ntl_shapefile, "r") as shapefile:
                shapes = [feature["geometry"] for feature in shapefile]

        # loop over images and filter
        for raster in tqdm(glob.glob(dest+'/pre-event/*.tif')):
            raster = raster.replace('\\', '/')
            raster_or = raster
            out_name = raster.split('.')[0] + '-ntl.tif'
            if 'ntl' in raster:
                continue
            crop_next = True

            print('processing', raster)
            out_name_ntl = raster.split('.')[0] + '-ntl-mask.tif'
            try:
                with rasterio.open(raster) as src:
                    shapes_r = [x for x in shapes if not rasterio.coords.disjoint_bounds(src.bounds, rasterio.features.bounds(x))]
                    if len(shapes_r) == 0:
                        print('no ntl present, discard')
                        crop_next = False
                    else:
                        print('ntl present, creating mask')
                        out_image, out_transform = rasterio.mask.mask(src, shapes_r, crop=True)
                        out_meta = src.meta

                        out_meta.update({"driver": "GTiff",
                                         "height": out_image.shape[1],
                                         "width": out_image.shape[2],
                                         "transform": out_transform})
                        # save temporary ntl file
                        print('saving mask', out_name_ntl)
                        with rasterio.open(out_name_ntl, "w", **out_meta) as dst:
                            dst.write(out_image)
                        crop_next = True
                    raster = out_name_ntl
                if crop_next:
                    with rasterio.open(raster) as src:
                        print('cropping nan on', raster)
                        window = get_data_window(src.read(1, masked=True))

                        kwargs = src.meta.copy()
                        kwargs.update({
                            'height': window.height,
                            'width': window.width,
                            'transform': rasterio.windows.transform(window, src.transform)})

                        print('saving', out_name)
                        try:
                            with rasterio.open(out_name, 'w', **kwargs) as dst:
                                dst.write(src.read(window=window))
                        except:
                            print('empty raster, discard')

                    # remove temporary ntl file
                    os.remove(raster)
                    # remove original raster
                    os.remove(raster_or)
            except:
                print('error loading raster, skipping')

            # remove original raster
            # os.remove(raster_or)


if __name__ == "__main__":
    main()