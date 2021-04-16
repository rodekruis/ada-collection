# ada-collection

Tools for Automated Mapping and Damage Assessment.

This repo wraps two packages:

- *abd_model* - forked from [automated-building-detection](https://github.com/rodekruis/automated-building-detection)
- *ada_tools* - tools for pre- and post-processing of remote sensing images and vector data

The damage assessment framework & model is at [caladrius:ada-0.1](https://github.com/rodekruis/caladrius/tree/ada-0.1) automatically installed via Docker ([caladrius.Dockerfile](https://github.com/rodekruis/ada-collection/blob/master/caladrius.Dockerfile)).

## Getting started

### Get pre-trained models and images
1. Download pre-trained building detection model.
2. Download pre-trained building damage classification model.
3. [OPTIONAL] pre- and post-disaster satellite images
```
    <workspace>
    ├── ...
    ├── images                 # satellite images
    │   ├── pre-event          # before the disaster
    │   └── post-event         # after the disaster
    └── ...
```
### Using Docker
1. Install [Docker](https://www.docker.com/get-started).
2. Download the [latest Docker Image](https://hub.docker.com/r/rodekruis/automated-building-detection)
```
docker pull rodekruis/ada-collection
```
3. Create a docker container and connect it to a local directory (`<path-to-your-workspace>`)
```
docker run --name ada-collection -dit -v <path-to-your-workspace>:/workdir --ipc=host --gpus all -p 5000:5000 rodekruis/ada-collection
```
4. Access the container
```
docker exec -it ada-collection bash
```

### Manual Setup
1. Install Python 3.7 and [pip](https://pypi.org/project/pip/)
2. Install [Anaconda](https://www.anaconda.com/products/individual)
3. Create and activate a new Anaconda environment
```
conda create --name abdenv python=3.7 
conda activate abdenv
```
4. From root directory, move to `ada_tools` and install
```
cd ada_tools
pip install .
```
5. Move to `abd_model` and install
```
cd ../abd_model
pip install .
```
5. Get [caladrius:ada-0.1](https://github.com/rodekruis/caladrius/tree/ada-0.1) (damage assessment framework) and install
```
git clone --branch ada-0.1 https://github.com/rodekruis/caladrius.git
cd caladrius
./caladrius_install.sh
```

## End-to-end example
1. Get satellite images of typhoon Mangkhut from [Maxar Open Data](https://www.maxar.com/open-data)
```
load-images --disaster typhoon-mangkhut --dest <workspace>/images
```
2. Prepare images for building detection
```
abd cover --raster <workspace>/images/pre-event/*.tif --zoom 17 --out <workspace>/abd/cover.csv
abd tile --raster <workspace>/images/pre-event/*.tif --zoom 17 --cover <workspace>/abd/cover.csv --out <workspace>/abd/images --format tif --no_web_ui --config ada-tools/config.toml
```
2. Detect buildings
```
abd predict --dataset <workspace>/abd --cover <workspace>/abd/cover.csv --checkpoint <workspace>/neat-fullxview-epoch75.pth --out <workspace>/abd/predictions --metatiles --keep_borders --config ada-tools/config.toml
```
3. Generate vector file with buildings and filter noise
```
abd vectorize --masks <workspace>/abd/predictions --type Building --out <workspace>/abd/buildings.geojson --config ada-tools/config.toml
filter-buildings --data <workspace>/abd/buildings.geojson --dest <workspace>/abd/buildings-clean.geojson
```
5. Prepare images for building damage classification
```
prepare-data --data <workspace>/images --buildings <workspace>/abd/buildings-clean.geojson --dest <workspace>/caladrius
```
4. Classify building damage
```
python caladrius/caladrius/run.py --run-name run --data-path <workspace>/caladrius --model-path <workspace>/best_model_wts.pkl --checkpoint-path <workspace>/caladrius/runs --output-type classification --inference
```
4. Generate vector file with buildings and damage labels
```
final-layer --builds <workspace>/abd/buildings-clean.geojson --damage <workspace>/caladrius/runs/run-input_size_32-learning_rate_0.001-batch_size_32/predictions/run-split_inference-epoch_001-model_inception-predictions.txt --out <workspace>/buildings-predictions.geojson --thresh 1
```
