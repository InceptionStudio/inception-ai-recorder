import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import threading
import signal
import sys
from typing import Dict, List
from .audio_manager import AudioManager, AudioDevice

class WaveformWidget:
    """Widget for displaying waveform and level meter"""
    
    def __init__(self, parent, device_id: int, device_name: str):
        self.device_id = device_id
        self.device_name = device_name
        
        # Create frame for this waveform
        self.frame = ttk.Frame(parent)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(6, 1.5), dpi=80, facecolor='black')
        self.axis = self.figure.add_subplot(111, facecolor='black')
        self.axis.set_xlim(0, 100)
        self.axis.set_ylim(-1.1, 1.1)
        self.axis.set_xticks([])
        self.axis.set_yticks([])
        
        # Initialize empty line for waveform
        self.line, = self.axis.plot([], [], 'g-', linewidth=1.5)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, self.frame)
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Level meter
        self.level_var = tk.DoubleVar()
        self.level_progress = ttk.Progressbar(
            self.frame, 
            orient='vertical', 
            length=100,
            mode='determinate',
            variable=self.level_var,
            maximum=100
        )
        self.level_progress.pack(side=tk.RIGHT, padx=5)
        
        # Initialize empty waveform
        self.update_waveform([])
        self.update_level(0.0)
    
    def update_waveform(self, data: List[float]):
        """Update waveform display"""
        if data:
            x_data = np.linspace(0, 100, len(data))
            self.line.set_data(x_data, data)
        else:
            # Show flat line when no data
            self.line.set_data([0, 100], [0, 0])
        
        try:
            self.canvas.draw_idle()
        except:
            pass  # Ignore drawing errors
    
    def update_level(self, level: float):
        """Update level meter"""
        level_percent = min(100.0, level * 100.0)
        self.level_var.set(level_percent)
        
        # Change color based on level
        if level > 0.8:
            style = 'red.Horizontal.TProgressbar'
        elif level > 0.5:
            style = 'yellow.Horizontal.TProgressbar'
        else:
            style = 'green.Horizontal.TProgressbar'
        
        try:
            self.level_progress.configure(style=style)
        except:
            pass  # Ignore style errors

class DeviceRow:
    """Represents a single device row in the GUI"""
    
    def __init__(self, parent, device: AudioDevice, audio_manager: AudioManager):
        self.device = device
        self.audio_manager = audio_manager
        
        # Create main frame for this device
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Left side - device controls
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Device selection checkbox
        self.selected_var = tk.BooleanVar()
        self.checkbox = ttk.Checkbutton(
            control_frame,
            variable=self.selected_var,
            command=self.on_selection_changed
        )
        self.checkbox.pack(anchor=tk.W)
        
        # Device name and info
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(fill=tk.X, pady=2)
        
        device_label = ttk.Label(info_frame, text=device.name, font=('Courier', 10))
        device_label.pack(anchor=tk.W)
        
        channels_label = ttk.Label(info_frame, text=f"Channels: {device.max_input_channels}", 
                                 font=('Arial', 8), foreground='gray')
        channels_label.pack(anchor=tk.W)
        
        # Custom label entry
        label_frame = ttk.Frame(control_frame)
        label_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(label_frame, text="Label:", font=('Arial', 8)).pack(side=tk.LEFT)
        
        self.label_var = tk.StringVar()
        self.label_var.set(audio_manager.get_device_label(device.id))
        self.label_entry = ttk.Entry(label_frame, textvariable=self.label_var, width=15)
        self.label_entry.pack(side=tk.LEFT, padx=2)
        self.label_entry.bind('<KeyRelease>', self.on_label_changed)
        
        # Right side - waveform and level
        self.waveform_widget = WaveformWidget(self.frame, device.id, device.name)
        self.waveform_widget.frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
    
    def on_selection_changed(self):
        """Handle device selection change"""
        selected = self.selected_var.get()
        self.audio_manager.set_device_selected(self.device.id, selected)
        
        # Enable/disable waveform based on selection
        if selected:
            self.waveform_widget.axis.set_facecolor('black')
        else:
            self.waveform_widget.axis.set_facecolor('gray')
            self.waveform_widget.update_waveform([])
            self.waveform_widget.update_level(0.0)
        
        self.waveform_widget.canvas.draw_idle()
    
    def on_label_changed(self, event=None):
        """Handle label text change"""
        label = self.label_var.get()
        self.audio_manager.set_device_label(self.device.id, label)
    
    def update_audio_data(self, level: float, waveform: List[float]):
        """Update audio level and waveform"""
        if self.selected_var.get():  # Only update if device is selected
            self.waveform_widget.update_level(level)
            self.waveform_widget.update_waveform(waveform)
    
    def set_controls_enabled(self, enabled: bool):
        """Enable or disable device controls"""
        state = "normal" if enabled else "disabled"
        self.checkbox.config(state=state)
        self.label_entry.config(state=state)

