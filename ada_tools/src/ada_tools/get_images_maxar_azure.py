import os
import os.path
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Tuple

import click
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient
from bs4 import BeautifulSoup
from tqdm import tqdm

# TODO: use config.ini with configparser

# connection_string = os.environ["AZURE_CONNECTION_STRING"]
# container_name = os.environ["AZURE_CONTAINER_NAME"]

connection_string = ""
container_name = "redcross7270"


# Global mapping of thread ids to tqdm progress bars to show download progress.
PROGRESS_BARS: Dict[int, tqdm] = {}


def get_maxar_image_urls(disaster: str) -> List[str]:
    """
    Parse the image urls from a Maxar dataset webpage.

    The webpage contains a single <textarea> containing a newline-delimited list of
    urls. Written on 2020-11-03, will probably break in the future due to the nature of
    webpages.
    """
    base_url = "https://www.maxar.com/open-data/" + disaster
    response = urllib.request.urlopen(base_url)
    html = response.read()
    html_soup = BeautifulSoup(html, "html.parser")
    return [
        url.strip()
        for url in html_soup.find_all("textarea")[0].text.split("\n")
        if url.strip().endswith(".tif")
    ]


def split_pre_post(images: List[str], splitdate) -> Tuple[List[str], List[str]]:
    "Split images into the pre- and post-disaster images."
    if splitdate is not None:
        images_post = [
            x
            for x in images
            if datetime.strptime(x.split("/")[-2], "%Y-%m-%d")
            >= datetime.strptime(splitdate, "%Y-%m-%d")
        ]
        images_pre = [x for x in images if x not in images_post]
    else:
        images_pre = [x for x in images if "pre-" in x.split("/")[-4]]
        images_post = [x for x in images if "post-" in x.split("/")[-4]]
        if len(images_pre) == 0 and len(images_post) == 0:
            images_pre = [x for x in images if "/pre/" in x]
            images_post = [x for x in images if "/post/" in x]
    return images_pre, images_post


# download images to Azure blob storage
def download_and_upload_images_to_blob(
    images: List[Tuple[str, str]], max_threads: int = None, progress_format: float = 1e6
) -> None:
    """
    list: List of tuples of the form (url, destination path).
    max_threads: Maximum number of concurrent threads to download from. If None,
        Python's heuristics are used.
    progress_format: Download progress is printed as bytes / `progress_format`. For
        example, a value of 1e3 would print as kilobytes, 1e6 as megabytes, and so on.
    """

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    # Create the container if it doesn't exist
    # probably not necessary, but doesn't hurt
    if not container_client.exists():
        container_client.create_container()

    def upload_stream_to_blob(blob_name, data_stream):
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data_stream)

    def _download_and_upload(url_tuple):
        url, blob_name = url_tuple
        ident = threading.get_ident()
        PROGRESS_BARS[ident] = tqdm(desc=f"Thread {ident}")

        with urllib.request.urlopen(url) as response:
            data_stream = response.read()
            upload_stream_to_blob(blob_name, data_stream)
            pbar = PROGRESS_BARS[threading.get_ident()]
            pbar.total = len(data_stream) / progress_format
            pbar.update(len(data_stream) / progress_format)

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(_download_and_upload, images)


@click.command()
@click.option("--disaster", default="mauritius-oil-spill", help="name of the disaster")
@click.option("--dest", default="input", help="destination folder")
@click.option("--splitdate", default=None, help="split pre- and post-disaster by date")
@click.option("--maxpre", default=1000000, help="max number of pre-disaster images")
@click.option("--maxpost", default=1000000, help="max number of post-disaster images")
@click.option(
    "--maxthreads",
    default=None,
    type=int,
    help="max number of download threads, if omitted Python's heuristics are used",
)
@click.option(
    "--progress-format",
    type=click.Choice(["B", "KB", "MB", "GB"], case_sensitive=False),
    default="MB",
    help="size unit to format the download progress bar",
)
def main(disaster, dest, splitdate, maxpre, maxpost, maxthreads, progress_format):
    os.makedirs(dest, exist_ok=True)
    os.makedirs(dest + "/pre-event", exist_ok=True)
    os.makedirs(dest + "/post-event", exist_ok=True)

    urls = get_maxar_image_urls(disaster)
    images_pre, images_post = split_pre_post(urls, splitdate)

    # apply maxpre and maxpost
    images_pre = images_pre[:maxpre]
    images_post = images_post[:maxpost]

    print("Selected pre-images:")
    print("\n".join(images_pre))
    print("Selected post-images:")
    print("\n".join(images_post))

    size_numerator = {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9}.get(progress_format)

    # generate the destination paths
    paths = [
        (
            url,
            os.path.join(
                dest,
                "pre-event",
                url.replace(
                    "https://maxar-opendata.s3.us-west-2.amazonaws.com/events/", ""
                ).replace("/", "-"),
            ),
        )
        for url in images_pre
    ] + [
        (
            url,
            os.path.join(
                dest,
                "post-event",
                url.replace(
                    "https://maxar-opendata.s3.us-west-2.amazonaws.com/events/", ""
                ).replace("/", "-"),
            ),
        )
        for url in images_post
    ]

    # download_images(
    #     images=paths,
    #     max_threads=maxthreads,
    #     progress_format=size_numerator,
    # )

    download_and_upload_images_to_blob(
        images=paths,
        max_threads=maxthreads,
        progress_format=size_numerator,
    )


if __name__ == "__main__":
    main()
