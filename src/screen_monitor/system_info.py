import time
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
        

if __name__ == "__main__":
    st = SystemMonitor()
    time.sleep(2.6)
    print(st.get_idle_time())
