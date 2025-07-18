# AutoDriveLab-Simulator

## Carla Server 

To run the Carla server, first pull the Docker image
```commandline 
docker pull kevinliuzc/carla-video-stream
```

Then run the carla server
```commandline 
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY kevinliuzc/carla-video-stream /bin/bash ./CarlaUE4.sh --graphicsadapter=1 -RenderOffScreen
```
## Running Client and Recording Sensor Data 

To run the Carla client, first build the Docker  
```commandline 
docker build -f Dockerfile.dockerfile -t cisl/client-latency-recording .
```

Then run a Carla client container
```commandline 
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY -v ./:/app cisl/client-latency-recording
```
