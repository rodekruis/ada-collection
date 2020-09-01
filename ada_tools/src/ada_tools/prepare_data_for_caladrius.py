import os
import sys
import argparse
import datetime
import time
from shutil import move
from PIL import Image
import rasterio
import pandas as pd
import geopandas
from geopandas.tools import reverse_geocode

import numpy as np

# from PIL import Image
from tqdm import tqdm

import rasterio.mask
import rasterio.features
import rasterio.warp

import logging

logger = logging.getLogger(__name__)
logging.getLogger("fiona").setLevel(logging.ERROR)
logging.getLogger("fiona.collection").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.ERROR)


def exceptionLogger(exceptionType, exceptionValue, exceptionTraceback):
    logger.error(
        "Uncaught Exception",
        exc_info=(exceptionType, exceptionValue, exceptionTraceback),
    )


sys.excepthook = exceptionLogger

# supported damage types
DAMAGE_TYPES = ["destroyed", "significant", "partial", "none"]

# Fraction of image pixels that must be non-zero
NONZERO_PIXEL_THRESHOLD = 0.70


def damage_quantifier(category):
    stats = {
        "none": {"mean": 0.2, "std": 0.2},
        "partial": {"mean": 0.55, "std": 0.15},
        "significant": {"mean": 0.85, "std": 0.15},
    }

    if category == "none":
        value = np.random.normal(stats["none"]["mean"], stats["none"]["std"])
    elif category == "partial":
        value = np.random.normal(stats["partial"]["mean"], stats["partial"]["std"])
    else:
        value = np.random.normal(
            stats["significant"]["mean"], stats["significant"]["std"]
        )

    return np.clip(value, 0.0, 1.0)


def makesquare(minx, miny, maxx, maxy):
    rangeX = maxx - minx
    rangeY = maxy - miny

    # 20 refers to 5% added to each side
    extension_factor = 20

    # Set image to a square if not square
    if rangeX == rangeY:
        pass
    elif rangeX > rangeY:
        difference_range = rangeX - rangeY
        miny -= difference_range / 2
        maxy += difference_range / 2
    elif rangeX < rangeY:
        difference_range = rangeY - rangeX
        minx -= difference_range / 2
        maxx += difference_range / 2
    else:
        pass

    # update ranges
    rangeX = maxx - minx
    rangeY = maxy - miny

    # add some extra border
    minx -= rangeX / extension_factor
    maxx += rangeX / extension_factor
    miny -= rangeY / extension_factor
    maxy += rangeY / extension_factor
    geoms = [
        {
            "type": "MultiPolygon",
            "coordinates": [
                [[[minx, miny], [minx, maxy], [maxx, maxy], [maxx, miny], [minx, miny]]]
            ],
        }
    ]

    return geoms


def get_image_list(root_folder):
    image_list = []
    for path, subdirs, files in os.walk(root_folder):
        for name in files:
            if name.lower().endswith(".tif"):
                image_list.append(os.path.join(path, name).replace("\\","/"))
    return image_list


def save_image(image, transform, out_meta, image_path):
    # out_meta.update(
    #     {
    #         "driver": "PNG",
    #         "height": image.shape[1],
    #         "width": image.shape[2],
    #         "transform": transform,
    #     }
    # )
    # with rasterio.open(image_path, "w", **out_meta) as dest:
    #     dest.write(image)
    image = np.swapaxes(image, 0, 2)
    image = np.swapaxes(image, 0, 1)
    im = Image.fromarray(image)
    im.save(image_path)
    return image_path


def get_image_path(geo_image_path, object_id, TEMP_DATA_FOLDER):
    filename = "{}.png".format(object_id)

    image_path = geo_image_path.split("/")

    sub_folder = "before" if "pre-event" in image_path else "after"
    image_path = os.path.join(TEMP_DATA_FOLDER, sub_folder).replace("\\","/")

    os.makedirs(image_path, exist_ok=True)

    image_path = os.path.join(image_path, filename).replace("\\","/")

    return image_path


def match_geometry(image_path, geo_image_file, geometry):
    try:
        image, transform = rasterio.mask.mask(geo_image_file, geometry, crop=True)
        out_meta = geo_image_file.meta.copy()
        good_pixel_fraction = np.count_nonzero(image) / image.size
        if (
            np.sum(image) > 0
            and good_pixel_fraction > NONZERO_PIXEL_THRESHOLD
            and len(image.shape) > 2
            and image.shape[0] == 3
        ):
            return save_image(image, transform, out_meta, image_path)
    except ValueError:
        return False


