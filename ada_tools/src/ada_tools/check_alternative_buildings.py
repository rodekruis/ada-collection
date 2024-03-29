import click
import rasterio
import numpy as np
from shapely.geometry import box
import geopandas as gpd
import pandas as pd
import os
from ada_tools.align_raster import align, translate
from azure.storage.blob import BlobServiceClient
from tqdm import tqdm
from shapely.geometry import Polygon


def download_blob(container, blobpath, filepath, secret):
    blob_service_client = BlobServiceClient.from_connection_string(secret)
    blob_client = blob_service_client.get_blob_client(container=container, blob=blobpath)
    with open(filepath, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())


def get_extent(raster: str) -> gpd.GeoDataFrame:
    """
    get extent of raster, return it as geodataframe
    """
    df = pd.DataFrame()
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
        df = df.append(pd.Series({
                'file': raster,
                'crs': crs.to_dict()['init'],
                'geometry': box(*bounds),
            }), ignore_index=True)

    if len(df.crs.unique()) > 1:
        raise Exception(f'ERROR: multiple CRS found: {df.crs.unique()}')

    crs_proj = df.crs.unique()[0]
    gdf = gpd.GeoDataFrame({'geometry': df.geometry.tolist(),
                            'file': df.file.tolist()},
                           crs=crs_proj)

    return gdf


@click.command()
@click.option('--ext', default='extents.geojson', help='input buildings extents')
@click.option('--builds', default='input', help='input buildings directory')
@click.option('--container', help='blob storage container')
@click.option('--secret', help='blob storage secret')
@click.option('--raster', default='input', help='input raster')
@click.option('--refbuilds', default='buildings.geojson', help='input reference buildings')
@click.option('--dest', default='buildings.geojson', help='output')
def main(ext, builds, container, secret, raster, refbuilds, dest):
    """
    check if builds cover raster, if yes align with refbuilds and save as dest
    """
    build_target = gpd.GeoDataFrame()
    gdf_raster = get_extent(raster)
    xmin, ymin, xmax, ymax = gdf_raster.total_bounds
    gdf_builds_extents = gpd.read_file(ext)
    gdf_builds_extents = gdf_builds_extents.rename(columns={'file': 'alternative_buildings_file'})
    res_intersection = gpd.overlay(gdf_raster, gdf_builds_extents, how='intersection')
    if not res_intersection.empty:
        for ix, row in res_intersection.iterrows():
            build_file = row["alternative_buildings_file"]
            download_blob(container, os.path.join(builds, build_file), build_file, secret)
            gdf_build = gpd.read_file(build_file)
            gdf_build_in_raster = gdf_build.cx[xmin:xmax, ymin:ymax]
            if not gdf_build_in_raster.empty:
                build_target = build_target.append(gdf_build_in_raster, ignore_index=True)

    build_reference = gpd.read_file(refbuilds)
    if len(build_target) > 0 and len(build_reference) > 0:
        target_crs = "EPSG:4326"
        build_target = build_target.set_crs(target_crs, allow_override=True)  # override Google's default ("Undefined geographic SRS")
        if build_reference.crs is None:
            build_reference.set_crs("EPSG:4326")
        build_target = build_target.to_crs("EPSG:8857")
        build_reference = build_reference.to_crs("EPSG:8857")

        res = align(build_target, build_reference)

        if res.success:
            print("Termination:", res.message)
            print("Number of iterations performed by the optimizer:", res.nit)
            print("Results:", res.x)
            xb, yb = res.x[0], res.x[1]
            build_aligned = build_target.copy()
            build_aligned.geometry = build_target.geometry.translate(xoff=xb, yoff=yb)
            build_aligned = build_aligned.to_crs(target_crs)
            build_aligned.to_file(dest, driver='GeoJSON')
        else:
            print(f"ERROR: alignment failed! keeping {refbuilds}")
    elif len(build_target) == 0 and len(build_reference) > 0:
        print("No alternative buildings found, continuing")
    elif len(build_target) > 0 and len(build_reference) == 0:
        print("No reference buildings found, continuing")
    elif len(build_target) == 0 and len(build_reference) == 0:
        print("No alternative and reference buildings found, continuing")


if __name__ == "__main__":
    main()
