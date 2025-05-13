import time
from screen_monitor.capture import ScreenCapture
from screen_monitor.system_info import SystemMonitor
from utils.logger import ActivityLogger
from ui.modal import ModalWindow
from ui.focus_dialog import FocusDialog
import keyboard
import threading
from ai.vision_analyzer import VisionAnalyzer
from utils.db import Database
from utils.stats import UserStats

class ScreenNanny:
    def __init__(self, log_interval=5, analyze_interval=60, idle_threshold=30, ai_enabled=True):
        self.analyze_interval = analyze_interval
        self.log_interval = log_interval
        self.ai_enabled=ai_enabled
        self.screen_capture = ScreenCapture()
        self.system_monitor = SystemMonitor()
        self.logger = ActivityLogger()
        self.modal = ModalWindow()
        self.focus_dialog = FocusDialog()
        self.stats = UserStats(self.logger)
        self.focus_mode = False
        self.focus_description = None
        self.screenshot_enabled = False
        self.vision_analyzer = VisionAnalyzer()
        self.idle_threshold = idle_threshold
        self.db = Database()  # Initialize database
        
        # Restore focus mode state if it exists
        focus_state = self.db.get('focus_state', {})
        self.focus_mode = focus_state.get('active', False)
        self.focus_description = focus_state.get('description', None)
        
        # Start hotkey listener
        self._setup_hotkey()
        
        if not ai_enabled:
            print("AI mode disabled. Only logging window information.")
    
    def _setup_hotkey(self):
        """Setup the hotkey listener"""
        keyboard.add_hotkey('ctrl+alt+f', self.toggle_focus_dialog)
    
    def toggle_focus_dialog(self):
        """Toggle between starting and ending focus mode"""
        if not self.focus_mode:
            self.show_focus_dialog()
        else:
            self.show_cancel_dialog()
    
    def show_focus_dialog(self):
        """Show the focus mode dialog"""
        def on_focus_set(description):
            self.focus_mode = True
            self.focus_description = description
            # Save focus state to db
            self.db.set('focus_state', {
                'active': True,
                'description': description
            })
            self.logger.log_activity("focus_mode_start", {"description": description})
        
        self.focus_dialog.show_dialog(on_focus_set)
    
    def show_cancel_dialog(self):
        """Show the cancel focus mode dialog"""
        def on_cancel():
            self.focus_mode = False
            self.focus_description = None
            # Clear focus state from db
            self.db.set('focus_state', {
                'active': False,
                'description': None
            })
            self.logger.log_activity("focus_mode_end", {})
        
        self.focus_dialog.show_dialog(
            on_focus_set=None,  # Not needed for cancel dialog
            is_active=True,
            current_focus=self.focus_description,
            on_cancel=on_cancel
        )
    
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
            message = "Focus\n\n"
            if self.focus_mode:
                message += f"Remember, you're supposed to be focusing on:\n{self.focus_description}\n\n"
            message += f"Reason: {analysis['reason']}"
            
            self.modal.show_message(message, duration=analysis["timeout"])
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        try:
            while True:
                # Check if system is idle
                idle_time = self.system_monitor.get_idle_time()
                is_idle = int(idle_time) > self.idle_threshold
                
                # When the user is present
                if not is_idle:
                    screenshot_path = None
                    
                    if self.screenshot_enabled:
                        screenshot_path = self.screen_capture.capture()
                        self.logger.log_activity("screenshot", {"path": screenshot_path})

                    # Get the window info
                    window_info = self.system_monitor.get_active_window_info()
                    self.logger.log_activity("window_info", window_info)
                    print(window_info)
                    
                    #TODO: give the ai self.stats.get_most_used_windows(10, 3)
                    
                    # Analyze using window title
                    if self.ai_enabled:
                        self.analyze_and_warn(screenshot_path, window_info)
    
                    # Keep logging until we need to analyze the screen again
                    for _ in range(self.analyze_interval):
                        self.logger.log_activity("window_info", self.system_monitor.get_active_window_info())
                        time.sleep(1)
                else:
                    print(f"System idle for {idle_time} seconds")
                    time.sleep(self.analyze_interval)
                
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        except Exception as e:
            print(f"Error during monitoring: {str(e)}")
            import traceback
            print(traceback.format_exc())

if __name__ == "__main__":
    debug = False
    
    if debug:
        nanny = ScreenNanny(ai_enabled=False)
        # nanny.start_monitoring() 
        print(nanny.stats.get_most_used_windows(10, 3))

    else:
        nanny = ScreenNanny(ai_enabled=True)
        nanny.start_monitoring() 