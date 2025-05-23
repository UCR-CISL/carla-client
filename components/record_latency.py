import concurrent.futures

class Latency(): 
    def __init__(self, save_path):
        self.frames = [] 
        self.timestamps = []
        self.events = []
        self.save_path = save_path

        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def _log(self, event, timestamp, frame):
        with open(self.save_path, "a") as file:
            file.write(f"{frame},{timestamp},{event}\n")

    def log(self, event, timestamp, frame):
        self.pool.submit(self._log, event, timestamp, frame)