class MultitrackRecorderGUI:
    """Main GUI application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Multitrack Audio Recorder")
        self.root.geometry("900x600")
        
        # Initialize audio manager
        self.audio_manager = AudioManager()
        self.audio_manager.set_level_callback(self.on_level_update)
        self.audio_manager.set_waveform_callback(self.on_waveform_update)
        
        # Device rows
        self.device_rows: Dict[int, DeviceRow] = {}
        
        # Shutdown flag
        self._shutting_down = False
        
        self.create_widgets()
        self.populate_devices()
        
        # Set up cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Style configuration for progressbars
        self.setup_styles()
    
    def setup_styles(self):
        """Set up custom styles for progressbars"""
        style = ttk.Style()
        
        # Configure colored progressbar styles
        style.configure('green.Vertical.TProgressbar', background='green')
        style.configure('yellow.Vertical.TProgressbar', background='yellow')
        style.configure('red.Vertical.TProgressbar', background='red')
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Main title
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(title_frame, text="Multitrack Audio Recorder", 
                              font=('Arial', 16, 'bold'))
        title_label.pack()
        
        # Export directory selection
        export_frame = ttk.Frame(self.root)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(export_frame, text="Choose Export Folder", 
                  command=self.choose_export_directory).pack(side=tk.LEFT)
        
        self.export_label = ttk.Label(export_frame, text="No folder selected", 
                                    foreground='orange')
        self.export_label.pack(side=tk.LEFT, padx=10)
        
        # Device controls
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(controls_frame, text="Input Devices", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        self.refresh_button = ttk.Button(controls_frame, text="Refresh", 
                                        command=self.refresh_devices)
        self.refresh_button.pack(side=tk.RIGHT)
        
        self.device_count_label = ttk.Label(controls_frame, text="", 
                                          font=('Arial', 9), foreground='gray')
        self.device_count_label.pack(side=tk.RIGHT, padx=10)
        
        # Scrollable frame for devices
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")
        
        # Recording controls
        recording_frame = ttk.Frame(self.root)
        recording_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.record_button = ttk.Button(recording_frame, text="Start Recording", 
                                      command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT)
        
        self.recording_status = ttk.Label(recording_frame, text="")
        self.recording_status.pack(side=tk.LEFT, padx=10)
    
    def populate_devices(self):
        """Populate device list"""
        # Clear existing device rows
        for row in self.device_rows.values():
            row.frame.destroy()
        self.device_rows.clear()
        
        # Add device rows
        devices = self.audio_manager.get_input_devices()
        for device in devices:
            device_row = DeviceRow(self.scrollable_frame, device, self.audio_manager)
            self.device_rows[device.id] = device_row
        
        # Update device count
        self.device_count_label.config(text=f"Available devices: {len(devices)}")
        
        if len(devices) == 0:
            no_devices_label = ttk.Label(self.scrollable_frame, 
                                       text="No input devices found", 
                                       foreground='red')
            no_devices_label.pack(pady=20)
    
    def set_device_controls_enabled(self, enabled: bool):
        """Enable or disable all device controls"""
        for device_row in self.device_rows.values():
            device_row.set_controls_enabled(enabled)
        # Also disable/enable refresh button during recording
        if hasattr(self, 'refresh_button'):
            self.refresh_button.config(state="normal" if enabled else "disabled")
    
    def choose_export_directory(self):
        """Choose export directory"""
        directory = filedialog.askdirectory(title="Select Export Folder")
        if directory:
            self.audio_manager.set_export_directory(directory)
            self.export_label.config(text=f"Export to: {directory}", foreground='black')
    
    def refresh_devices(self):
        """Refresh device list with timeout protection"""
        if self.audio_manager.is_recording():
            messagebox.showwarning("Warning", "Cannot refresh devices while recording")
            return
        
        # Show progress/busy state
        original_text = self.refresh_button.cget("text") if hasattr(self, 'refresh_button') else "Refresh"
        
        try:
            print("🔄 GUI: Starting device refresh...")
            
            # Update button to show activity
            if hasattr(self, 'refresh_button'):
                self.refresh_button.config(text="Refreshing...", state="disabled")
                self.root.update_idletasks()
            
            # Clear any pending UI callbacks that might reference old device IDs
            self.root.after_idle(lambda: None)  # Clear idle queue
            
            # Refresh audio manager (this now has timeout protection)
            self.audio_manager.refresh_devices()
            
            # Update UI
            self.populate_devices()
            
            print("✅ GUI: Device refresh completed")
            
        except RuntimeError as e:
            # This is our timeout/serious error - suggest restart
            print(f"❌ GUI: Critical error during refresh: {e}")
            messagebox.showerror("Critical Error", 
                               f"Device refresh failed: {e}\n\n"
                               "The application may be in an unstable state. "
                               "Consider restarting the application.")
            
        except Exception as e:
            print(f"❌ GUI: Error during refresh: {e}")
            messagebox.showerror("Error", f"Failed to refresh devices: {e}")
            
            # Try to recover by repopulating with current state
            try:
                self.populate_devices()
            except Exception as recovery_error:
                print(f"❌ GUI: Failed to recover from refresh error: {recovery_error}")
        
        finally:
            # Restore button state
            if hasattr(self, 'refresh_button'):
                self.refresh_button.config(text=original_text, state="normal")
    
    def toggle_recording(self):
        """Toggle recording state"""
        if self.audio_manager.is_recording():
            try:
                self.audio_manager.stop_recording()
                self.record_button.config(text="Start Recording")
                self.recording_status.config(text="", foreground='black')
                # Re-enable device controls when recording stops
                self.set_device_controls_enabled(True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop recording: {e}")
        else:
            try:
                selected_devices = self.audio_manager.get_selected_device_ids()
                if not selected_devices:
                    messagebox.showwarning("Warning", "No devices selected for recording")
                    return
                
                if not self.audio_manager.get_export_directory():
                    messagebox.showwarning("Warning", "Please select an export directory first")
                    return
                
                self.audio_manager.start_recording()
                self.record_button.config(text="Stop Recording")
                self.recording_status.config(text="Recording...", foreground='red')
                # Disable device controls when recording starts
                self.set_device_controls_enabled(False)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start recording: {e}")
    
    def on_level_update(self, device_id: int, level: float):
        """Handle audio level updates"""
        # Check if we're shutting down or if root window is being destroyed
        try:
            if self._shutting_down or not hasattr(self, 'root') or not self.root.winfo_exists():
                return
                
            def safe_update():
                try:
                    # Double-check during execution
                    if (hasattr(self, 'root') and self.root.winfo_exists() and 
                        device_id in self.device_rows):
                        self.device_rows[device_id].waveform_widget.update_level(level)
                except Exception as e:
                    pass  # Silently ignore UI update errors during shutdown
                
            self.root.after_idle(safe_update)
        except Exception as e:
            pass  # Silently ignore callback errors during shutdown
    
    def on_waveform_update(self, device_id: int, waveform: List[float]):
        """Handle waveform data updates"""
        # Check if we're shutting down or if root window is being destroyed
        try:
            if self._shutting_down or not hasattr(self, 'root') or not self.root.winfo_exists():
                return
                
            def safe_update():
                try:
                    # Double-check during execution
                    if (hasattr(self, 'root') and self.root.winfo_exists() and 
                        device_id in self.device_rows):
                        self.device_rows[device_id].waveform_widget.update_waveform(waveform)
                except Exception as e:
                    pass  # Silently ignore UI update errors during shutdown
            
            self.root.after_idle(safe_update)
        except Exception as e:
            pass  # Silently ignore callback errors during shutdown
    
    def on_closing(self):
        """Handle application closing"""
        # Set shutdown flag to prevent new callbacks
        self._shutting_down = True
        
        try:
            print("🔄 Starting graceful shutdown...")
            
            # Step 1: Stop recording if active
            if self.audio_manager.is_recording():
                print("🛑 Stopping recording...")
                self.audio_manager.stop_recording()
                self.record_button.config(text="Start Recording")
                self.recording_status.config(text="", foreground='black')
                print("✅ Recording stopped")
            
            # Step 2: Uncheck all device checkboxes (turn off all listeners)
            print("🔌 Turning off all device listeners...")
            for device_id, device_row in self.device_rows.items():
                if device_row.selected_var.get():
                    device_row.selected_var.set(False)
                    self.audio_manager.set_device_selected(device_id, False)
            print("✅ All device listeners turned off")
            
            # Step 3: Clean up audio manager
            print("🧹 Cleaning up audio resources...")
            self.audio_manager.cleanup()
            print("✅ Audio cleanup completed")
        except Exception as e:
            print(f"Error during shutdown: {e}")

        def shutdown():
            try:
                # Step 4: Force update UI to ensure all changes are visible
                self.root.update_idletasks()
                
            except Exception as e:
                print(f"Error during shutdown: {e}")
            finally:
                print("🚪 Closing application window...")
                self.root.destroy()
                
                # Add a small delay to ensure cleanup is complete
                import time
                time.sleep(0.1)
                
                # Force exit to ensure process terminates
                import sys
                import os
                print("🔄 Exiting application...")
                sys.exit(0)

        self.root.after_idle(shutdown)

    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()

def main():
    """Main entry point"""
    app = MultitrackRecorderGUI()
    app.run()

if __name__ == "__main__":
    main()