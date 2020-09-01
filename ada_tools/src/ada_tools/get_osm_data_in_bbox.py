import overpy
api = overpy.Overpass()
import geopandas as gpd
from shapely.geometry import Polygon
import re
import math
from tqdm import tqdm

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


# SETTINGS
location_name = 'Beirut'
outfilename = 'buildings.geojson'

# BOUNDING BOX
# N.B. standard format (e.g. https://boundingbox.klokantech.com/) is [long_start, lat_start, long_end, lat_end]
bbounds = [35.466783, 33.862331, 35.542587, 33.916113]

# convert the bounding box into string for query
bbox_query = "s=\""+str(bbounds[1])+"\" w=\""+str(bbounds[0])+"\" n=\""+str(bbounds[3])+"\" e=\""+str(bbounds[2])+"\""

# call API
print('call API:')
r = api.query("""
<osm-script input="json">
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

print('store buildings:')
for index, way in tqdm(enumerate(r.ways)):
    coordinates = list_lon_lat[index]

    if coordinates[0] == coordinates[-1]:
        geom = Polygon(coordinates)
        geopandas_dataframe.loc[index_start + index_g, 'geometry'] = geom
        id = re.compile(r'id=([0-9]+)')
        geopandas_dataframe.loc[index_start + index_g, 'OBJECTID'] = id.findall(str(way).strip())
        index_g += 1

geopandas_dataframe = geopandas_dataframe[~(geopandas_dataframe.geometry.is_empty | geopandas_dataframe.geometry.isna())]

# convert to geodataframe and save as geojson
geopandas_dataframe.crs = {'init': 'epsg:4326'}
geopandas_dataframe.to_file(filename=outfilename, driver='GeoJSON')