#!/bin/bash
echo "Starting jetson docker..."
cd /*yourpath_to*/jetson-inference
./docker/run.sh --volume /*yourpath_to*/my-scripts:/myscripts -r "python3 /myscripts/search-object.py"
echo "Jetson docker stopped..."
