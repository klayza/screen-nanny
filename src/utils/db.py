import json
import os
import threading
from pathlib import Path

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = Path(__file__).parent.parent / 'db.json'
            self.ensure_db_exists()
            self.initialized = True

    def ensure_db_exists(self):
        """Create db.json if it doesn't exist"""
        if not self.db_path.exists():
            self.db_path.write_text('{}')

    def get(self, key, default=None):
        """Get a value from the database"""
        with self._lock:
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                return data.get(key, default)
            except json.JSONDecodeError:
                return default

    def set(self, key, value):
        """Set a value in the database"""
        with self._lock:
            try:
                # Read existing data
                if self.db_path.exists():
                    with open(self.db_path, 'r') as f:
                        data = json.load(f)
                else:
                    data = {}
                
                # Update data
                data[key] = value
                
                # Write back to file
                with open(self.db_path, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                return True
            except Exception as e:
                print(f"Error setting database value: {e}")
                return False

    def update(self, key, value_dict):
        """Update a dictionary in the database"""
        with self._lock:
            current = self.get(key, {})
            if isinstance(current, dict) and isinstance(value_dict, dict):
                current.update(value_dict)
                return self.set(key, current)
            return False 