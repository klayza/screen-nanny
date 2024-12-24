import json
import logging
from datetime import datetime
import os

class ActivityLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up file logging
        logging.basicConfig(
            filename=os.path.join(log_dir, 'activity.log'),
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        
        # Set up JSON logging for structured data
        self.json_log_path = os.path.join(log_dir, 'activity_data.json')
    
    def log_activity(self, activity_type, data):
        """Log an activity with its associated data"""
        timestamp = datetime.now().isoformat()
        
        # Log to text file
        logging.info(f"{activity_type}: {json.dumps(data)}")
        
        # Log to JSON file
        log_entry = {
            "timestamp": timestamp,
            "type": activity_type,
            "data": data
        }
        
        self._append_to_json(log_entry)
    
    def _append_to_json(self, entry):
        """Append an entry to the JSON log file"""
        try:
            if os.path.exists(self.json_log_path):
                with open(self.json_log_path, 'r+') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = []
                    data.append(entry)
                    f.seek(0)
                    json.dump(data, f, indent=2)
            else:
                with open(self.json_log_path, 'w') as f:
                    json.dump([entry], f, indent=2)
        except Exception as e:
            logging.error(f"Failed to write to JSON log: {str(e)}") 