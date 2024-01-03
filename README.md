# ada-collection

Tools for Automated Mapping and Damage Assessment.

This repo wraps two packages:

- *abd_model* - forked from [automated-building-detection](https://github.com/rodekruis/automated-building-detection)
- *ada_tools* - tools for pre- and post-processing of remote sensing images and vector data

The damage assessment framework & model is at [caladrius:ada-0.1](https://github.com/rodekruis/caladrius/tree/ada-0.1) automatically installed via Docker ([caladrius.Dockerfile](https://github.com/rodekruis/ada-collection/blob/master/caladrius.Dockerfile)).

> [!IMPORTANT]  
> This readme is intended for the general public.
>
> **For 510-specific instructions during emergencies, see the [ADA SOP](https://github.com/rodekruis/ada-collection/blob/master/docs/SOP.md).**

## Getting started

### Get pre-trained models and images
1. Download pre-trained building detection model: [neat-fullxview-epoch75.pth](https://drive.google.com/file/d/1pMkrBjdpmOgT_MzqZSLHvmQDsZNM_Lwo/view?usp=sharing): 
  * architecture: AlbuNet ([U-Net-like](https://arxiv.org/abs/1505.04597) encoder-decoder with a ResNet, ResNext or WideResNet encoder)
  * training: [xBD dataset](https://arxiv.org/pdf/1911.09296.pdf), 75 epochs
  * performance: [IoU](https://en.wikipedia.org/wiki/Jaccard_index) 0.79, [MCC](https://en.wikipedia.org/wiki/Matthews_correlation_coefficient) 0.75
2. Download pre-trained building damage classification model: [caladrius_att_effnet4_v1.pkl](https://drive.google.com/file/d/1a_yQgHSvcatNp0KUeHmDtvdFUDJffOLq/view?usp=sharing)
  * architecture: pseudo-[siamese network](http://papers.nips.cc/paper/769-signature-verification-using-a-siamese-time-delay-neural-network) with two [ImageNet](https://ieeexplore.ieee.org/abstract/document/5206848)
pre-trained [EffNet-B4](https://arxiv.org/pdf/1905.11946.pdf) models + attention
  * training: [xBD dataset](https://arxiv.org/pdf/1911.09296.pdf), 75 epochs
  * performance: up to [F1 score](https://en.wikipedia.org/wiki/F-score) 0.79, [AUC](https://en.wikipedia.org/wiki/Receiver_operating_characteristic) 0.984 (see [performance paper](https://www.mdpi.com/2072-4292/12/17/2839))
3. [OPTIONAL] pre- and post-disaster satellite images

Your workspace should then look like
```
    <workspace>
    ├── ...
    ├── neat-fullxview-epoch75.pth    # pre-trained building detection model
    ├── caladrius_att_effnet4_v1.pkl  # pre-trained building damage classification model
    ├── images                        # satellite images
    │   ├── pre-event                 # before the disaster
    │   └── post-event                # after the disaster
    └── ...
```
### Using Docker
1. Install [Docker](https://www.docker.com/get-started).
2. Download the [latest Docker Image](https://hub.docker.com/r/rodekruis/ada-collection)
```
docker pull jmargutti/ada-collection
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
1. Install Python 3.7 and [pip](https://pypi.org/project/pip/).
2. Install [Anaconda](https://www.anaconda.com/products/individual).
3. Create and activate a new Anaconda environment.
```
conda create --name abdenv python=3.7 
conda activate abdenv
```
4. From root directory, move to `ada_tools` and install
```
cd ada_tools
pip install .
```
Note: Make sure libboost/boost is installed. 

5. Move to `abd_model` and install
```
cd ../abd_model
pip install .
```
6. Get [caladrius:ada-0.1](https://github.com/rodekruis/caladrius/tree/ada-0.1) (damage assessment framework) and install
```
git clone --branch ada-0.1 https://github.com/rodekruis/caladrius.git
cd caladrius
./caladrius_install.sh
```

## End-to-end example
1) Get satellite images of typhoon Mangkhut from [Maxar Open Data](https://www.maxar.com/open-data)
```
load-images --disaster typhoon-mangkhut --dest <workspace>/images
```
* Alternatively, load images from Azure blob storage
```
load-images-azure --disaster typhoon-mangkhut --dest <workspace>/images
```
* Set the `CONNECTION_STRING` and `CONTAINER_NAME` environmental variables corresponding to your Azure account

2) Prepare images for building detection
```
abd cover --raster <workspace>/images/pre-event/*.tif --zoom 17 --out <workspace>/abd/cover.csv
abd tile --raster <workspace>/images/pre-event/*.tif --zoom 17 --cover <workspace>/abd/cover.csv --out <workspace>/abd/images --format tif --no_web_ui --config ada-tools/config.toml
```
3) Detect buildings
```
abd predict --dataset <workspace>/abd --cover <workspace>/abd/cover.csv --checkpoint <workspace>/neat-fullxview-epoch75.pth --out <workspace>/abd/predictions --metatiles --keep_borders --config ada-tools/config.toml
```
4) Generate vector file with buildings and filter noise
```
abd vectorize --masks <workspace>/abd/predictions --type Building --out <workspace>/abd/buildings.geojson --config ada-tools/config.toml
filter-buildings --data <workspace>/abd/buildings.geojson --dest <workspace>/abd/buildings-clean.geojson
```
5) Prepare images for building damage classification
```
prepare-data --data <workspace>/images --buildings <workspace>/abd/buildings-clean.geojson --dest <workspace>/caladrius
```
6) Classify building damage
```
CUDA_VISIBLE_DEVICES="0" python caladrius/caladrius/run.py --run-name run --data-path <workspace>/caladrius --model-type attentive --model-path <workspace>/caladrius_att_effnet4_v1.pkl --checkpoint-path <workspace>/caladrius/runs --batch-size 2 --classification-loss-type f1 --output-type classification --inference
```
7) Generate vector file with buildings and damage labels
```
final-layer --builds <workspace>/abd/buildings-clean.geojson --damage <workspace>/caladrius/runs/run-input_size_32-learning_rate_0.001-batch_size_32/predictions/run-split_inference-epoch_001-model_inception-predictions.txt --out <workspace>/buildings-predictions.geojson --thresh 1
```
8) Take your favorite [GIS application](https://en.wikipedia.org/wiki/Geographic_information_system) and visualize `<workspace>/buildings-predictions.geojson` in a nice map
