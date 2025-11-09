import carla
import pandas as pd
import numpy as np
from pathlib import Path
import cv2
import time
import json

root = Path("data")

idx = 0

def setup_client():
    client = carla.Client("192.168.88.96", 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    return world, client

def spawn_agents(world, infos):
    agents = {}
    bp_lib = world.get_blueprint_library()

    for info in infos:

        is_ego = False

        if infos[info]["id"] == "spectator":
            continue
        
        if infos[info]["id"] == "vehicle.dodge.charger_2020":
            is_ego = True
        
        blueprint = bp_lib.find(infos[info]["id"])

        spawn_location = infos[info]["location"][0]
        spawn_rotation = infos[info]["rotation"][0]

        spawn_point = carla.Transform(
                carla.Location(x=spawn_location[0] / 100, y=spawn_location[1] / 100, z=spawn_location[2] / 100 + 0.1),
                carla.Rotation(pitch=spawn_rotation[0], yaw=spawn_rotation[1], roll=spawn_rotation[2])
            )
        
        print(f"Spawning Actor: {info} of type {infos[info]['id']} at {spawn_point}")
        
        actor = world.spawn_actor(blueprint, spawn_point)

        agents[info] = {"actor": actor, "is_ego": is_ego}
    
    return agents


def attach_camera(world, vehicle, agent_name, collection, take):
    bp_lib = world.get_blueprint_library()
    cam_bp = bp_lib.find('sensor.camera.rgb')
    cam_bp.set_attribute('image_size_x', '1920')
    cam_bp.set_attribute('image_size_y', '1080')
    cam_bp.set_attribute('fov', '120')

    camera_transforms = {
        "top": carla.Transform(
            carla.Location(x=0.40, y=0.00, z=1.60),
            carla.Rotation(pitch=11.00, yaw=0.00, roll=0.00)
        ),
        "left": carla.Transform(
            carla.Location(x=-0.31, y=-0.48, z=1.60),
            carla.Rotation(pitch=-1.00, yaw=-90.00, roll=0.00)
        ),
        "right": carla.Transform(
            carla.Location(x=-0.31, y=0.48, z=1.60),
            carla.Rotation(pitch=-1.00, yaw=-270.00, roll=0.00)
        ),
        "rear": carla.Transform(
            carla.Location(x=-0.96, y=0.00, z=1.60),
            carla.Rotation(pitch=13.00, yaw=180.00, roll=0.00)
        )
    }

    cameras = []

    for key, transform in camera_transforms.items():
        cam = world.spawn_actor(cam_bp, transform, attach_to=vehicle)

        (root / collection / take / "images" / agent_name / key).mkdir(parents=True, exist_ok=True)

        def save_img(image, key):
            img = np.frombuffer(image.raw_data, dtype=np.uint8)
            img = img.reshape((image.height, image.width, 4))
            path = root / collection / take / "images" / agent_name / key / f"{idx}.jpg"
            cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 40])

        cam.listen(lambda img, k = key: save_img(img, k))
        cameras.append(cam)
        
    return cameras

def load_infos(file):
    with open(file, "r") as f:
        infos = json.load(f)

    return infos


def manual_replay(world, agents, infos):
    global idx
    print(f"Replaying {len(infos['1']['location'])} synchronized frames across 3 agents...")

    for frame_idx in range(len(infos['1']['location'])):
        print(f"Processing Frame: {frame_idx}")

        for agent_id in agents:
            location = infos[agent_id]["location"][frame_idx]
            rotation = infos[agent_id]["rotation"][frame_idx]
            
            transform = carla.Transform(
                carla.Location(x=location[0] / 100, y=location[1] / 100, z=location[2] / 100),
                carla.Rotation(pitch=rotation[0], yaw=rotation[1], roll=rotation[2])
            )

            agents[agent_id]["actor"].set_transform(transform)

        world.tick()
        idx += 1


def cleanup(world, actors, sensors):
    print("Cleaning up actors and sensors...")
    for a in actors:
        a.destroy()
    
    for a in sensors:
        a.stop()
        a.destroy()
    world.apply_settings(world.get_settings())
    print("Cleanup complete.")


def playback(file, collection, take):
    world, client = setup_client()

    actors = []
    actors += world.get_actors().filter("vehicle.*")
    actors += world.get_actors().filter("walker.*")
    actors += world.get_actors().filter("controller.*")

    sensors = []
    sensors += world.get_actors().filter("sensor.camera.rgb")

    cleanup(world, actors, sensors)

    infos = load_infos(file)

    agents = spawn_agents(world, infos)

    sensors = []

    for agent in agents:
        if agents[agent]["is_ego"]:
            sensors += attach_camera(world, agents[agent]["actor"], agent, collection, take)

    try:
        manual_replay(world, agents, infos)
        # pass
    finally:
        actors = []
        actors += world.get_actors().filter("vehicle.*")
        actors += world.get_actors().filter("walker.*")
        actors += world.get_actors().filter("controller.*")

        sensors = []
        sensors += world.get_actors().filter("sensor.camera.rgb")

        cleanup(world, actors, sensors)


if __name__ == "__main__":
    recordings = Path("carla-recordings/2025-10-20/")

    for recording in recordings.rglob("6.json"):
        print(f"Processing Recording: {str(recording)}")
        playback(recording, recording.parent.name, recording.stem)
