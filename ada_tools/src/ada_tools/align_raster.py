import geopandas as gpd
import os
import numpy as np
from scipy.optimize import minimize
import click
from osgeo import gdal
import shutil
import math


def meters_to_decimal_degrees(meters, latitude):
    # from wikipedia (https://en.wikipedia.org/wiki/Earth%27s_circumference)
    # Measured around the poles, the circumference is 40,007.863 km (24,859.734 mi)
    # 40007.863 / 360 = 111.132952778 m/deg
    return meters / (111.132952778 * 1000 * math.cos(latitude * (math.pi / 180)))


def align(build_target, build_reference):
    build_target['build_id'] = build_target.index
    xy_bounds = ((-10., 10.), (-10., 10.))
    build_area = build_target.geometry.area.sum()
    build_ref = build_reference[['geometry']].copy()
    build = build_target[['build_id', 'geometry']].copy()
    res = minimize(translate, (0., 0.), bounds=xy_bounds, args=(build, build_ref, build_area),
                   options={"disp": True, "maxls": 100})
    return res


def translate(x_y, gdf, gdf_ref, total_area):
    # N.B. CRS must be in meters
    translated_geometry = gpd.GeoDataFrame()
    translated_geometry['build_id'] = gdf.index
    translated_geometry.geometry = gdf.geometry.translate(xoff=x_y[0], yoff=x_y[1])
    intersection = gpd.overlay(translated_geometry, gdf_ref, how='intersection').dissolve(by='build_id', aggfunc='sum')
    delta_overlap = total_area - intersection.geometry.area.sum()
    return np.log(delta_overlap)


def translate_raster(xb, yb, raster_start, raster_end):
    if raster_start != raster_end:
        shutil.copyfile(raster_start, raster_end)
    rast_src = gdal.Open(raster_end, 1)
    gt = rast_src.GetGeoTransform()
    gtl = list(gt)
    gtl[0] += meters_to_decimal_degrees(xb, gtl[3])
    gtl[3] += meters_to_decimal_degrees(yb, gtl[3])
    rast_src.SetGeoTransform(tuple(gtl))
    rast_src = None  # equivalent to save/close


@click.command()
@click.option('--targetbuild', default='buildings_target.geojson', help='target buildings')
@click.option('--referencebuild', default='buildings_reference.geojson', help='reference buildings')
@click.option('--alignedbuild', default='buildings_aligned.geojson', help='aligned buildings')
@click.option('--targetraster', default='input.tif', help='target raster')
@click.option('--alignedraster', default='output.tif', help='output raster')
def main(targetbuild, referencebuild, alignedbuild, targetraster, alignedraster):
    """
    translate target raster based on best alignment between target and reference buildings
    """

    for out in [alignedraster, alignedbuild]:
        path_to_out = os.path.split(out)[0]
        if path_to_out != '' and not os.path.exists(path_to_out):
            os.makedirs(path_to_out)

    build_target = gpd.read_file(targetbuild)
    build_reference = gpd.read_file(referencebuild)
    if len(build_target) > 0 and len(build_reference) > 0:
        target_crs = build_target.crs
        if target_crs is None:
            target_crs = "EPSG:4326"
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
            build_aligned.to_file(alignedbuild, driver='GeoJSON')
            translate_raster(xb, yb, targetraster, alignedraster)
        else:
            print("ERROR: alignment failed!")
            if targetraster != alignedraster:
                shutil.copyfile(targetraster, alignedraster)
    else:
        print("WARNING: no buildings to do alignment")
        if targetraster != alignedraster:
            shutil.copyfile(targetraster, alignedraster)


if __name__ == "__main__":
    main()