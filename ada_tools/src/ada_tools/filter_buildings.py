import geopandas as gpd
import click

@click.command()
@click.option('--data', default='buildings.geojson', help='input')
@click.option('--dest', default='buildings-filtered.geojson', help='input')
@click.option('--area', default=5, help='minimum building area, in m2 [DEFAULT: 5]')
def main(data, dest, area):

    df = gpd.read_file(data)

    # filter by area
    crs_ = df.crs
    df = df.to_crs({'init': 'epsg:3857'})
    df['area'] = df['geometry'].area
    df = df[df.area > area]
    df = df[['geometry']]
    df = df.to_crs(crs_)

    # merge touching buildings
    df_sj = gpd.sjoin(df, df, how='left', op='intersects')
    df_new = df_sj.dissolve(by='index_right', aggfunc='sum')
    df_new = df_new.drop_duplicates(subset=['geometry'])
    df_new.to_file(dest, driver='GeoJSON')


if __name__ == "__main__":
    main()

