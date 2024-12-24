import customtkinter as ctk
import threading
import queue

class ModalWindow:
    def __init__(self):
        self.active_window = None
        self.message_queue = queue.Queue()
        self.window = None
        
        # Start the message processing thread
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def show_message(self, message, duration=5):
        """Queue a message to be shown"""
        self.message_queue.put((message, duration))
    
    def _process_messages(self):
        """Process messages from the queue"""
        # Create the root window in the main thread
        self.window = ctk.CTk()
        self.window.withdraw()  # Hide the root window
        
        def check_queue():
            try:
                while True:
                    message, duration = self.message_queue.get_nowait()
                    self._create_modal(message, duration)
            except queue.Empty:
                pass
            
            # Check again after 100ms
            self.window.after(100, check_queue)
        
        # Start checking the queue
        check_queue()
        
        # Start the main loop
        self.window.mainloop()
    
    def _create_modal(self, message, duration):
        """Create and show a modal window"""
        # Close any existing modal
        if self.active_window:
            self.active_window.destroy()
        
        # Create new window
        modal = ctk.CTkToplevel(self.window)
        self.active_window = modal
        
        # Configure window
        modal.attributes('-topmost', True)
        modal.attributes('-fullscreen', True)
        modal.configure(fg_color='#2B2B2B')
        
        # Add message
        label = ctk.CTkLabel(
            modal,
            text=message,
            font=('Arial', 24),
            text_color='white',
            wraplength=800
        )
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        # Add countdown label
        countdown_label = ctk.CTkLabel(
            modal,
            text=f"Closing in {duration} seconds...",
            font=('Arial', 14),
            text_color='white'
        )
        countdown_label.place(relx=0.5, rely=0.6, anchor='center')
        
        # Add initially hidden close button
        close_btn = ctk.CTkButton(
            modal,
            text="Close",
            command=modal.destroy
        )
        close_btn.place(relx=0.5, rely=0.7, anchor='center')
        close_btn.place_forget()  # Hide initially
        
        def update_countdown(remaining):
            if remaining > 0:
                countdown_label.configure(text=f"Closing in {remaining} seconds...")
                modal.after(1000, update_countdown, remaining - 1)
            else:
                countdown_label.configure(text="You can close this window now")
                close_btn.place(relx=0.5, rely=0.7, anchor='center')  # Show close button
        
        # Start countdown
        update_countdown(duration)
        
        # Auto-close after duration
        modal.after(duration * 1000, modal.destroy)