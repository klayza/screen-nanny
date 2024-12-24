from datetime import datetime
from PIL import ImageGrab
import os

class ScreenCapture:
    def __init__(self, save_dir="captures"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
    
    def capture(self):
        """Take a screenshot and save it with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot = ImageGrab.grab()
        
        # Save with timestamp
        filepath = os.path.join(self.save_dir, f"screen_{timestamp}.png")
        screenshot.save(filepath)
        
        return filepath 