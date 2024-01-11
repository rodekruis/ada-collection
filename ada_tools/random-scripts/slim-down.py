import geopandas as gpd
import os
import click
import shutil

@click.command()
@click.option('--dir', help='directory with index and images')
@click.option('--dest', default="", help='target directory for geotiffs')
def main(dir, dest):
    df = gpd.read_file(os.path.join(dir, 'tile_index.geojson'))
    imgs_all = []
    for ix, row in df.iterrows():
        dict_im = row['pre-event']
        imgs = dict_im.values()




if __name__ == "__main__":
    main()