import time
import imageio.v3 as iio
import os 
from pathlib import Path
import concurrent.futures
from datetime import datetime
import subprocess



class Recorder():
    def __init__(self, base_path: Path):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers = 8)
        self.recording = False
        self.client = None

        now = datetime.now()
        self._base = base_path / now.strftime("%Y-%m-%d")

        if self._base.exists():
            existing_takes = [int(p.name) for p in self._base.iterdir() if p.is_dir() and p.name.isdigit()]
            self.take = max(existing_takes) + 1 if existing_takes else 0
        else:
            self.take = 0

        self.recording_path = self._base / str(self.take)

    def __del__(self):
        self.pool.shutdown(wait = True) 

    def set_client(self, client):
        """Set the CARLA client for recording."""
        self.client = client

    def turn_recorder_on(self) -> None:
        if self.recording:
            return 
        
        self.recording_path = self._base / str(self.take)
        self.take += 1

        # Start CARLA recorder and save .log in recording_path if client is available
        if self.client is not None:
            try:
                # Ensure directory exists
                os.makedirs(self.recording_path, exist_ok=True)
                
                print(f"Starting CARLA recorder")
                self.client.start_recorder("final.log",True)
                
            except Exception as e:
                print(f"Error starting CARLA recorder: {e}")
                return

        self.recording = True

    def get_image_folders_status(self):
        required_folders = ["driver", "left", "reverse", "right"]
        images_path = self.recording_path / "images"
        status = {}
        for folder in required_folders:
            status[folder] = (images_path / folder).is_dir()
        return status

    def turn_recorder_off(self) -> None:
        if self.recording:
            # Stop CARLA recorder if client is available
            if self.client is not None:
                self.client.stop_recorder()
                print("Stopped CARLA recorder.")
                time.sleep(3)
                #We wait before copying so that the log file is fully written

                # Copy the log file from the docker container directly to recording path
                try:
                    # Copy from docker directly to recording path
                    subprocess.run(
                        f"docker cp single:/home/carla/.config/Epic/CarlaUE4/Saved/final.log {self.recording_path}/recording.log",
                        shell=True,
                        check=True
                    )
                    print(f"Copied recording log to {self.recording_path / 'recording.log'}")
                except Exception as e:
                    print(f"Error copying recording log: {e}")
                
            self.recording = False

    def is_recording(self) -> bool:
        return self.recording

    def save_position(self, vehicle, frame: str,intent) -> None:
        if self.recording == False:
            return
        
        def _worker():
            transform = vehicle.get_transform()

            file = self.recording_path / "position.csv"

            velocity = vehicle.get_velocity()
            speed = (velocity.x**2 + velocity.y**2 + velocity.z**2) ** 0.5

            acceleration = vehicle.get_acceleration()
            accel = (acceleration.x**2 + acceleration.y**2 + acceleration.z**2) ** 0.5

            angular_velocity = vehicle.get_angular_velocity()
            angular = (angular_velocity.x**2 + angular_velocity.y**2 + angular_velocity.z**2) ** 0.5

            with open(file, "a") as f:
                f.write(f'{datetime.now()},{frame},{vehicle.id},{transform.location.x},{transform.location.y},{transform.location.z},{transform.rotation.yaw},{transform.rotation.pitch},{transform.rotation.roll},{speed},{accel},{angular},{intent}\n')

        self.pool.submit(_worker)

    def save_button(self, type, button, frame, ticks) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "buttons.csv"

            with open(file, "a") as f:
                f.write(f'{datetime.now()},{ticks},{frame},{type},{button}\n')
        
        self.pool.submit(_worker)

    def save_hat(self, type, value, frame, ticks) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "hat.csv"

            with open(file, "a") as f:
                f.write(f'{datetime.now()},{ticks},{frame},{type},{value}\n')
        
        self.pool.submit(_worker)

    def save_key(self, type, key, frame, ticks) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "keys.csv"

            with open(file, "a") as f:
                f.write(f'{datetime.now()},{ticks},{frame},{type},{key}\n')\
        
        self.pool.submit(_worker)

    def save_joystick(self, throttle_raw, throttle_calculated, brake_raw, brake_calculated, steer_raw, steer_calculated, frame, timestamp) -> None:
        if self.recording == False:
            return
        
        def _worker():
            file = self.recording_path / "joysticks.csv"

            with open(file, "a") as f:
                f.write(f'{datetime.now()},{timestamp},{frame},{throttle_raw},{throttle_calculated},{brake_raw},{brake_calculated},{steer_raw},{steer_calculated}\n')
        
        self.pool.submit(_worker)

recorder = Recorder(Path("recordings"))