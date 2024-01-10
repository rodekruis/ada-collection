## Setup
# go do the resource group ada-training
https://portal.azure.com/#@rodekruis.onmicrosoft.com/resource/subscriptions/b2d243bd-7fab-4a8a-8261-a725ee0e3b47/resourcegroups/510global-ada-training

# Start your VM (change the name at the end of the url to your name)
https://portal.azure.com/#@rodekruis.onmicrosoft.com/resource/subscriptions/b2d243bd-7fab-4a8a-8261-a725ee0e3b47/resourceGroups/510global-ada-training/providers/Microsoft.Compute/virtualMachines/NC4as-T4-V3-Bouke

# Connect to the VM:
1. navigate to bastion
2. enter credentials from bitwarden
3. connection to the vm will now open \in another browser tab. Make sure pop-ups are not blocked by your browser

# mount the datalake storage (let's look into blobfuse2)
sudo blobfuse training-data --tmp-path=/mnt/resource/blobfusetmp  --config-file=blobfuse/fuse_connection_adatraining.cfg -o attr_timeout=240 -o entry_timeout=240 -o negative_timeout=120 -o allow_other

# have a look at the data
1. run `ls`
2. the training-data folder should now be highlighted
3. run `cd training-data`
4. run 'ls'
5. all datat in the datalake storage is now available within the vm
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Getting Images
# Next step would be to check if there are satellite images available that cover the relevant area, pre and post images overlap and that are of sufficient quality. 
# This can be quiet a hassle since we are working with big files here. Downloading the images and visualizing them in QGIS is a lot of work!! (is there a QGIS plugin to directly connect to Azure Blob Storage)?
# Have a good look at the file names of the satellite images, they often correspond to geographical areas and can already tell you which pre and post images might overlap.
# Again, take into account that this might actually take some time.

# A common source for good satellite images would be Maxar. If they have images available, the first step would be to manually upload them to the datalake (divided in pre- and post-event) OR download them from Maxar open data
# 1. go to https://www.maxar.com/open-data
# 2. browse to the relevant event
# 3. copy the name of the event from the URL (e.g. "typhoon-mangkhut" from https://www.maxar.com/open-data/typhoon-mangkhut)
# 4. download the images with 
# `load-images --disaster typhoon-mangkhut --dest ~/training-data/typhoon-mangkhut`
# 5. The images are now uploaded to the datalake storage which is mounted to the VM
# 6. Usually the next step would be to inspect the images as described above. For now we have already prepared images of good quality. :):)

# Then copy images from the datalake storage to the VM (processing is faster locally)
cp -r ~/training-data/hurricane-dorian ~/hurricane-dorian
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Getting building footprints
# If you haven't already, download the images from the datalake to your local machine. 
# Visualize them with QGIS and check if OpenStreetMap (OSM) buildings are good enough;
# 1. ...
# 2. ...

# If OSM buildings are good enough, download OSM buildings with
# 1. navigate to hurrican dorian folder: `cd ~/hurricane-dorian`
# 2. run `get-osm-buildings --raster pre-event/1050010012BCAE00-pre-clipped.tif`

# if not, check Google buildings
# https://sites.research.google/open-buildings/#download

# if not, check Microsoft buildings
# https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/examples/example_building_footprints.ipynb
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Run ADA
# prepare data for caladrius (damage classification model)
cd ~/hurricane-dorian
prepare-data --data . --buildings buildings.geojson --dest caladrius

# run caladrius
conda activate cal
CUDA_VISIBLE_DEVICES="0" python ~/caladrius/caladrius/run.py --run-name run --data-path caladrius --model-type attentive --model-path ~/training-data/caladrius_att_effnet4_v1.pkl --checkpoint-path caladrius/runs --batch-size 2 --number-of-workers 4 --classification-loss-type f1 --output-type classification --inference

# prepare the final vector file with building polygons and caladrius' predictions
conda activate base
final-layer --builds buildings.geojson --damage caladrius/runs/run-input_size_32-learning_rate_0.001-batch_size_2/predictions/run-split_inference-epoch_001-model_attentive-predictions.txt --out buildings-predictions.geojson

# copy it back on the datalake, download it locally and visualize it with QGIS
cp buildings-predictions.geojson ~/training-data/hurricane-dorian/
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Optionally: create map
# ...
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Shut down
# unmount the datalake storage
sudo fusermount -u training-data
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Final notes
# We have run everything on a VM now. .... Can also use Azure Batch ....
