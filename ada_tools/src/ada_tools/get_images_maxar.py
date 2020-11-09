import urllib.request
from bs4 import BeautifulSoup
import sys
import time
import click
import os
from tqdm import tqdm
from typing import List


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


def get_maxar_image_urls(disaster: str) -> List[str]:
    """
    Parse the image urls from a Maxar dataset webpage.

    The webpage contains a single <textarea> containing a newline-delimited list of
    urls. Written on 2020-11-03, will probably break in the future due to the nature of
    webpages.
    """
    base_url = 'https://www.digitalglobe.com/ecosystem/open-data/' + disaster
    response = urllib.request.urlopen(base_url)
    html = response.read()
    html_soup = BeautifulSoup(html, 'html.parser')
    return [
        url.strip()
        for url in html_soup.find_all("textarea")[0].text.split("\n")
        if url.strip().endswith(".tif")
    ]


def download_images(urls: List[str], dest: str, maxpre: int, maxpost: int) -> None:
    images_pre = [x for x in urls if 'pre-' in x.split('/')[-4]]
    images_post = [x for x in urls if 'post-' in x.split('/')[-4]]
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


@click.command()
@click.option('--disaster', default='mauritius-oil-spill', help='name of the disaster')
@click.option('--dest', default='input', help='destination folder')
@click.option('--maxpre', default=1000000, help='max number of pre-disaster images')
@click.option('--maxpost', default=1000000, help='max number of post-disaster images')
def main(disaster, dest, maxpre, maxpost):
    os.makedirs(dest, exist_ok=True)
    os.makedirs(dest+'/pre-event', exist_ok=True)
    os.makedirs(dest+'/post-event', exist_ok=True)

    urls = get_maxar_image_urls(disaster)
    download_images(urls, dest, maxpre, maxpost)


if __name__ == "__main__":
    main()
