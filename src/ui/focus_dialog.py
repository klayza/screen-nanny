import customtkinter as ctk

class FocusDialog:
    def __init__(self):
        self.window = None
        self.callback = None
        
    def show_dialog(self, on_focus_set):
        """Show the focus session dialog"""
        self.callback = on_focus_set
        
        # Create window
        window = ctk.CTk()
        self.window = window
        window.title("Start Focus Session")
        window.geometry("500x300")
        window.attributes('-topmost', True)
        
        # Add description label
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
        
        window.mainloop()
    
    def _on_submit(self):
        """Handle focus session submission"""
        focus_description = self.text_area.get("1.0", "end-1c")
        if self.callback:
            self.callback(focus_description)
        self.window.destroy() 