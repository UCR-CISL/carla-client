import carla
import numpy as np
import pygame
import threading
import time
import os
import cv2
from datetime import datetime
from pathlib import Path
import re
import csv
import math

# Setup base path and find takes
#base_path = Path("recordings") / f"{datetime.now().strftime('%Y-%m-%d')}-Alpha"
base_path = Path("recordings") / f"2025-10-27-Lambda"
start_take = 0
takes = sorted([int(p.name) for p in base_path.iterdir() if p.is_dir() and p.name.isdigit()])
# --- Filter to only include takes >= start_take ---
takes = [t for t in takes if t >= start_take]
takes = ['0','1','2', '3', '4']
if not takes:
    raise RuntimeError(f"No takes found in {base_path}")

print(f"Found takes: {takes}")



# --- CARLA Setup ---
host = '127.0.0.1'
port = 2000
client = carla.Client(host, port)
client.set_timeout(10.0)

# Get world and set synchronous mode
world = client.get_world()
settings = world.get_settings()
settings.synchronous_mode = True
# settings.fixed_delta_seconds = 0.0769  # 20 FPS
world.apply_settings(settings)


def get_closest_vehicle_from_csv(world, position_csv, vehicle_filter='vehicle.dodge.charger_2020'):
    """
    Find the vehicle in the CARLA world that is closest to the first recorded position
    in a given CSV file.

    Args:
        world: carla.World object
        position_csv: path to the CSV file containing vehicle positions
        vehicle_filter: CARLA actor filter (default: 'vehicle.dodge.charger_2020')

    Returns:
        (closest_vehicle, distance): tuple containing the closest carla.Actor and its distance in meters
    """
    # --- Get all matching vehicles ---
    vehicles = world.get_actors().filter(vehicle_filter)
    if len(vehicles) == 0:
        raise RuntimeError(f"No vehicles found matching filter: {vehicle_filter}")

    # --- Read first position from CSV ---
    with open(position_csv, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # skip header
        first_row = next(reader)  # first data line

        # CSV format:
        # timestamp,frame,vehicle.id,x,y,z,yaw,pitch,roll,speed,accel,angular,intent
        ref_x = float(first_row[3])
        ref_y = float(first_row[4])
        ref_z = float(first_row[5])
        ref_position = (ref_x, ref_y, ref_z)

    # --- Compute distance function ---
    def distance(loc, ref_pos):
        return math.sqrt(
            (loc.x - ref_pos[0])**2 +
            (loc.y - ref_pos[1])**2 +
            (loc.z - ref_pos[2])**2
        )

    # --- Find closest vehicle ---
    closest_vehicle = min(vehicles, key=lambda v: distance(v.get_location(), ref_position))
    closest_distance = distance(closest_vehicle.get_location(), ref_position)

    print(f"Reference position: {ref_position}")
    print(f"Closest vehicle: {closest_vehicle.id} ({closest_vehicle.type_id})")
    print(f"Distance: {closest_distance:.2f} m")

    return closest_vehicle, closest_distance

# Define take processing function
def setup_cameras(world, vehicle, camera_bp, camera_transforms, base_path, first_frame):
    """Setup cameras and their callbacks for the replay."""
    cameras = {}
    frames = {}
    frame_locks = {}
    frame_written = {}
    frame_written_locks = {}
    frame_complete_event = threading.Event()

    # Global variables for tracking frames
    current_frame_number = first_frame
    frames_processed = 0

    for key, transform in camera_transforms.items():
        cam = world.spawn_actor(camera_bp, transform, attach_to=vehicle)
        cameras[key] = cam
        frames[key] = None
        frame_locks[key] = threading.Lock()
        frame_written[key] = False
        frame_written_locks[key] = threading.Lock()

        def make_callback(k):
            camera_folder = base_path / "images" / k
            os.makedirs(camera_folder, exist_ok=True)
            
            def callback(image):
                nonlocal current_frame_number, frames_processed
                img_array = np.frombuffer(image.raw_data, dtype=np.uint8)
                img_array = img_array.reshape((image.height, image.width, 4))
                img_bgr = img_array[:, :, :3][:, :, ::-1]
                
                frame_number  = world.get_snapshot().frame
                img_path = camera_folder / f"{frame_number}.jpg"
                
                cv2.imwrite(str(img_path), img_array,  [int(cv2.IMWRITE_JPEG_QUALITY), 40])
                
                with frame_locks[k]:
                    frames[k] = (img_bgr, image.frame)
                
                with frame_written_locks[k]:
                    frame_written[k] = True
                
                all_written = True
                for cam_key in cameras.keys():
                    with frame_written_locks[cam_key]:
                        if not frame_written[cam_key]:
                            all_written = False
                            break
                
                if all_written:
                    current_frame_number = first_frame + frames_processed
                    frames_processed += 1
                    frame_complete_event.set()
                    
                    for cam_key in cameras.keys():
                        with frame_written_locks[cam_key]:
                            frame_written[cam_key] = False
            
            return callback

        cam.listen(make_callback(key))
    
    return cameras, frames, frame_locks, frame_written, frame_written_locks, frame_complete_event

def simulate_replay(take_path: Path, client, world, base_path: Path, first_frame: int):
    """Run a replay simulation for a single take with camera setup and frame capture."""
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode((1600, 900))
    pygame.display.set_caption('CARLA Replay')
    
    # Camera view positions in the display window
    positions = {
        "top": (0, 0),
        "left": (0, 300),
        "right": (400, 300),
        "rear": (800, 300)
    }
    
    # Start the replay
    recording_path = str(take_path / "recording.log")
    print(f"At start replay {recording_path}")
    client.replay_file(f"/home/remote-ops/Documents/carla-client/{recording_path}", 0.0, -1.0, 0)
    
    # Wait for the world to be ready
    world.tick()
    
    bp_lib = world.get_blueprint_library()
    
    # Find the vehicle from replay
    vehicles = world.get_actors().filter('vehicle.dodge.charger_2020')
    print(vehicles)
    if len(vehicles) == 0:
        raise RuntimeError("No vehicles found in the replay!")
    position_csv = take_path / 'position.csv'
    vehicle, dist = get_closest_vehicle_from_csv(world, position_csv)
    print(f"Attached cameras to: {vehicle.type_id}")
    
    # Camera Setup
    camera_bp = bp_lib.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '1920')
    camera_bp.set_attribute('image_size_y', '1080')
    camera_bp.set_attribute('fov', '120')
    
    # Define camera transforms
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
    
    return {
        'recording_path': recording_path,
        'positions': positions,
        'vehicle': vehicle,
        'camera_bp': camera_bp,
        'camera_transforms': camera_transforms,
        'screen': screen,
        'clock': clock
    }

