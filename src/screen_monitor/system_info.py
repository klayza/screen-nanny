import time
import psutil
import platform
from datetime import datetime
import win32gui
import win32process
import tkinter as tk
import keyboard
from utils.db import Database
from utils.logger import ActivityLogger

class SystemMonitor:
    # Constants for garbage collection
    CLEANUP_INTERVAL = 1800  # 30 minutes in seconds
    MIN_DURATION_FOR_KEEP = 60  # 1 minute in seconds
    MIN_DURATION_FOR_ACTIVITY = 300  # 5 minutes in seconds

    # CLEANUP_INTERVAL = 10  # 30 minutes in seconds
    # MIN_DURATION_FOR_KEEP = 5  # 1 minute in seconds
    # MIN_DURATION_FOR_ACTIVITY = 5  # 5 minutes in seconds

    def __init__(self):
        self.window_durations = {}
        self.current_window_start = None
        self.current_window_title = None
        self.last_cleanup_time = time.time()
        self.db = Database()
        self.logger = ActivityLogger()
        
        # Restore window durations from db
        stored_durations = self.db.get('window_durations', {})
        self.window_durations = stored_durations

    def get_active_window_info(self):
        """Get information about the currently active window"""
        try:
            window = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(window)
            window_title = win32gui.GetWindowText(window)
            process = psutil.Process(pid)
            
            return {
                "window_title": window_title,
                "process_name": process.name(),
                "pid": pid,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_system_metrics(self):
        """Get general system metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "timestamp": datetime.now().isoformat()
        } 
    
    def get_idle_time(self):
        """Returns the number of seconds since last user input"""
        if platform.system() == "Windows":
            return self._get_idle_time_windows()
        elif platform.system() == "Darwin":  # macOS
            return self._get_idle_time_macos()
        elif platform.system() == "Linux":
            return self._get_idle_time_linux()
        return 0

    def _get_idle_time_windows(self):
        from ctypes import Structure, windll, c_uint, sizeof, byref
        
        class LASTINPUTINFO(Structure):
            _fields_ = [
                ('cbSize', c_uint),
                ('dwTime', c_uint),
            ]
        
        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = sizeof(lastInputInfo)
        windll.user32.GetLastInputInfo(byref(lastInputInfo))
        millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
        return millis / 1000.0  # Convert to seconds

    def _get_idle_time_macos(self):
        # Requires pyobjc-framework-Quartz
        try:
            import Quartz
            return Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateHIDSystemState,
                Quartz.kCGAnyInputEventType
            )
        except ImportError:
            return 0

    def _get_idle_time_linux(self):
        try:
            import subprocess
            output = subprocess.check_output(['xprintidle']).decode('utf-8')
            return float(output) / 1000.0  # Convert to seconds
        except:
            return 0
        
    def cleanup_window_durations(self):
        """Clean up window durations and save significant ones to activity data"""
        current_time = time.time()
        
        # Only run cleanup every CLEANUP_INTERVAL seconds
        if current_time - self.last_cleanup_time < self.CLEANUP_INTERVAL:
            return
            
        # Remove windows with less than minimum duration
        self.window_durations = {
            title: data for title, data in self.window_durations.items()
            if data['total'] >= self.MIN_DURATION_FOR_KEEP
        }
        
        # Save to activity data if duration exceeds threshold
        significant_windows = {
            title: data for title, data in self.window_durations.items()
            if data['total'] >= self.MIN_DURATION_FOR_ACTIVITY
        }
        
        if significant_windows:
            self.logger.log_activity("window_durations", significant_windows)
        
        # Save current state to db
        self.db.set('window_durations', self.window_durations)
        
        self.last_cleanup_time = current_time

    def update_window_info(self):
        """Update window information and handle garbage collection"""
        try:
            window = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(window)
            current_time = time.time()
            
            # Handle window switch
            if window_title != self.current_window_title:
                # Update previous window duration if exists
                if self.current_window_title and self.current_window_start:
                    duration = int(current_time - self.current_window_start)
                    # Ensure window exists in durations
                    if self.current_window_title not in self.window_durations:
                        self.window_durations[self.current_window_title] = {
                            'total': 0,
                            'consecutive': 0
                        }
                    self.window_durations[self.current_window_title]['total'] += duration
                    self.window_durations[self.current_window_title]['consecutive'] = 0
                
                # Initialize new window if needed
                if window_title not in self.window_durations:
                    self.window_durations[window_title] = {
                        'total': 0,
                        'consecutive': 0
                    }
                
                self.current_window_start = current_time
                self.current_window_title = window_title
            
            # Update consecutive duration for current window
            if self.current_window_title:
                
                # Add defensive check
                if self.current_window_title not in self.window_durations:
                    print(f"Warning: Current window not in durations: {self.current_window_title}")
                    self.window_durations[self.current_window_title] = {
                        'total': 0,
                        'consecutive': 0
                    }
                
                consecutive_duration = current_time - self.current_window_start
                self.window_durations[self.current_window_title]['consecutive'] = int(consecutive_duration)
            
            # Run cleanup if needed
            self.cleanup_window_durations()
            
            return {
                "window_title": window_title,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error updating window info: {e}")
            print(f"Current window title: {window_title if 'window_title' in locals() else 'N/A'}")
            print(f"Window durations: {self.window_durations}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

    def get_window_durations(self, window_title):
        """Get the total and consecutive duration for a window"""
        if window_title in self.window_durations:
            return self.window_durations[window_title]
        return {'total': 0, 'consecutive': 0}

    def pretty_print_window_times(self, min_total=0, max_items=-1):
        # Filter and sort windows by total duration
        sorted_windows = sorted(
            [(window, data) for window, data in self.window_durations.items() if data['total'] >= min_total],
            key=lambda x: x[1]['total'],
            reverse=True
        )
        
        # Limit the number of items if max_items is set
        if max_items != -1:
            sorted_windows = sorted_windows[:max_items]
        
        # Print each window's info
        for window, data in sorted_windows:
            print(f"[T:{data['total']}s][C:{data['consecutive']}s]{window}")


if __name__ == "__main__":
    st = SystemMonitor()
    while True:
        st.update_window_info()
        time.sleep(1)
        st.pretty_print_window_times(max_items=3)
        print("=============")