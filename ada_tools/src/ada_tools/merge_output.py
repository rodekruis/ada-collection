import geopandas as gpd
import os
import click


@click.command()
@click.option('--dir', help='directory with results')
@click.option('--data', default='buildings-predictions.geojson', help='result filename')
@click.option('--dest', default='buildings-predictions.geojson', help='output')
def main(dir, data, dest):
    gdf_merged = gpd.GeoDataFrame()
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.contains(data):
                gdf = gpd.read_file(file)
                gdf_merged = gdf_merged.append(gdf, ignore_index=True)
    gdf_merged.to_file(dest)


if __name__ == "__main__":
    main()
