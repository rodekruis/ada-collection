FROM nvidia/cuda:12.2.0-base-ubuntu22.04

RUN apt-get update && \
	apt-get install -y python3 python3-pip && \
	apt-get install python-is-python3

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN deps='build-essential curl gdal-bin libgdal-dev kmod wget apache2 libopencv-dev python3-opencv' && \
	apt-get update && \
	apt-get install -y $deps

RUN pip install --upgrade pip && \
	pip install GDAL==$(gdal-config --version)

# install conda
ENV HOME="/root"
ENV PATH="$HOME/conda/bin:$PATH"
RUN mkdir $HOME/.conda &&\
    curl -sL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh > $HOME/miniconda.sh &&\
    chmod 0755 $HOME/miniconda.sh &&\
    /bin/bash $HOME/miniconda.sh -b -p $HOME/conda &&\
    rm $HOME/miniconda.sh &&\
    $HOME/conda/bin/conda update -n base -c defaults conda &&\
    conda init

# install ada_tools in env base
WORKDIR /ada_tools
ADD ada_tools .
RUN pip install .

# install abd in env abd
RUN conda create -y -n abd python=3.7
SHELL ["conda", "run", "-n", "abd", "/bin/bash", "-c"]
WORKDIR /abd
ADD abd_model .
RUN pip install .

# clone caladrius repo
WORKDIR /
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl vim less
RUN git clone --branch ada-0.1 https://github.com/rodekruis/caladrius.git

# install caladrius in env cal
WORKDIR /caladrius
RUN /bin/bash caladrius_install.sh
WORKDIR /

# go back to env base
SHELL ["conda", "run", "-n", "base", "/bin/bash", "-c"]

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8