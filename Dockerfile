FROM python:3.8-slim

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN apt-get update && \
	apt-get install -y build-essential gdal-bin python-gdal libgdal-dev && \
	pip install GDAL==2.4.0

WORKDIR /neo
ADD . .
RUN pip install .
