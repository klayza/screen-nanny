import time
from screen_monitor.capture import ScreenCapture
from screen_monitor.system_info import SystemMonitor
from utils.logger import ActivityLogger
from ui.modal import ModalWindow
from ui.focus_dialog import FocusDialog
from pynput import keyboard
import threading
from ai.vision_analyzer import VisionAnalyzer

class ScreenNanny:
    def __init__(self, capture_interval=60, idle_threshold=30):
        self.capture_interval = capture_interval
        self.screen_capture = ScreenCapture()
        self.system_monitor = SystemMonitor()
        self.logger = ActivityLogger()
        self.modal = ModalWindow()
        self.focus_dialog = FocusDialog()
        self.focus_mode = False
        self.focus_description = None
        self.vision_analyzer = VisionAnalyzer()
        self.idle_threshold = idle_threshold
        
        # Start hotkey listener
        self._setup_hotkey()
    
    def _setup_hotkey(self):
        """Setup the hotkey listener"""
        def on_press(key):
            try:
                # Check for Ctrl+Shift+F
                if key == keyboard.Key.f and keyboard.Key.ctrl in self.current_keys and keyboard.Key.shift in self.current_keys:
                    self.show_focus_dialog()
            except AttributeError:
                pass

        def on_release(key):
            try:
                if key in self.current_keys:
                    self.current_keys.remove(key)
            except KeyError:
                pass

        self.current_keys = set()
        
        # Start listener in a non-blocking way
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
    
    def show_focus_dialog(self):
        """Show the focus mode dialog"""
        def on_focus_set(description):
            self.focus_mode = True
            self.focus_description = description
            self.modal.show_message(
                f"Focus Mode Activated!\n\nYour Goal: {description}",
                duration=3
            )
            self.logger.log_activity("focus_mode_start", {"description": description})
        
        self.focus_dialog.show_dialog(on_focus_set)
    
    def analyze_and_warn(self, screenshot_path, window_info):
        """Analyze activity and show warning if distracted"""
        # Use window title analysis by default (cheaper)
        analysis = self.vision_analyzer.analyze_window_title(
            window_info,
            self.focus_description if self.focus_mode else None
        )
        
        # Log the analysis and token usage
        self.logger.log_activity("ai_analysis", {
            "analysis": analysis,
            "token_usage": self.vision_analyzer.get_token_usage(),
            "analysis_type": "window_title"
        })

        print(analysis)
        
        if analysis["is_distracted"]:
            message = "⚠️ Distraction Detected!\n\n"
            if self.focus_mode:
                message += f"Remember, you're supposed to be focusing on:\n{self.focus_description}\n\n"
            message += f"Reason: {analysis['reason']}"
            
            self.modal.show_message(message)
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        try:
            while True:
                # Check if system is idle
                idle_time = self.system_monitor.get_idle_time()
                is_idle = int(idle_time) > self.idle_threshold

                if not is_idle:
                    # Only monitor if system is active
                    screenshot_path = self.screen_capture.capture()
                    window_info = self.system_monitor.get_active_window_info()
                    
                    # Log everything
                    self.logger.log_activity("screenshot", {"path": screenshot_path})
                    self.logger.log_activity("window_info", window_info)
                    
                    # Analyze using window title
                    self.analyze_and_warn(screenshot_path, window_info)
                else:
                    self.logger.log_activity("system_idle", {"idle_time": idle_time})
                    print(f"System idle for {idle_time} seconds")
                
                time.sleep(self.capture_interval)
                
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        except Exception as e:
            print(f"Error during monitoring: {str(e)}")

if __name__ == "__main__":
    nanny = ScreenNanny()
    nanny.start_monitoring() 