import overpy
api = overpy.Overpass()
import geopandas as gpd
from shapely.geometry import Polygon
import rasterio
import re
import math
from tqdm import tqdm
import click


def deg2tile(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)


@click.command()
@click.option('--raster', help='input (raster)')
@click.option('--out', default='buildings.geojson', help='output (buildings)')
def main(raster, out):
    # raster_file = '105001001875DA00-post.tif'
    ra = rasterio.open(raster)
    bounds = ra.bounds
    
    # convert the bounding box into string for query
    bbox_query = "s=\""+str(bounds.bottom)+"\" w=\""+str(bounds.left)+"\" n=\""+str(bounds.top)+"\" e=\""+str(bounds.right)+"\""
    
    # call API
    r = api.query("""
    <osm-script>
        <query type="way">
          <has-kv k="building"/>
          <bbox-query """+bbox_query+"""/>
        </query>
      <print mode="body"/>
      <recurse type="down"/>
      <print mode="skeleton"/>
    </osm-script>
    """)
    
    # get building outlines as a list of polygons
    nodes_of_ways = [way.get_nodes(resolve_missing=True) for way in r.ways]
    
    list_lon_lat = []
    for way in nodes_of_ways:
        list_of_ways = []
        for node in way:
            list_of_ways.append([float(node.lon), float(node.lat)])
        list_lon_lat.append(list_of_ways)
    
    geopandas_dataframe = gpd.GeoDataFrame()
    geopandas_dataframe['geometry'] = None
    index_start = len(geopandas_dataframe)
    index_g = 0
    id_re = re.compile(r'id=([0-9]+)')
    
    for index, way in tqdm(enumerate(r.ways)):
        coordinates = list_lon_lat[index]
    
        if coordinates[0] == coordinates[-1]:
            geom = Polygon(coordinates)
            geopandas_dataframe.loc[index_start + index_g, 'geometry'] = geom
            id = re.compile(r'id=([0-9]+)')
            objectid = id.findall(str(way).strip())
            if type(objectid) == list:
                geopandas_dataframe.loc[index_start + index_g, 'OBJECTID'] = objectid[0]
            else:
                geopandas_dataframe.loc[index_start + index_g, 'OBJECTID'] = objectid
            index_g += 1
    
    geopandas_dataframe = geopandas_dataframe[~(geopandas_dataframe.geometry.is_empty | geopandas_dataframe.geometry.isna())]
    
    # convert to geodataframe and save as geojson
    geopandas_dataframe.crs = {'init': 'epsg:4326'}
    print(geopandas_dataframe)
    geopandas_dataframe.to_file(filename=out, driver='GeoJSON')


if __name__ == "__main__":
    main()