# Collection of tools for Automated Damage Assessment 

This repo wraps two packages relevant for Automated Damage Assessment project:

- *neat_eo* - unofficial copy of a package for analysis of satellite imagery
- *ada_tools* - tools for pre- and post-processing of satellite image related data,
copy of https://github.com/jmargutt/ADA_tools

For further information on both packages, read their respective READMEs in each package's folder.

## Installation and usage
This repo is intended to be used to build a Docker image for usage in Azure Batch service 
(https://github.com/ondrejzacha/ada-azure-batch).

To build and push the docker image, run:
```bash
docker build -t ada510.azurecr.io/neo:latest .
docker push ada510.azurecr.io/neo:latest
```

Eventually change to match image referenced in [ada-azure-batch project](https://github.com/ondrejzacha/ada-azure-batch).

This build uses the `Dockerfile` file, `nvidia.Dockerfile` is an experiment including installation of necessary
nvidia / cuda packages.
