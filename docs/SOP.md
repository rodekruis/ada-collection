# ADA Standard Operating Procedures
These Standard Operating Procedures (SOP) are meant for 510 to use ADA during emergencies.

## Should I run ADA?
* There **must** be a clear request by the IFRC SIMS/IM Coordinator - in case of international respone - or by its NS counterpart, because we want this analysis to be useful and used.
* The relevant agencies - [Copernicus](https://emergency.copernicus.eu/mapping/list-of-activations-rapid), [UNOSAT](https://unosat.org/products/), or [others](https://data.humdata.org/search?q=damage+assessment) - **must not** be already producing damage assessments for this emergency, or there must be a clear gap in terms of spatial coverage of those assessments, because we don't want to duplicate efforts.
* ...

## Can I run ADA?
* High-resolution (<0.6 m/pixel) optical satellite imagery of the affected area, both pre- and post-disaster, **must** be available.
* The pre- and post-disaster imagery **must** spatially overlap, since ADA needs both images for each building.
* There **should** be building information (polygons) already available by [OpenStreetMap](https://www.openstreetmap.org/), [Microsoft](https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/examples/example_building_footprints.ipynb), or [Google](https://sites.research.google/open-buildings/#download). 
  * if not, buildings can be detected automatically using [ABD](https://github.com/rodekruis/ada-collection/tree/master/abd_model), but the quality of the results will strongly depend on building density, being lower for densely built-up areas.

> [!TIP]
> You can check the extent and overlap of images from Maxar Open data using [opengeos/maxar-open-data](https://github.com/opengeos/maxar-open-data).

## How do I run ADA?

### Prerequisites
1. Access to the BitWarden collection `Damage Assessment`
2. Access to the resource group `510Global-ADA` with role `Contributor` or higher
3. [QGIS](https://www.qgis.org/en/site/index.html) installed locally

### 1. Get the imagery
The first step is to load the satellite imagery in the container `operations` of the datalake storage `adadatalakestorage`. 

Login into the VM `510ada-NC8asT4` using SSH or Bastion (credentials in BitWarden). 

Mount the container on the directory `data` with
```commandline
sudo mkdir /mnt/resource/blobfusetmp -p
sudo blobfuse data --tmp-path=/mnt/resource/blobfusetmp  --config-file=blobfuse/fuse_connection_adadatalake.cfg -o attr_timeout=240 -o entry_timeout=240 -o negative_timeout=120 -o allow_other
```

If you received a link to the images (e.g. from another agency), simply download and extract it in `data`.
```commandline
mkdir ~/data/<event-name>
cd ~/data/<event-name>
wget <link-to-my-images>
```

If you already have the images on your local machine, simply upload them to the data lake storage, in the `operations` container.

> [!TIP]
> Use [Azure Storage Explorer](https://azure.microsoft.com/en-us/products/storage/storage-explorer) to upload and organize images if you're not familiar with command line.

> [!CAUTION]
> Make sure that the images are divided in two sub-folders called `pre-event` and `post-event`.

If you first need to download the images from Maxar
  1. go to [Maxar Geospatial Platform (MGP) Xpress](https://xpress.maxar.com)
  2. log in (credentials are in BitWarden)
  3. browse to the relevant event
  4. download the images one by one

DEPRECATED: for old events (pre-2023) there is a script that lists all images from the old [Maxar Open Data Portal](https://www.maxar.com/open-data). To use that,
  1. go to [Maxar Open Data Portal](https://www.maxar.com/open-data)
  2. browse to the relevant event
  6. copy the name of the event from the URL (e.g. "typhoon-mangkhut" from https://www.maxar.com/open-data/typhoon-mangkhut)
  7. download the images with 
  ```commandline
  load-images --disaster <event-name> --dest ~/data/<event-name>
  ```

### 2. Check the imagery
Verify that the imagery is
* optical (RGB), or multi-spectral with optical
* high-resolution (<0.6 m/pixel)
* cloud-free
* and that building damage is visible. Can be done locally by downloading the images and visualizing them with QGIS.

### 3. Get building footprint
The second step is to get a vector file (.geojson) with the buildings in the affected area.
* Check if OpenStreetMap (OSM) buildings are good enough; if so, download them for each image with
```commandline
run get-osm-buildings --raster ~/data/<event-name>/pre-event/<image-name>.tif
```

* if OSM is not good enough, check [Google buildings](https://colab.research.google.com/github/google-research/google-research/blob/master/building_detection/open_buildings_download_region_polygons.ipynb)
* if also Google is not good enough, check [Microsoft buildings](https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/examples/example_building_footprints.ipynb)
* if also Microsoft is not good enough, run [automated-building-detection](https://github.com/rodekruis/automated-building-detection?tab=readme-ov-file#end-to-end-example)
* place the output `buildings.geojson` in `~/data/<event-name>`

### 4. Run ADA
* [OPTIONAL] Copy images from the datalake storage to the VM (processing is faster locally)
```
cp -r ~/data/<event-name> ~/<event-name>
```
* Prepare data for caladrius (damage classification model)
```
cd ~/<event-name>
prepare-data --data . --buildings buildings.geojson --dest caladrius
```
* Run caladrius
```
conda activate cal
CUDA_VISIBLE_DEVICES="0" python ~/caladrius/caladrius/run.py --run-name run --data-path caladrius --model-type attentive --model-path ~/data/caladrius_att_effnet4_v1.pkl --checkpoint-path caladrius/runs --batch-size 2 --number-of-workers 4 --classification-loss-type f1 --output-type classification --inference
```
* Prepare the final vector file with building polygons and caladrius' predictions
```
conda activate base
final-layer --builds buildings.geojson --damage caladrius/runs/run-input_size_32-learning_rate_0.001-batch_size_2/predictions/run-split_inference-epoch_001-model_attentive-predictions.txt --out buildings-predictions.geojson
```
* Copy it back on the datalake, download it locally and visualize it with QGIS
```
cp buildings-predictions.geojson ~/data/<event-name>
```

### 5. Interpret and communicate about ADA
* This is an AI-based assessment: it is not perfect, but it is fast. 
* The **expected accuracy** of ADA on new disasters is **around 60-70%**: this means that **3 out of 5** buildings should be correctly assessed. Make sure to communicate this clearly with your end users before sharing the results.
* To be sure, take 20/50/100 random buildings and check that at least 15/30/60 buildings were correctly assessed.
  * If this the case, manually correct the most obvious mistakes (if any) and proceed to create a map. 
  * If this is not the case, it is probably connected with the quality of the images: go back to step #2 and repeat.
* Create a map and share; please re-use the disclaimers and style from previous examples:
  * [Libya Floods 2023](https://drive.google.com/file/d/1QCCgf2wcQDeNCThPR9hckTXJEuZZyObD/view?usp=sharing)
  * [Turkey/Syria Earthquake 2023](https://drive.google.com/file/d/1bRnv5Gu1Bx5X2EB2euYDcrNzu9Y-50Rm/view?usp=sharing)
