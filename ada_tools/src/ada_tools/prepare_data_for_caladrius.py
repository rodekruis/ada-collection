import argparse
import datetime
import logging
import os
import sys
from shutil import move

import geopandas
import numpy as np
import rasterio
import rasterio.features
import rasterio.mask
import rasterio.warp
from PIL import Image
from shapely.geometry import box
# from PIL import Image
from tqdm import tqdm

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
NONZERO_PIXEL_THRESHOLD = 0.7


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


def get_image_list(root_folder, ROOT_FILENAME_PRE, ROOT_FILENAME_POST):
    image_list = []
    for path, subdirs, files in os.walk(root_folder):
        for name in files:
            if "pre-event" in path:
                if ROOT_FILENAME_PRE != "" and ROOT_FILENAME_PRE not in name:
                    continue
            elif "post-event" in path:
                if ROOT_FILENAME_POST != "" and ROOT_FILENAME_POST not in name:
                    continue
            if name.lower().endswith(".tif"):
                image_list.append(os.path.join(path, name).replace("\\", "/"))
    return image_list


def save_image(image, transform, out_meta, image_path):
    image = np.swapaxes(image, 0, 2)
    image = np.swapaxes(image, 0, 1)
    if image.max() > 255.:
        image = image * 255. / image.max()
    try:
        im = Image.fromarray(image)
    except TypeError:
        image = image.astype(np.uint8)
        im = Image.fromarray(image)
    im.save(image_path)
    return image_path


def get_image_path(geo_image_path, object_id, TEMP_DATA_FOLDER):
    filename = "{}.png".format(object_id)

    image_path = geo_image_path.split("/")

    sub_folder = "before" if "pre-event" in image_path else "after"
    image_path = os.path.join(TEMP_DATA_FOLDER, sub_folder).replace("\\", "/")

    os.makedirs(image_path, exist_ok=True)

    image_path = os.path.join(image_path, filename).replace("\\", "/")

    return image_path


def match_geometry(image_path, geo_image_file, geometry):
    try:
        image, transform = rasterio.mask.mask(geo_image_file, geometry, crop=True)
        out_meta = geo_image_file.meta.copy()
    except ValueError:
        return False
    try:
        good_pixel_fraction = np.count_nonzero(image) / image.size
        if len(image.shape) < 3:
            logging.error("image has less than 3 bands")
            return False
        if image.shape[0] > 3:
            image = image[:3, :, :]
        if (
                np.sum(image) > 0
                and good_pixel_fraction >= NONZERO_PIXEL_THRESHOLD
        ):
            save_image(image, transform, out_meta, image_path)
            return True
        else:
            logging.info(
                f"something's wrong with the image: {np.sum(image)}, {good_pixel_fraction}")
            return False
    except ValueError:
        return False


def create_datapoints(df, ROOT_DIRECTORY, ROOT_FILENAME_PRE, ROOT_FILENAME_POST, LABELS_FILE, TEMP_DATA_FOLDER):
    start_time = datetime.datetime.now()

    logger.info("Creating datapoints.")
    logger.info("Feature Size {}".format(len(df)))

    image_list = get_image_list(ROOT_DIRECTORY, ROOT_FILENAME_PRE, ROOT_FILENAME_POST)

    # logger.info(len(image_list)) # 319
    df['is_building_processed_pre'] = False
    df['is_building_processed_post'] = False

    with open(LABELS_FILE, "w+") as labels_file:
        for pre_or_post in ['pre', 'post']:
            image_list_pp = [image for image in image_list if f'{pre_or_post}-event' in image]
            print(f'starting {pre_or_post}-event')
            count = 0
            for geo_image_path in tqdm(image_list_pp):
                with rasterio.open(geo_image_path) as geo_image_file:
                    try:
                        df = df.to_crs(geo_image_file.crs)
                        crs = geo_image_file.crs
                    except:
                        df = df.to_crs("EPSG:4326")
                        crs = "EPSG:4326"
                    print(f'analyzing image {geo_image_path} (CRS {crs})')
                    df['is_building_in_image'] = df.within(box(*geo_image_file.bounds))
                    print(f'buildings found in image: {len(df[df["is_building_in_image"]])}')
                    if not df['is_building_in_image'].any():
                        logging.info(f"image contains no building, skipping")
                        continue
                    df_in_image = df[(df['is_building_in_image'] == True) &
                                     (df[f'is_building_processed_{pre_or_post}'] == False)]
                    print(f'of which not yet processed: {len(df_in_image)}')
                    for index, row in df_in_image.iterrows():  # tqdm(df_in_image.iterrows(), total=df_in_image.shape[0]):

                        # identify data point
                        if "OBJECTID" in row.keys():
                            object_id = row["OBJECTID"]
                        else:
                            object_id = index

                        image_path = get_image_path(geo_image_path, object_id, TEMP_DATA_FOLDER)

                        if os.path.exists(image_path):
                            continue

                        bounds = row["geometry"].bounds
                        geometry = makesquare(*bounds)

                        save_success = match_geometry(
                            image_path, geo_image_file, geometry
                        )
                        if save_success:
                            count = count + 1
                        df.at[index, f'is_building_processed_{pre_or_post}'] = True
            logger.info(f"Total buildings successfully saved for {pre_or_post}-event: {count}")

    delta = datetime.datetime.now() - start_time
    logger.info("create_datapoints completed in {}".format(delta))


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

        split_filepath = os.path.join(TARGET_DATA_FOLDER, split).replace("\\", "/")
        os.makedirs(split_filepath, exist_ok=True)

        split_labels_file = os.path.join(split_filepath, "labels.txt").replace("\\", "/")

        split_before_directory = os.path.join(split_filepath, "before").replace("\\", "/")
        os.makedirs(split_before_directory, exist_ok=True)

        split_after_directory = os.path.join(split_filepath, "after").replace("\\", "/")
        os.makedirs(split_after_directory, exist_ok=True)

        with open(split_labels_file, "w+") as split_file:
            for datapoint in tqdm(split_mappings[split]):
                datapoint_name = datapoint.split(" ")[0]

                before_src = os.path.join(TEMP_DATA_FOLDER, "before", datapoint_name).replace("\\", "/")
                after_src = os.path.join(TEMP_DATA_FOLDER, "after", datapoint_name).replace("\\", "/")

                before_dst = os.path.join(split_before_directory, datapoint_name).replace("\\", "/")
                after_dst = os.path.join(split_after_directory, datapoint_name).replace("\\", "/")

                move(before_src, before_dst)

                move(after_src, after_dst)

                split_file.write(datapoint)

    return split_mappings


