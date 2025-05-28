import imageio.v3 as iio
import os 
from pathlib import Path
import concurrent.futures

class Recorder():
    def __init__(self, base_path: Path):
        self.base = base_path

        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers = 8)

    def __del__(self):
        self.pool.shutdown(wait = True) 

    def save_image(self, image, type: str, frame: str):
        def _worker():
            directory = self.base / "images" / type 
            os.makedirs(directory, exist_ok = True)

            path = directory / f"{frame}.png"
            iio.imwrite(path, image)
        
        self.pool.submit(_worker)

    def save_position(self, vehicle, frame: str):
        def _worker():
            transform = vehicle.get_transform()

            file = self.base / "position.csv"

            with open(file, "a") as f:
                f.write(f'{frame},{vehicle.id},{transform.location.x},{transform.location.y},{transform.location.z},{transform.rotation.yaw},{transform.rotation.pitch},{transform.rotation.roll}\n')

        self.pool.submit(_worker)

    def save_button(self, type, button, frame, timestamp):
        def _worker():
            file = self.base / "buttons.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{button}\n')
        
        self.pool.submit(_worker)

    def save_hat(self, type, value, frame, timestamp):
        def _worker():
            file = self.base / "hat.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{value}\n')
        
        self.pool.submit(_worker)

    def save_key(self, type, key, frame, timestamp):
        def _worker():
            file = self.base / "keys.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{key}\n')\
        
        self.pool.submit(_worker)

    def save_joystick(self, type, raw, calculated, frame, timestamp):
        def _worker():
            file = self.base / "joysticks.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{raw},{calculated}\n')
        
        self.pool.submit(_worker)

recorder = Recorder(Path("recordings/0"))