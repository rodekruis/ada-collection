# ada-collection

Tools for Automated Mapping and Damage Assessment.

This repo wraps two packages:

- *abd_model* - forked from [automated-building-detection](https://github.com/rodekruis/automated-building-detection)
- *ada_tools* - tools for pre- and post-processing of remote sensing images and vector data

The damage assessment framework & model is at [caladrius:ada-0.1](https://github.com/rodekruis/caladrius/tree/ada-0.1) automatically installed via Docker ([caladrius.Dockerfile](https://github.com/rodekruis/ada-collection/blob/master/caladrius.Dockerfile)).

## Getting started

### Prerequisites
1. Download pre-trained building detection model.
2. Download pre-trained building damage classification model.
3. [OPTIONAL] Pre- and post-disaster satellite images
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