def process_take(take_path: Path, client, world):
    print(f"\nProcessing take at {take_path}")
    
    # Check for required files
    position_csv = take_path / "position.csv"
    recording_log = take_path / "recording.log"
    
    if not position_csv.exists():
        print(f"Warning: position.csv not found at {position_csv}")
        return False
    
    if not recording_log.exists():
        print(f"Warning: recording.log not found at {recording_log}")
        return False
        
    # Read frame numbers from position.csv
    with open(position_csv, 'r') as f:
        next(f)  # Skip header if it exists
        first_line = next(f)
        first_frame = int(first_line.split(',')[1])
        
        # Read to end to get last frame
        for line in f:
            last_frame = int(line.split(',')[1])
            
    print(f"Found frames {first_frame} to {last_frame}")
    
    
    
    # Setup camera recording context
    frames = {}
    frame_locks = {}
    frame_written = {}
    frame_written_locks = {}
    frame_complete_event = threading.Event()
    
    # Return simulation context and frame information
    return {
        'first_frame': first_frame,
        'last_frame': last_frame,
        'frames': frames,
        'frame_locks': frame_locks,
        'frame_written': frame_written,
        'frame_written_locks': frame_written_locks,
        'frame_complete_event': frame_complete_event
    }


def run_playback_loop(context, world, client, control_writer=None, position_writer=None):
    """Run the main playback loop for recording playback and visualization."""
    running = True
    starting_frame = None
    final_frame = None
    current_frame = -1
    print(context['recording_path'])
    # Get total frame count from recording
    info = client.show_recorder_file_info(f"/home/remote-ops/Documents/carla-client/{context['recording_path']}", True)
    match = re.search(r"Frames:\s*(\d+)", info)
    total_frames = int(match.group(1)) if match else None
    print(f"Recording has {total_frames} frames." if total_frames else "Could not find total frame count.")
    vehicle = context['vehicle']
    while running:
        try:
            # Clear frame completion event
            context['frame_complete_event'].clear()
            
            # Tick world to advance simulation
            world.tick()
            #-----Log position per frame---
            vehicle_id = vehicle.id

            # --- Get transform and motion data ---
            transform = vehicle.get_transform()
            velocity = vehicle.get_velocity()
            acceleration = vehicle.get_acceleration()
            angular_velocity = vehicle.get_angular_velocity()

            speed = (velocity.x**2 + velocity.y**2 + velocity.z**2) ** 0.5
            accel = (acceleration.x**2 + acceleration.y**2 + acceleration.z**2) ** 0.5
            angular = (angular_velocity.x**2 + angular_velocity.y**2 + angular_velocity.z) ** 0.5

            world_snapshot = world.get_snapshot()
            timestamp = world_snapshot.timestamp

            if position_writer:
                try:
                    position_writer.writerow([
                        world_snapshot.frame,
                        f"{timestamp.elapsed_seconds:.6f}",
                        vehicle_id,
                        transform.location.x,
                        transform.location.y,
                        transform.location.z,
                        transform.rotation.yaw,
                        transform.rotation.pitch,
                        transform.rotation.roll,
                        f"{speed}",
                        f"{accel}",
                        f"{angular}"
                    ])
                except Exception as e:
                    print(f"Warning: Could not log location data: {e}")
            # --- Log control values per frame ---
            if control_writer:
                try:
                    control = vehicle.get_control()
                    timestamp = world.get_snapshot().timestamp.elapsed_seconds
                    control_writer.writerow([
                        world.get_snapshot().frame,
                        control.throttle,
                        control.brake,
                        control.steer,
                        control.reverse,
                        control.hand_brake,
                        control.manual_gear_shift,
                        control.gear
                    ])
                except Exception as e:
                    print(f"Warning: Could not log control data: {e}")
                
            # Wait for camera frames
            if not context['frame_complete_event'].wait(timeout=30.0):
                print("Warning: Timeout waiting for cameras to write frames")
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            
            context['screen'].fill((0, 0, 0))
            if final_frame is not None and current_frame >= final_frame:
                print(f"Replay complete. Processed {current_frame} frames.")
                running = False
                break
            
            current_frame = -1
            for key, frame_data in context['frames'].items():
                if frame_data is not None:
                    with context['frame_locks'][key]:
                        img, frame_num = frame_data
                        img = img.copy()
                        current_frame = max(current_frame, frame_num)
                        
                        if starting_frame is None:
                            starting_frame = current_frame
                            final_frame = starting_frame + total_frames
                            print(f"Replay starting at {starting_frame}, will end at {final_frame}")
                        
                        surface = pygame.surfarray.make_surface(img.swapaxes(0, 1))
                        surface = pygame.transform.scale(surface, (400, 300))
                        x, y = context['positions'][key]
                        context['screen'].blit(surface, (x, y))
            
            pygame.display.flip()
            context['clock'].tick(30)
            
        except RuntimeError as e:
            if "recording is over" in str(e).lower():
                print("Replay finished")
                running = False
            else:
                raise
    if control_writer:
        control_writer.writerow([])  # Optional blank line
        control_writer = None
    if position_writer:
        position_writer.writerow([])  # Optional blank line
        position_writer = None


