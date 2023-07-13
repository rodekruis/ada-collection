import geopandas as gpd
import pandas as pd
import click
from tqdm import tqdm
import os
import shutil
import time
start_time = time.time()

SPLIT_SIZE = 1000
THRESHOLD = 0.0001


def which_border_is_shared(bounds, bounds2):
    minx, miny, maxx, maxy = bounds[0], bounds[1], bounds[2], bounds[3]
    minx2, miny2, maxx2, maxy2 = bounds2[0], bounds2[1], bounds2[2], bounds2[3]
    if abs(minx - maxx2) < THRESHOLD or abs(minx - minx2) < THRESHOLD:
        return "x", minx
    elif abs(maxx - minx2) < THRESHOLD or abs(maxx - maxx2) < THRESHOLD:
        return "x", maxx
    elif abs(miny - maxy2) < THRESHOLD or abs(miny - miny2) < THRESHOLD:
        return "y", miny
    elif abs(maxy - miny2) < THRESHOLD or abs(maxy - maxy2) < THRESHOLD:
        return "y", maxy
    else:
        return "none", 0


def divide_dataframe(df, shuffle=False):
    if shuffle:
        df = df.sample(frac=1).reset_index(drop=True)
    xmin, ymin, xmax, ymax = df.total_bounds
    xhalf = (xmax+xmin)*0.5
    yhalf = (ymax+ymin)*0.5
    splitx = [df.cx[xmin:xhalf, ymin:ymax],
              df.cx[xhalf:xmax, ymin:ymax]]
    splity = [df.cx[xmin:xmax, ymin:yhalf],
              df.cx[xmin:xmax, yhalf:ymax]]
    if abs(len(splitx[0])-len(splitx[1])) < abs(len(splity[0])-len(splity[1])):
        return splitx
    else:
        return splity


def get_num_disj(gdf):
    df_sj = gpd.sjoin(gdf, gdf, how='left', predicate='intersects')
    df_sj = df_sj.reset_index().rename(columns={'index': 'index_left'})
    return len(df_sj[df_sj['index_left'] != df_sj['index_right']])


def divide_by_num_disj(gdf_list_to_divide):
    num_disj_list = [get_num_disj(gdf) for gdf in gdf_list_to_divide]
    while any([num_disj > SPLIT_SIZE for num_disj in num_disj_list]):
        gdf_list_new = []
        for gdf, num_disj in zip(gdf_list_to_divide, num_disj_list):
            if num_disj > SPLIT_SIZE:
                gdf_list_new = gdf_list_new + divide_dataframe(gdf)
            else:
                gdf_list_new.append(gdf)
        num_disj_list = [get_num_disj(gdf) for gdf in gdf_list_new]
        gdf_list_to_divide = gdf_list_new.copy()
    return gdf_list_to_divide


def merge_each_gdf_in_list(gdf_list):
    gdf_list_merged = []
    for ix, gdf in enumerate(gdf_list):
        print(f"merging buildings and appending {ix+1}/{len(gdf_list)} ({len(gdf_list_merged)})")
        gdf_list_merged.append(merge_touching_buildings(gdf))
    return gdf_list_merged


def combine_and_merge(gdf_list_merged):
    if len(gdf_list_merged) > 1:
        gdf_merged = gdf_list_merged[0].copy()
        gdf_list_to_combine = gdf_list_merged[1:].copy()

        while len(gdf_list_to_combine) > 0:
            print(f"combining and appending ({len(gdf_list_to_combine)})")
            gdf_list_new = []
            for gdf in tqdm(gdf_list_to_combine):
                len_gdf_merged, len_gdf = len(gdf_merged), len(gdf)
                gdf_combo = pd.concat([gdf_merged, gdf], ignore_index=True)
                x_or_y, coord = which_border_is_shared(gdf_merged.total_bounds, gdf.total_bounds)
                print("merging on:", x_or_y)
                if x_or_y == "x":
                    is_near = (abs(gdf_combo.bounds.minx - coord) < THRESHOLD*2.) | (abs(gdf_combo.bounds.maxx - coord) < THRESHOLD*2.)
                    gdf_combo_to_merge = gdf_combo[is_near]
                    gdf_combo_not_to_merge = gdf_combo[~is_near]
                    gdf_combo_to_merge = merge_touching_buildings(gdf_combo_to_merge)
                    gdf_merged = pd.concat([gdf_combo_to_merge, gdf_combo_not_to_merge], ignore_index=True)
                elif x_or_y == "y":
                    is_near = (abs(gdf_combo.bounds.miny - coord) < THRESHOLD*2.) | (abs(gdf_combo.bounds.maxy - coord) < THRESHOLD*2.)
                    gdf_combo_to_merge = gdf_combo[is_near]
                    gdf_combo_not_to_merge = gdf_combo[~is_near]
                    gdf_combo_to_merge = merge_touching_buildings(gdf_combo_to_merge)
                    gdf_merged = pd.concat([gdf_combo_to_merge, gdf_combo_not_to_merge], ignore_index=True)
                elif x_or_y == "none":
                    gdf_merged = gdf_combo
                print(f"{len_gdf_merged} + {len_gdf} --> {len(gdf_merged)}")
            gdf_list_to_combine = gdf_list_new.copy()
    else:
        gdf_merged = gdf_list_merged[0]
    print("final merge", len(gdf_merged))
    if get_num_disj(gdf_merged) > 0:
        gdf_merged = merge_touching_buildings(gdf_merged)
    print("final merge completed:", len(gdf_merged))
    return gdf_merged