def create_inference_dataset(TEMP_DATA_FOLDER, TARGET_DATA_FOLDER):
    logger.info('Creating inference dataset.')
    temp_before_directory = os.path.join(TEMP_DATA_FOLDER, "before").replace("\\", "/")
    temp_after_directory = os.path.join(TEMP_DATA_FOLDER, "after").replace("\\", "/")
    images_in_before_directory = [
        x for x in os.listdir(temp_before_directory) if x.endswith(".png")
    ]
    if len(images_in_before_directory) == 0:
        raise RuntimeError("no pre-event images of buildings")
    images_in_after_directory = [
        x for x in os.listdir(temp_after_directory) if x.endswith(".png")
    ]
    if len(images_in_after_directory) == 0:
        raise RuntimeError("no post-event images of buildings")
    intersection = list(
        set(images_in_before_directory) & set(images_in_after_directory)
    )
    if len(intersection) == 0:
        raise RuntimeError("no corresponding images pre- and post-disaster")

    n_img_to_rm = len(list(set(images_in_before_directory) - set(images_in_after_directory))) + \
                  len(list(set(images_in_after_directory) - set(images_in_before_directory)))

    logger.info(f'Images found in both pre- and post-event: {len(intersection)} (out of {len(intersection)+n_img_to_rm})')

    logger.info(f'Removing {n_img_to_rm} non-overlapping images')
    for image in tqdm(list(set(images_in_before_directory) - set(images_in_after_directory))):
        os.remove(os.path.join(temp_before_directory, image))
    for image in tqdm(list(set(images_in_after_directory) - set(images_in_before_directory))):
        os.remove(os.path.join(temp_after_directory, image))

    os.rename(TEMP_DATA_FOLDER, os.path.join(TARGET_DATA_FOLDER, "inference").replace("\\", "/"))

    # inference_directory = os.path.join(TARGET_DATA_FOLDER, "inference").replace("\\", "/")
    # os.makedirs(inference_directory, exist_ok=True)
    #
    # inference_before_directory = os.path.join(inference_directory, "before").replace("\\", "/")
    # os.makedirs(inference_before_directory, exist_ok=True)
    #
    # inference_after_directory = os.path.join(inference_directory, "after").replace("\\", "/")
    # os.makedirs(inference_after_directory, exist_ok=True)
    #
    # for datapoint_name in tqdm(intersection):
    #     before_image_src = os.path.join(temp_before_directory, datapoint_name).replace("\\", "/")
    #     after_image_src = os.path.join(temp_after_directory, datapoint_name).replace("\\", "/")
    #
    #     before_image_dst = os.path.join(inference_before_directory, datapoint_name).replace("\\", "/")
    #     after_image_dst = os.path.join(inference_after_directory, datapoint_name).replace("\\", "/")
    #     move(before_image_src, before_image_dst)
    #     move(after_image_src, after_image_dst)


def create_version_file(version_number, TARGET_DATA_FOLDER, VERSION_FILE_NAME):
    with open(
            os.path.join(TARGET_DATA_FOLDER, VERSION_FILE_NAME).replace("\\", "/"), "w+"
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
        "--reproject",
        type=str,
        default="",
        help="force reprojection of buildings to given CRS"
    )
    parser.add_argument(
        "--datapre",
        type=str,
        default="",
        help="filter pre-event input data by string",
    )
    parser.add_argument(
        "--datapost",
        type=str,
        default="",
        help="filter post-event input data by string",
    )
    parser.add_argument(
        "--buildings",
        type=str,
        required=True,
        help="vector file with buildings",
    )
    parser.add_argument(
        "--dest",
        type=str,
        required=True,
        help="output data path",
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
    ROOT_FILENAME_PRE = args.datapre
    ROOT_FILENAME_POST = args.datapost

    GEOJSON_FILE = args.buildings

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
    if len(df) == 0:
        raise RuntimeError("no buildings detected in pre-disaster image")

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

    if args.reproject != "":
        df = df.to_crs(args.reproject)

    if args.create_image_stamps:
        create_datapoints(df, ROOT_DIRECTORY, ROOT_FILENAME_PRE, ROOT_FILENAME_POST, LABELS_FILE, TEMP_DATA_FOLDER)
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
