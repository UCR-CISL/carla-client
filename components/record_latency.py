import os 

class RecordLatency(object): 
    def __init__(self, save_path):
        self.frames = [] 
        self.timestamps = []
        self.events = []
        self.save_path = save_path

    def _check_existing_directory(self): 
        folder = os.path.dirname(self.save_path)
        folder = os.path.expanduser(folder)
        if folder and not os.path.exists(folder): 
            os.makedirs(folder)

    def log(self, event, timestamp, frame):
        with open(self.save_path, "a") as file:
            file.write(f"{frame},{timestamp},{event}\n")