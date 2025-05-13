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

    def get_logs(self, start_time=None, end_time=None, activity_type=None):
        """
        Retrieve logs within a specified time range and/or activity type
        
        Args:
            start_time (datetime, optional): Start time for filtering logs
            end_time (datetime, optional): End time for filtering logs
            activity_type (str, optional): Filter by activity type
            
        Returns:
            list: List of log entries matching the criteria
        """
        try:
            if not os.path.exists(self.json_log_path):
                return []
                
            with open(self.json_log_path, 'r') as f:
                logs = json.load(f)
            
            filtered_logs = []
            for log in logs:
                log_time = datetime.fromisoformat(log['timestamp'])
                
                # Apply time filters if specified
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
                    
                # Apply activity type filter if specified
                if activity_type and log['type'] != activity_type:
                    continue
                    
                filtered_logs.append(log)
                
            return filtered_logs
            
        except Exception as e:
            logging.error(f"Failed to read logs: {str(e)}")
            return []