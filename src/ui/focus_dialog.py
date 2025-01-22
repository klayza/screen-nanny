import customtkinter as ctk

class FocusDialog:
    def __init__(self):
        self.window = None
        self.callback = None
        self.cancel_callback = None
        
    def show_dialog(self, on_focus_set, is_active=False, current_focus=None, on_cancel=None):
        """Show the focus session dialog"""
        self.callback = on_focus_set
        self.cancel_callback = on_cancel
        
        # Create window
        window = ctk.CTk()
        self.window = window
        window.title("Focus Session")
        window.geometry("500x300")
        window.attributes('-topmost', True)
        
        if not is_active:
            # Show start focus session dialog
            label = ctk.CTkLabel(
                window,
                text="What are you planning to work on?",
                font=('Arial', 16)
            )
            label.pack(pady=20)
            
            # Add text area
            self.text_area = ctk.CTkTextbox(
                window,
                width=400,
                height=100
            )
            self.text_area.pack(pady=20)
            
            # Add buttons
            button_frame = ctk.CTkFrame(window)
            button_frame.pack(pady=20)
            
            start_btn = ctk.CTkButton(
                button_frame,
                text="Start Focus Session",
                command=self._on_submit
            )
            start_btn.pack(side='left', padx=10)
            
            cancel_btn = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=window.destroy
            )
            cancel_btn.pack(side='left', padx=10)
        else:
            # Show active focus session dialog
            label = ctk.CTkLabel(
                window,
                text="Current Focus Session",
                font=('Arial', 20, 'bold')
            )
            label.pack(pady=20)
            
            current_focus_label = ctk.CTkLabel(
                window,
                text=current_focus,
                font=('Arial', 16),
                wraplength=400
            )
            current_focus_label.pack(pady=20)
            
            # Add buttons
            button_frame = ctk.CTkFrame(window)
            button_frame.pack(pady=20)
            
            end_btn = ctk.CTkButton(
                button_frame,
                text="End Focus Session",
                command=self._on_cancel,
                fg_color="red",
                hover_color="darkred"
            )
            end_btn.pack(side='left', padx=10)
            
            keep_btn = ctk.CTkButton(
                button_frame,
                text="Keep Focusing",
                command=window.destroy
            )
            keep_btn.pack(side='left', padx=10)
        
        window.mainloop()
    
    def cleanup(self):
        """Cleanup method to properly close the dialog"""
        if self.window and self.window.winfo_exists():
            self.window.quit()
            self.window.destroy()
            self.window = None
    
    def _safe_destroy(self):
        """Safely destroy the window"""
        try:
            if self.window and self.window.winfo_exists():
                self.window.quit()
                self.window.destroy()
                self.window = None
        except Exception as e:
            print(f"Error destroying focus dialog: {e}")
    
    def _on_submit(self):
        """Handle focus session submission"""
        focus_description = self.text_area.get("1.0", "end-1c")
        if self.callback:
            self.callback(focus_description)
        self._safe_destroy()
    
    def _on_cancel(self):
        """Handle focus session cancellation"""
        if self.cancel_callback:
            self.cancel_callback()
        self._safe_destroy() 