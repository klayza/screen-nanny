import psutil
import platform
from datetime import datetime
import win32gui
import win32process

class SystemMonitor:
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