def cleanup_simulation(cameras, context):
    """Cleanup simulation resources."""
    print("\nCleaning up simulation resources...")
    
    # Destroy all cameras
    for camera in cameras.values():
        if camera.is_alive:
            print(f"Destroying camera: {camera.type_id}")
            camera.destroy()
    
    # Reset frame tracking variables
    context['frames'].clear()
    context['frame_locks'].clear()
    context['frame_written'].clear()
    context['frame_written_locks'].clear()
    
    # Close display if it was created
    if 'screen' in context and pygame.get_init():
        pygame.display.quit()
    
    print("Cleanup completed")

# Process each take
for take in takes:
    take_path = base_path / str(take)
    print(f"\n=== Processing Take {take} ===")
    take_context = process_take(take_path, client, world)
    if not take_context:
        print(f"Skipping take {take} due to missing files")
        continue
    
    # Setup simulation
    sim_context = simulate_replay(take_path, client, world, base_path, take_context['first_frame'])
    
    # Setup cameras
    cameras, frames, frame_locks, frame_written, frame_written_locks, frame_complete_event = setup_cameras(
        world, sim_context['vehicle'], sim_context['camera_bp'], sim_context['camera_transforms'],
        take_path, take_context['first_frame']
    )
    control_log_path = take_path / f"controls.csv"
    control_log_file = open(control_log_path, mode='w', newline='')
    control_writer = csv.writer(control_log_file)

    position_log_path =  take_path / f"location.csv"
    position_log_file = open(position_log_path, mode='w', newline='')
    position_writer = csv.writer(position_log_file)

    # Write header
    position_writer.writerow([
        "frame_id",
        "timestamp",
        "vehicle_id",
        "x", "y", "z",
        "yaw", "pitch", "roll",
        "speed", "accel", "angular"
    ])

    # Write header row
    control_writer.writerow([
        "frame", 
        "throttle", "brake", "steer", 
        "reverse", "hand_brake", "manual_gear_shift", "gear"
    ])

    # Create full context
    context = {**sim_context, **{
        'frames': frames,
        'frame_locks': frame_locks,
        'frame_written': frame_written,
        'frame_written_locks': frame_written_locks,
        'frame_complete_event': frame_complete_event
    }}
    
    # Run playback loop
    run_playback_loop(context, world, client, control_writer, position_writer)
    control_log_file.close()
    position_log_file.close()
    print(f"Control log saved: {control_log_path}")
    
    # Cleanup
    cleanup_simulation(cameras, context)
    pygame.quit()
    
    print(f"Completed processing take {take}")

