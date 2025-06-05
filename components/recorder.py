import imageio.v3 as iio
import os 
from pathlib import Path
import concurrent.futures

from datetime import datetime



class Recorder():
    def __init__(self, base_path: Path):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers = 8)
        self.recording = False

        self.take = 0
        now = datetime.now()
        self._base = base_path / now.strftime("%Y-%m-%d")
        self.recording_path = self._base / str(self.take)

    def __del__(self):
        self.pool.shutdown(wait = True) 

    def turn_recorder_on(self) -> None:
        if self.recording:
            return 
        
        self.recording_path = self._base / str(self.take)
        self.take += 1

        self.recording = True

    def turn_recorder_off(self) -> None:
        self.recording = False

    def is_recording(self) -> bool:
        return self.recording

    def save_image(self, image, type: str, frame: str) -> None:
        if self.recording == False:
            return

        def _worker():
            directory = self.recording_path / "images" / type 
            os.makedirs(directory, exist_ok = True)

            path = directory / f"{frame}.png"
            iio.imwrite(path, image)
        
        self.pool.submit(_worker)

    def save_position(self, vehicle, frame: str) -> None:
        if self.recording == False:
            return
        
        def _worker():
            transform = vehicle.get_transform()

            file = self.recording_path / "position.csv"

            with open(file, "a") as f:
                f.write(f'{frame},{vehicle.id},{transform.location.x},{transform.location.y},{transform.location.z},{transform.rotation.yaw},{transform.rotation.pitch},{transform.rotation.roll}\n')

        self.pool.submit(_worker)

    def save_button(self, type, button, frame, timestamp) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "buttons.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{button}\n')
        
        self.pool.submit(_worker)

    def save_hat(self, type, value, frame, timestamp) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "hat.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{value}\n')
        
        self.pool.submit(_worker)

    def save_key(self, type, key, frame, timestamp) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "keys.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{key}\n')\
        
        self.pool.submit(_worker)

    def save_joystick(self, type, raw, calculated, frame, timestamp) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "joysticks.csv"

            with open(file, "a") as f:
                f.write(f'{timestamp},{frame},{type},{raw},{calculated}\n')
        
        self.pool.submit(_worker)

recorder = Recorder(Path("recordings"))