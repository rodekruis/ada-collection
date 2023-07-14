import geopandas as gpd
import pandas as pd
import click
from tqdm import tqdm
import numpy as np


@click.command()
@click.option('--builds', help='input (buildings)')
@click.option('--damage', help='input (damage classes)')
@click.option('--out', default='buildings_predictions.geojson', help='input')
@click.option('--thresh', default="no", help='threshold to binarize output')
def main(builds, damage, out, thresh):
    df = gpd.read_file(builds).to_crs(epsg="4326")
    df = df.loc[~df["geometry"].is_empty]
    if "OBJECTID" in df.columns:
        df.index = df["OBJECTID"]
        df = df.drop(columns=["OBJECTID"])
    labels = pd.read_csv(damage, sep=" ")
    labels = labels[1:]
    labels['filename'] = labels['filename'].str.replace(".png", "")
    labels.index = labels["filename"]
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
        try:
            label = int(labels.loc[str(index), "label"])
            # binarize
            if thresh != "no":
                if float(label) > float(thresh):
                    label = 1.0
                else:
                    label = 0.0
            df.at[index, 'damage'] = label
        except:
            df.at[index, 'damage'] = np.nan
        df.at[index, 'ID'] = index
    df.to_file(out, driver='GeoJSON')


if __name__ == "__main__":
    main()
