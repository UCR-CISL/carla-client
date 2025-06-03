#!/bin/bash

source /home/remote-ops/anaconda3/etc/profile.d/conda.sh

conda activate carla

python manual_control.py --host 192.168.88.96
