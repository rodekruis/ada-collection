# data_processing
scripts to download/transform pre- and post-disaster images

1. get images from Maxar
```
Usage: get_images_Maxar.py [OPTIONS]

Options:
  --disaster TEXT    name of the disaster
  --dest TEXT        destination folder
  --maxpre INTEGER   max number of pre-disaster images
  --maxpost INTEGER  max number of post-disaster images
  --help             Show this message and exit.
```
2. filter images
```
Usage: filter_images.py [OPTIONS]

Options:
  --mosaic TEXT   merge overlapping rasters
  --data TEXT     original images
  --dest TEXT     destination folder
  --ntl TEXT      filter pre-event images by night-time lights (yes/no)
  --bbox TEXT     filter pre-event images by bounding box (CSV format)
  --country TEXT  country
  --help          Show this message and exit.
  ```
3. transform for damage classification (after building detection)
```
usage: prepare_data_for_caladrius.py [-h] [--version VERSION] --data DATA
                                     --dest DEST [--create-image-stamps]

optional arguments:
  -h, --help            show this help message and exit
  --version VERSION     set a version number to identify dataset (default: 0)
  --data DATA           input data path (default: None)
  --dest DEST           output data path (default: None)
  --create-image-stamps
                        For each building shape, creates a before and after
                        image stamp for the learning model, and places them in
                        the approriate directory (train, validation, or test)
                        (default: True)
```
