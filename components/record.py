import imageio.v3 as iio
import os 
import time 

def get_vehicle_position(frame, vehicle, save_path):
    start = time.time()
    transform = vehicle.get_transform()
        
    frame_data = {
                    "frame_id" : frame,
                    "vehicle_id" : vehicle.id, 
                    "x" : transform.location.x, 
                    "y" : transform.location.y, 
                    "z" : transform.location.z, 
                    "yaw" : transform.rotation.yaw, 
                    "pitch" : transform.rotation.pitch, 
                    "roll" : transform.rotation.roll
                }

    with open(save_path, "a") as file:
        file.write(f'{frame},{vehicle.id},{frame_data["x"]},{frame_data["y"]},{frame_data["z"]},{frame_data["yaw"]},{frame_data["pitch"]},{frame_data["roll"]}\n')

    end = time.time()
    return frame_data, start, end

def save_image(image_data, frame, save_folder, cam_type):
    start = time.time()
    file_name = f"{frame}.png"
    save_dir = os.path.join(save_folder, "images",  cam_type)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file_name)
    iio.imwrite(save_path, image_data)
    end = time.time() 
    return start, end, file_name
