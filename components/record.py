import carla 
import numpy as np 
import imageio.v3 as iio
import os 
import time 

#TODO: Determine format for .json to hold vehicle position for each frame
def get_vehicle_position(frame, vehicle): 
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
    end = time.time()
    return frame_data, start, end

#TODO: Change to include user inputted save_folder
def save_image(image, cam_type, save_folder="images"):

    image_data = np.array(image.raw_data)
    image_data = image_data.reshape((image.height, image.width, 4)) 
    image_data = image_data[:, :, :3]  
    file_name = f"frame_{image.frame}.png"
    save_path = os.path.join(save_folder, cam_type, file_name)
    iio.imwrite(save_path, image_data)

#TODO: Check if directory exists 
def save_image2(image_data, frame, save_folder="latency_performance"):
    start = time.time()
    if 1080 in image_data.shape:
        cam_type = "driver"
    else:
        cam_type = "reverse"
    file_name = f"frame_{frame}.png"
    save_dir = os.path.join(save_folder, "images")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, cam_type, file_name)
    iio.imwrite(save_path, image_data)
    end = time.time() 
    return start, end, file_name
