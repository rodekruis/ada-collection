# go do the resource group ada-training
https://portal.azure.com/#@rodekruis.onmicrosoft.com/resource/subscriptions/b2d243bd-7fab-4a8a-8261-a725ee0e3b47/resourcegroups/510global-ada-training

# Start your VM
https://portal.azure.com/#@rodekruis.onmicrosoft.com/resource/subscriptions/b2d243bd-7fab-4a8a-8261-a725ee0e3b47/resourceGroups/510global-ada-training/providers/Microsoft.Compute/virtualMachines/NC4as-T4-V3-Bouke

# Connect > Connect via Bastion

# mount the datalake storage
sudo blobfuse training-data --tmp-path=/mnt/resource/blobfusetmp  --config-file=blobfuse/fuse_connection_adatraining.cfg -o attr_timeout=240 -o entry_timeout=240 -o negative_timeout=120 -o allow_other

# in this training, we prepared the images for you. In real life, you need to manually upload them to the datalake OR download them from Maxar open data
# load-images --disaster typhoon-mangkhut --dest training-data/typhoon-mangkhut

# copy images on the VM (processing is faster locally)
cp -r training-data/hurricane-dorian hurricane-dorian

# check on QGIS if OSM is good enough; if yes, download them with
cd ~/hurricane-dorian
get-osm-buildings --raster pre-event/1050010012BCAE00-pre-clipped.tif

# if not, check Google buildings
# https://sites.research.google/open-buildings/#download

# if not, check Microsoft buildings
# https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/examples/example_building_footprints.ipynb

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
