import pandas as pd 
import os 

class RecordLatency(object): 
    def __init__(self):
        self.frames = [] 
        self.timestamps = []
        self.events = []
        self.save_path = ""

    def check_existing_directory(self): 
        folder = os.path.dirname(self.save_path)
        folder = os.path.expanduser(folder)
        if folder and not os.path.exists(folder): 
            os.makedirs(folder)

    def update_df(self, event, timestamp, frame): 
        self.frames.append(frame)
        self.timestamps.append(timestamp)
        self.events.append(event)
        
    def save_to_csv(self):       
        data = {
                "Frame": self.frames, 
                "Timestamp": self.timestamps, 
                "Event" : self.events}
        df = pd.DataFrame(data)
        self.check_existing_directory()
        df.to_csv(self.save_path, index=False)