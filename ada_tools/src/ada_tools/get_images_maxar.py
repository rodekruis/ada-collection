import urllib.request
from bs4 import BeautifulSoup
import sys
import time
import click
import os
from tqdm import tqdm


def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]


def reporthook(count, block_size, total_size):
    global start_time
    if count == 0:
        start_time = time.time()
        return
    duration = max(time.time() - start_time, 1)
    progress_size = int(count * block_size)
    speed = int(progress_size / (1024 * duration))
    percent = min(int(count * block_size * 100 / total_size), 100)
    sys.stdout.write("\r...%d%%, %d MB, %d KB/s, %d seconds passed" %
                    (percent, progress_size / (1024 * 1024), speed, duration))
    sys.stdout.flush()


def get_maxar_image_urls(base_url):
    response = urllib.request.urlopen(base_url)
    html = response.read()
    html_soup = BeautifulSoup(html, 'html.parser')
    return [el['href'] for el in html_soup.find_all('a') if el['href'].endswith('.tif')]


@click.command()
@click.option('--disaster', default='typhoon-mangkhut', help='name of the disaster')
@click.option('--dest', default='input', help='destination folder')
@click.option('--maxpre', default=1000000, help='max number of pre-disaster images')
@click.option('--maxpost', default=1000000, help='max number of post-disaster images')
def main(disaster, dest, maxpre, maxpost):
    os.makedirs(dest, exist_ok=True)
    os.makedirs(dest+'/pre-event', exist_ok=True)
    os.makedirs(dest+'/post-event', exist_ok=True)

    # scrape maxar webpage for image urls
    base_url = 'https://www.digitalglobe.com/ecosystem/open-data/' + disaster
    images = get_maxar_image_urls(base_url)

    # download images
    images_pre = [x for x in images if 'pre-' in x.split('/')[-4]]
    images_post = [x for x in images if 'post-' in x.split('/')[-4]]
    print('total pre-disaster images:', len(images_pre))
    print('total post-disaster images:', len(images_post))
    print('selecting intersection of pre- and post-disaster sets (images that are in both)')
    images_pre_selected = [x for x in images_pre if x.split('/')[-1] in [x.split('/')[-1] for x in images_post]]
    images_post_selected = [x for x in images_post if x.split('/')[-1] in [x.split('/')[-1] for x in images_pre]]
    images_pre_selected = sorted(images_pre_selected, key=lambda x: x.split('/')[-1])
    images_post_selected = sorted(images_post_selected, key=lambda x: x.split('/')[-1])
    print('selected pre-disaster images:', len(images_pre_selected))
    print('selected post-disaster images:', len(images_post_selected))
    print('downloading pre-disaster images')
    for url in tqdm(images_pre_selected[:min(len(images_pre_selected), maxpre)]):
        name = url.split('/')[-1]
        cat = url.split('/')[-2]
        name = cat+'-'+name
        urllib.request.urlretrieve(url, dest+'/pre-event/'+name, reporthook)
    print('downloading post-disaster images')
    for url in tqdm(images_post_selected[:min(len(images_post_selected), maxpost)]):
        name = url.split('/')[-1]
        cat = url.split('/')[-2]
        name = cat + '-' + name
        urllib.request.urlretrieve(url, dest + '/post-event/' + name, reporthook)


if __name__ == "__main__":
    main()