def create_datapoints(df, ROOT_DIRECTORY, LABELS_FILE, TEMP_DATA_FOLDER):
    start_time = datetime.datetime.now()

    logger.info("Feature Size {}".format(len(df)))

    count = 0

    image_list = get_image_list(ROOT_DIRECTORY)

    # logger.info(len(image_list)) # 319

    with open(LABELS_FILE, "w+") as labels_file:
        for geo_image_path in tqdm(image_list):
            with rasterio.open(geo_image_path) as geo_image_file:
                df = df.to_crs(geo_image_file.crs)
                for index, row in tqdm(df.iterrows(), total=df.shape[0]):

                    bounds = row["geometry"].bounds
                    geometry = makesquare(*bounds)

                    # identify data point
                    if "OBJECTID" in row.keys():
                        object_id = row["OBJECTID"]
                    else:
                        object_id = index

                    image_path = get_image_path(geo_image_path, object_id, TEMP_DATA_FOLDER)
                    # print(image_path, geometry, geo_image_file)

                    if not os.path.exists(image_path):
                        save_success = match_geometry(
                            image_path, geo_image_file, geometry
                        )
                        if save_success:
                            logger.info("Saved image at {}".format(image_path))
                            count = count + 1

    delta = datetime.datetime.now() - start_time

    logger.info("Created {} Datapoints in {}".format(count, delta))


def split_datapoints(filepath, TARGET_DATA_FOLDER, TEMP_DATA_FOLDER):

    with open(filepath) as file:
        datapoints = file.readlines()

    allIndexes = list(range(len(datapoints)))

    np.random.shuffle(allIndexes)

    training_offset = int(len(allIndexes) * 0.8)

    validation_offset = int(len(allIndexes) * 0.9)

    training_indexes = allIndexes[:training_offset]

    validation_indexes = allIndexes[training_offset:validation_offset]

    testing_indexes = allIndexes[validation_offset:]

    split_mappings = {
        "train": [datapoints[i] for i in training_indexes],
        "validation": [datapoints[i] for i in validation_indexes],
        "test": [datapoints[i] for i in testing_indexes],
    }

    for split in split_mappings:

        split_filepath = os.path.join(TARGET_DATA_FOLDER, split).replace("\\","/")
        os.makedirs(split_filepath, exist_ok=True)

        split_labels_file = os.path.join(split_filepath, "labels.txt").replace("\\","/")

        split_before_directory = os.path.join(split_filepath, "before").replace("\\","/")
        os.makedirs(split_before_directory, exist_ok=True)

        split_after_directory = os.path.join(split_filepath, "after").replace("\\","/")
        os.makedirs(split_after_directory, exist_ok=True)

        with open(split_labels_file, "w+") as split_file:
            for datapoint in tqdm(split_mappings[split]):
                datapoint_name = datapoint.split(" ")[0]

                before_src = os.path.join(TEMP_DATA_FOLDER, "before", datapoint_name).replace("\\","/")
                after_src = os.path.join(TEMP_DATA_FOLDER, "after", datapoint_name).replace("\\","/")

                before_dst = os.path.join(split_before_directory, datapoint_name).replace("\\","/")
                after_dst = os.path.join(split_after_directory, datapoint_name).replace("\\","/")

                # print('{} => {} !! {}'.format(before_src, before_dst, os.path.isfile(before_src)))
                move(before_src, before_dst)

                # print('{} => {} !! {}'.format(after_src, after_dst, os.path.isfile(after_src)))
                move(after_src, after_dst)

                split_file.write(datapoint)

    return split_mappings


