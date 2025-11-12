# Run Carla Docker Container
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY kevinliuzc/carla-video-stream /bin/bash ./CarlaUE4.sh -RenderOffScreen

# Run manual_control.py
python manual_control.py --host 192.168.88.96