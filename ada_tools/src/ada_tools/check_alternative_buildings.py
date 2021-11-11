import click
import rasterio
import numpy as np
from shapely.geometry import box
import geopandas as gpd
import pandas as pd
import os
from ada_tools.align_raster import align, translate


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
@click.option('--builds', default='input', help='input buildings directory')
@click.option('--raster', default='input', help='input raster')
@click.option('--refbuilds', default='buildings.geojson', help='input reference buildings')
@click.option('--dest', default='buildings.geojson', help='output')
def main(builds, raster, refbuilds, dest):
    """
    check if builds cover raster, if yes align with refbuilds and save as dest
    """
    build_target = gpd.GeoDataFrame()
    gdf_raster = get_extent(raster)
    for build_file in os.listdir(builds):
        gdf_build = gpd.read_file(os.path.join(builds, build_file))
        xmin, ymin, xmax, ymax = gdf_raster.total_bounds
        gdf_build_in_raster = gdf_build.cx[xmin:xmax, ymin:ymax]
        if not gdf_build.empty:
            build_target = build_target.append(gdf_build_in_raster, ignore_index=True)

    build_reference = gpd.read_file(refbuilds)
    if len(build_target) > 0 and len(build_reference) > 0:
        target_crs = build_target.crsbuild
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
            build_aligned.to_file(dest, driver='GeoJSON')
        else:
            print(f"ERROR: alignment failed! keeping {refbuilds}")
    elif len(build_target) == 0 and len(build_reference) > 0:
        print("No existing buildings found, continuing")
    elif len(build_target) > 0 and len(build_reference) == 0:
        print("No buildings found")
    else:
        print("WARNING: no buildings to do alignment")


if __name__ == "__main__":
    main()
