FROM nvidia/cuda:10.2-runtime-ubuntu18.04

RUN apt-get update && \
	apt-get install -y python3-pip && \
	ln -sfn /usr/bin/python3.6 /usr/bin/python && \
	ln -sfn /usr/bin/pip3 /usr/bin/pip

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN deps='build-essential gdal-bin python-gdal libgdal-dev kmod wget apache2' && \
	apt-get update && \
	apt-get install -y $deps

RUN pip install --upgrade pip && \
	pip install GDAL==$(gdal-config --version)

WORKDIR /abd
ADD abd_model .
RUN pip install .

WORKDIR /ada_tools
ADD ada_tools .
RUN pip install . && pip install torchvision

# clone caladrius repo
WORKDIR /
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl vim less
RUN git clone --branch ada-0.1 https://github.com/rodekruis/caladrius.git
# install conda
ENV HOME="/root"
ENV PATH="$HOME/conda/bin:$PATH"
RUN mkdir $HOME/.conda &&\
    curl -sL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh > $HOME/miniconda.sh &&\
    chmod 0755 $HOME/miniconda.sh &&\
    /bin/bash $HOME/miniconda.sh -b -p $HOME/conda &&\
    rm $HOME/miniconda.sh &&\
    $HOME/conda/bin/conda update -n base -c defaults conda

# install caladrius
WORKDIR /caladrius
RUN /bin/bash caladrius_install.sh
WORKDIR /

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8