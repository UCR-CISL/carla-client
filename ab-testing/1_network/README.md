# Run Docker Container
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY carlasim/carla:0.9.15 /bin/bash ./CarlaUE4.sh -renderOffScreen  

# Connect Via Manual Control

## NIC
conda activate ab-testing
python manual_control.py --host 192.168.88.96

## WIFI
conda activate ab-testing
python manual_control.py --host 192.168.0.194