def merge_touching_buildings(gdf):
    df_sj = gpd.sjoin(gdf, gdf, how='left', predicate='intersects')
    df_sj = df_sj.reset_index().rename(columns={'index': 'index_left'})
    num_disj_start = len(df_sj[df_sj['index_left'] != df_sj['index_right']])
    num_disj = num_disj_start
    while num_disj > 0:
        df_sj = df_sj.dissolve(by='index_right').rename_axis(index={'index_right': 'index'})
        df_sj = df_sj.drop_duplicates(subset=['geometry'])
        df_sj = df_sj[['geometry']]
        df_sj = gpd.sjoin(df_sj, df_sj, how='left', predicate='intersects')
        df_sj = df_sj.reset_index().rename(columns={'index': 'index_left'})
        num_disj = len(df_sj[df_sj['index_left'] != df_sj['index_right']])
        if num_disj > num_disj_start:
            df_sj = df_sj.dissolve(by='index_left')
    df_sj.drop(['index_left', 'index_right'], axis=1, inplace=True)
    return df_sj


@click.command()
@click.option('--data', help='input (vector format)')
@click.option('--dest', help='output (vector format)')
@click.option('--crsmeters', default='EPSG:4087', help='CRS in unit meters, to filter small buildings [default: EPSG:4087]')
@click.option('--waterbodies', default='', help='vector file of water bodies, to filter artifacts')
@click.option('--area', default=10, help='minimum building area, in m2 [default: 10]')
def main(data, dest, crsmeters, waterbodies, area):
    """ merge touching buildings, filter small ones, simplify geometry """

    gdf = gpd.read_file(data)
    crs_original = gdf.crs

    if len(gdf) == 0:
        shutil.copyfile(data, dest)
        return

    print(f'merge ({len(gdf)} entries)')

    # merge touching buildings
    gdf_list_split = divide_by_num_disj([gdf])
    if len(gdf_list_split) > 1:
        gdf_list_merged = merge_each_gdf_in_list(gdf_list_split)
        gdf = combine_and_merge(gdf_list_merged)
        print(f"merge completed ({len(gdf)} buildings)")

    # filter small stuff
    print(f"second filter ({len(gdf)} entries)")
    gdf = gdf.to_crs(crsmeters)
    gdf['area'] = gdf['geometry'].area
    gdf = gdf[gdf.area > area]
    gdf = gdf[['geometry']]
    print(f'filter completed ({len(gdf)} entries)')

    # simplify geometry
    gdf = gdf.simplify(tolerance=1., preserve_topology=True)
    gdf = gdf.to_crs(crs_original)
    gdf = gpd.GeoDataFrame(geometry=gdf)
    gdf = gdf[~(gdf.geometry.is_empty | gdf.geometry.isna())]

    # filter by water bodies
    if len(gdf) > 0 and os.path.exists(waterbodies):
        print('filtering by water bodies')
        gdf_water = gpd.read_file(waterbodies)
        if gdf.crs != gdf_water.crs:
            gdf = gdf.to_crs(gdf_water.crs)
        gdf = gpd.sjoin(gdf, gdf_water, how='left', predicate='intersects')
        gdf = gdf[gdf['TYPE'].isna()]
        gdf = gdf[['geometry']]

    if len(gdf) == 0:
        with open(dest, "w") as text_file:
            text_file.write('{"type": "FeatureCollection", "features": []}')
        return

    # project to WGS84 and save
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    gdf.to_file(dest, driver='GeoJSON')

    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
    main()
