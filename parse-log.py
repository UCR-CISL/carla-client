import re
import numpy as np
from pathlib import Path
import json

def parse(file):
    with open(file, "r") as f:
        contents = f.read()

    frames = re.split(r'Frame \d+', contents)

    infos = {}
    prev_timestamp = 0.0
    curr_timestamp = 0.0

    for idx, frame in enumerate(frames[1:]):
        lines = frame.split("\n")

        timestamp_pattern = r"at\s+([0-9]*\.?[0-9]+)"
        timestamp = re.search(timestamp_pattern, frame)

        if timestamp:
            prev_timestamp = float(curr_timestamp)
            curr_timestamp = float(timestamp.group(1))

        for line in lines:
            line = line.strip()

            position_pattern = r"Id:\s*(\d+)\s+Location:\s*\(([^)]+)\)\s+Rotation:\s*\(([^)]+)\)"
            position = re.search(position_pattern, line)

            control_pattern = r"Id:\s*(\d+)\s+Steering:\s*([-\deE.+]+)\s+Throttle:\s*([-\deE.+]+)\s+Brake:\s*([-\deE.+]+)"
            control = re.search(control_pattern, line)

            if position:
                location = position.group(2)
                x, y, z = location.split(",")

                rotation = position.group(3)
                roll, pitch, yaw = rotation.split(",")

                if position.group(1) in infos:
                    infos[position.group(1)]["location"][idx] = [float(x), float(y), float(z)]
                    infos[position.group(1)]["rotation"][idx] = [float(roll), float(pitch), float(yaw)]
                    
                    velocity = ((infos[position.group(1)]["location"][idx] / 100) - (infos[position.group(1)]["location"][idx - 1]) / 100) / (curr_timestamp - prev_timestamp)
                    infos[position.group(1)]["velocity"][idx] = velocity

            elif control:
                if control.group(1) in infos:
                    infos[control.group(1)]["control"][idx] = [float(control.group(2)), float(control.group(3)), float(control.group(4))]

            elif line.startswith("Create"):
                id = re.search(r"\d+", line)

                vehicle = re.search(r"vehicle\.[a-z]*\.[a-z0-9_\.]*", line)
                if vehicle:
                    infos[id.group(0)] = {
                        "location": np.zeros((len(frames[1:]), 3)),
                        "rotation": np.zeros((len(frames[1:]), 3)),
                        "control": np.zeros((len(frames[1:]), 3)),
                        "velocity": np.zeros((len(frames[1:]), 3)),
                        "type": "vehicle",
                        "id": vehicle.group(0)
                    }

                spectator = re.search(r"spectator", line)
                if spectator:
                    infos[id.group(0)] = {
                        "location": np.zeros((len(frames[1:]), 3)),
                        "rotation": np.zeros((len(frames[1:]), 3)),
                        "velocity": np.zeros((len(frames[1:]), 3)),
                        "type": "spectator",
                        "id": spectator.group(0)
                    }

                pedestrian = re.search(r"walker\.[a-z]*\.[a-z0-9_\.]*", line)
                if pedestrian:
                    infos[id.group(0)] = {
                        "location": np.zeros((len(frames[1:]), 3)),
                        "rotation": np.zeros((len(frames[1:]), 3)),
                        "velocity": np.zeros((len(frames[1:]), 3)),
                        "type": "pedestrian",
                        "id": pedestrian.group(0)
                    }


    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open(str(file).replace(".log", ".json"), "w") as f:
        json.dump(infos, f, cls=NumpyEncoder)

def main():
    recordings = Path("carla-recordings")

    for log in recordings.rglob("*.log"):    
        parse(log)

main()