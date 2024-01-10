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
# Have a good look at the file names of the sattelite images, they often correspond to geographical areas and can already tell you which pre and post images might overlap.
# Take into account that this might take some time. We are working with big files, downloading images and visualizing them in QGIS takes some time :) (is there a QGIS plugin to directly connect to Azure Blob Storage?)

# A common source for good satellite images would be Maxar. If they have images available, the first step would be to manually upload them to the datalake (divided in pre- and post-event) OR download them from Maxar open data
# 1. go to https://www.maxar.com/open-data
# 2. browse to the relevant event
# 3. copy the name of the event from the URL (e.g. "typhoon-mangkhut" from https://www.maxar.com/open-data/typhoon-mangkhut)
# 4. download the images with 
# `load-images --disaster typhoon-mangkhut --dest ~/training-data/typhoon-mangkhut`
# 5. The images are now uploaded to the datalake storage which is mounted to the VM
# 6. Usually the next step would be to inspect the images as described above. For now we have already prepared images of good quality of hurricane dorian on the VM. :):)
# 7. Have a look at the images in Micrsoft Azure Storage Explorer under adadatalakestorage > Blob Containers > training. Download the images and visualize them in QGIS

# Ccopy the prepared images from the datalake storage to the VM (processing is faster locally)
cp -r ~/training-data/hurricane-dorian ~/hurricane-dorian
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Getting building footprints
# If you haven't already, download the images from the datalake to your local machine. 
# Visualize them with QGIS and check if OpenStreetMap (OSM) buildings are good enough;
# 1. Go to plugins
# 2. Open the QuickOSM plugin
# 3. Get all buildings (key=building, value=empty) in the area of the post sattelite images. 
#    You might first have to extraxt the extend of all the pre or post images, ask a QGIS colleague if you do not know how. :)

# If OSM buildings are good enough, download OSM buildings with
# 1. navigate to hurrican dorian folder: `cd ~/hurricane-dorian`
# 2. run `get-osm-buildings --raster pre-event/1050010012BCAE00-pre-clipped.tif`

# if not, check Google buildings. 
# https://sites.research.google/open-buildings/#download
# 1. Download the correct file, unpack it and open the csv file in QGIS

# if not, check Microsoft buildings
# Follow instructions given at:
# https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/examples/example_building_footprints.ipynb

# if still not, we have to run the building detection ourselves. We will assume for now that we actually do find good buildings and will not go into the automated building detection.

# For now we will continue with the OSM buildings that we already downloaded to the VM
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Run ADA
# prepare data for caladrius (damage classification model)
cd ~/hurricane-dorian
prepare-data --data . --buildings buildings.geojson --dest caladrius

# This code loops over all buildings, then checks if the building location is both in the pre and post images and if so crops both the pre and post event building at the building shape.
# This means for every building we get a cropped pre and post image combination.
# Finally, these image combinations are divided over a train, test, validation and inference set.
# Have a good look at the logging while the code is running.
# When it is done, check out the newly created caladrius folder (e.g. ls caladrius, ls caladrius/inference etc.)

# run caladrius
conda activate cal
CUDA_VISIBLE_DEVICES="0" python ~/caladrius/caladrius/run.py --run-name run --data-path caladrius --model-type attentive --model-path ~/training-data/caladrius_att_effnet4_v1.pkl --checkpoint-path caladrius/runs --batch-size 2 --number-of-workers 4 --classification-loss-type f1 --output-type classification --inference

# prepare the final vector file with building polygons and caladrius' predictions
conda activate base
final-layer --builds buildings.geojson --damage caladrius/runs/run-input_size_32-learning_rate_0.001-batch_size_2/predictions/run-split_inference-epoch_001-model_attentive-predictions.txt --out buildings-predictions.geojson

# copy the results back to the datalake datalake, download them locally and visualize with QGIS
cp buildings-predictions.geojson ~/training-data/hurricane-dorian/

# Do not forget to inspect the results. Look at some predictions of the model and check if they make sense by looking at the predicted building on the post images
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Shut down

# unmount the datalake storage
sudo fusermount -u training-data
````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````````
## Final notes
# We have run every separate step manually now with a small amount of data. When running ADA for real the datasets will be much bigger and processing them takes longer. 
# Therefore, we have also set up a notebook which use Azure Batch to run multiple processes at the same time. For more info, have a look at the notebooks at https://github.com/rodekruis/ada-azure-batch
