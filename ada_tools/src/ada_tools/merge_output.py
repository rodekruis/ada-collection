import geopandas as gpd
import os
import click


@click.command()
@click.option('--dir', help='directory with results')
@click.option('--path', default='12.', help='string in path')
@click.option('--data', default='buildings-predictions.geojson', help='result filename')
@click.option('--dest', default='buildings-predictions.geojson', help='output')
def main(dir, path, data, dest):
    gdf_merged = gpd.GeoDataFrame()
    for root, dirs, files in os.walk(dir):
        for file in files:
            if data in file and path in root:
                print(f'merging {os.path.join(root, file)}')
                gdf = gpd.read_file(os.path.join(root, file))
                gdf_merged = gdf_merged.append(gdf, ignore_index=True)
    gdf_merged.to_file(dest, driver="GeoJSON")


if __name__ == "__main__":
    main()