def create_inference_dataset(TEMP_DATA_FOLDER, TARGET_DATA_FOLDER):
    print('starting inference')
    temp_before_directory = os.path.join(TEMP_DATA_FOLDER, "before").replace("\\","/")
    temp_after_directory = os.path.join(TEMP_DATA_FOLDER, "after").replace("\\","/")
    images_in_before_directory = [
        x for x in os.listdir(temp_before_directory) if x.endswith(".png")
    ]
    images_in_after_directory = [
        x for x in os.listdir(temp_after_directory) if x.endswith(".png")
    ]
    intersection = list(
        set(images_in_before_directory) & set(images_in_after_directory)
    )
    print('images:', intersection)

    inference_directory = os.path.join(TARGET_DATA_FOLDER, "inference").replace("\\","/")
    os.makedirs(inference_directory, exist_ok=True)

    inference_before_directory = os.path.join(inference_directory, "before").replace("\\","/")
    os.makedirs(inference_before_directory, exist_ok=True)

    inference_after_directory = os.path.join(inference_directory, "after").replace("\\","/")
    os.makedirs(inference_after_directory, exist_ok=True)

    for datapoint_name in intersection:
        before_image_src = os.path.join(temp_before_directory, datapoint_name).replace("\\","/")
        after_image_src = os.path.join(temp_after_directory, datapoint_name).replace("\\","/")

        before_image_dst = os.path.join(inference_before_directory, datapoint_name).replace("\\","/")
        after_image_dst = os.path.join(inference_after_directory, datapoint_name).replace("\\","/")
        print(before_image_dst, after_image_dst)
        move(before_image_src, before_image_dst)
        move(after_image_src, after_image_dst)


def create_version_file(version_number, TARGET_DATA_FOLDER, VERSION_FILE_NAME):
    with open(
        os.path.join(TARGET_DATA_FOLDER, VERSION_FILE_NAME).replace("\\","/"), "w+"
    ) as version_file:
        version_file.write("{0}".format(version_number))
    return version_number


def main():
    logging.basicConfig(
        handlers=[
            logging.FileHandler(os.path.join("", "run.log").replace("\\", "/")),
            logging.StreamHandler(sys.stdout),
        ],
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    logger.info("python {}".format(" ".join(sys.argv)))

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--version",
        type=str,
        default="0",
        help="set a version number to identify dataset",
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="input data path",
    )
    parser.add_argument(
        "--dest",
        type=str,
        required=True,
        help="input data path",
    )
    parser.add_argument(
        "--create-image-stamps",
        action="store_true",
        default=True,
        help="For each building shape, creates a before and after "
        "image stamp for the learning model, and places them "
        "in the approriate directory (train, validation, or test)",
    )
    args = parser.parse_args()

    # input
    ROOT_DIRECTORY = args.data

    BEFORE_FOLDER = os.path.join(ROOT_DIRECTORY, "pre-event").replace("\\", "/")
    AFTER_FOLDER = os.path.join(ROOT_DIRECTORY, "post-event").replace("\\", "/")

    GEOJSON_FILE = os.path.join(ROOT_DIRECTORY, "buildings.geojson").replace("\\", "/")

    # input
    VERSION_FILE_NAME = "VERSION"

    TARGET_DATA_FOLDER = os.path.join(args.dest).replace("\\", "/")
    os.makedirs(TARGET_DATA_FOLDER, exist_ok=True)

    # cache
    TEMP_DATA_FOLDER = os.path.join(TARGET_DATA_FOLDER, "temp").replace("\\", "/")
    os.makedirs(TEMP_DATA_FOLDER, exist_ok=True)

    LABELS_FILE = os.path.join(TEMP_DATA_FOLDER, "labels.txt").replace("\\", "/")


    logger.info("Reading source file: {}".format(GEOJSON_FILE))

    # Read in the main buildings shape file
    df = geopandas.read_file(GEOJSON_FILE).to_crs(epsg="4326")

    # Remove any empty building shapes
    number_of_all_datapoints = len(df)
    logger.info("Source file contains {} datapoints.".format(number_of_all_datapoints))
    df = df.loc[~df["geometry"].is_empty]
    number_of_empty_datapoints = number_of_all_datapoints - len(df)
    logger.info("Removed {} empty datapoints.".format(number_of_empty_datapoints))

    logger.info(
        "Creating dataset using {} datapoints.".format(
            len(df)
        )
    )

    if args.create_image_stamps:
        logger.info("Creating training dataset.")
        create_datapoints(df, ROOT_DIRECTORY, LABELS_FILE, TEMP_DATA_FOLDER)
        split_datapoints(LABELS_FILE, TARGET_DATA_FOLDER, TEMP_DATA_FOLDER)
        create_inference_dataset(TEMP_DATA_FOLDER, TARGET_DATA_FOLDER)
    else:
        logger.info("Skipping creation of training dataset.")

    logger.info(
        "Created a Caladrius Dataset at {}v{}".format(
            TARGET_DATA_FOLDER, create_version_file(args.version, TARGET_DATA_FOLDER, VERSION_FILE_NAME)
        )
    )


if __name__ == "__main__":
    main()
