# AutoDriveLab-Simulator

## Carla Server 

To run the Carla server, first pull the Docker image
```commandline 
docker pull kevinliuzc/carla-video-stream
```

Then run the carla server
```commandline 
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY kevinliuzc/carla-video-stream /bin/bash ./CarlaUE4.sh
```
## Running Client and Recording Sensor Data 

To run the Carla client, first pull the Docker image 
```commandline 
docker pull kevinliuzc/carla-client
```

Then run a Carla client container
```commandline 
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY -v $(pwd):/app --rm -it --entrypoint /bin/bash kevinliuzc/carla-client
```

Within the container, run 
```commandline 
python3 manual_control.py 
```