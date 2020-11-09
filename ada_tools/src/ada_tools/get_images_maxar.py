import urllib.request
from bs4 import BeautifulSoup
import sys
import time
import click
import os
import os.path
from tqdm import tqdm
from typing import List, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor
import threading
from tqdm import tqdm


# Global mapping of thread ids to tqdm progress bars to show download progress.
PROGRESS_BARS: Dict[int, tqdm] = {}


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


def split_pre_post(images: List[str]) -> Tuple[List[str], List[str]]:
    "Split images into the pre- and post-disaster images."
    images_pre = [x for x in images if 'pre-' in x.split('/')[-4]]
    images_post = [x for x in images if 'post-' in x.split('/')[-4]]

    return images_pre, images_post


def download_images(
    images_pre: List[str],
    images_post: List[str],
    dest: str,
    maxpre: int,
    maxpost: int,
    max_threads: int = None,
) -> None:
    # reporthook function to update the progress bars
    def _reporthook(count, block_size, total_size):
        pbar = PROGRESS_BARS[threading.get_ident()]
        pbar.total = total_size
        pbar.update(block_size)

    # wrapper function to pass to the threads
    def _download(url, folder):
        # create the progress bar
        ident = threading.get_ident()
        PROGRESS_BARS[ident] = tqdm(desc=f"Thread {ident}")
        name = url.split('/')[-1]
        cat = url.split('/')[-2]
        name = f"{cat}-{name}"
        urllib.request.urlretrieve(url, os.path.join(folder, name), _reporthook)

    pre_paths = [os.path.join(dest, "pre-event")] * len(images_pre)
    post_paths = [os.path.join(dest, "post-event")] * len(images_post)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(_download, images_pre + images_post, pre_paths + post_paths)



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
    images_pre, images_post = split_pre_post(urls)
    print("Selected pre-images:")
    print("\n".join(images_pre))
    print("Selected post-images:")
    print("\n".join(images_post))
    download_images(images_pre, images_post, dest, maxpre, maxpost)


if __name__ == "__main__":
    main()
