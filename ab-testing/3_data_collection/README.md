# Run Carla Docker Container
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY kevinliuzc/carla-video-stream /bin/bash ./CarlaUE4.sh -RenderOffScreen

# Run manual_control.py
conda activate carla
python manual_control.py --host 192.168.88.96

# Run manual_control.py with live data collection
git checkout f669c8b870cd4d2032708f5b5e9ee0139492565c
python manual_control.py --host 192.168.88.96