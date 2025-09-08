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
import os
from typing import Dict, List
from .audio_manager import AudioManager, AudioDevice
from .settings_manager import SettingsManager

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
        
        # Remove margins to eliminate black horizontal bars
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
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
        
        channels_label = ttk.Label(info_frame, text=f"{device.host_api}, ID {device.id}", 
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
        
        # Gain control
        gain_frame = ttk.Frame(control_frame)
        gain_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(gain_frame, text="Gain:", font=('Arial', 8)).pack(side=tk.LEFT)
        
        self.gain_var = tk.DoubleVar()
        self.gain_var.set(audio_manager.get_device_gain(device.id))
        self.gain_slider = ttk.Scale(
            gain_frame,
            from_=-24.0,
            to=24.0,
            orient=tk.HORIZONTAL,
            variable=self.gain_var,
            command=self.on_gain_changed,
            length=120
        )
        self.gain_slider.pack(side=tk.LEFT, padx=2)
        
        self.gain_label = ttk.Label(gain_frame, text="0.0 dB", font=('Arial', 8), width=5)
        self.gain_label.pack(side=tk.LEFT, padx=2)
        
        # Auto gain label (clickable)
        self.auto_gain_label = ttk.Label(gain_frame, text="Auto", font=('Arial', 8), 
                                        foreground='blue', cursor='hand2')
        self.auto_gain_label.bind('<Button-1>', self.on_auto_gain_clicked)
        self.auto_gain_label.pack(side=tk.LEFT, padx=1)
        
        # Initialize gain label display
        self.on_gain_changed()
        
        # Right side - waveform and level
        self.waveform_widget = WaveformWidget(self.frame, device.id, device.name)
        self.waveform_widget.frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
    
    def on_selection_changed(self):
        """Handle device selection change"""
        selected = self.selected_var.get()
        self.audio_manager.set_device_selected(self.device.id, selected)
        
        # Clear waveform and level when deselected
        if not selected:
            self.waveform_widget.update_waveform([])
            self.waveform_widget.update_level(0.0)
        
        self.waveform_widget.canvas.draw_idle()
    
    def on_gain_changed(self, value=None):
        """Handle gain slider change"""
        gain_db = self.gain_var.get()
        self.audio_manager.set_device_gain(self.device.id, gain_db)
        # Update the gain label display
        self.gain_label.config(text=f"{gain_db:.1f} dB")
    
    def on_auto_gain_clicked(self, event=None):
        """Handle auto gain label click"""
        # Calculate optimal gain based on peak levels
        optimal_gain = self.audio_manager.calculate_auto_gain(self.device.id)
        
        if optimal_gain is not None:
            # Apply the calculated gain
            self.gain_var.set(optimal_gain)
            self.audio_manager.set_device_gain(self.device.id, optimal_gain)
            self.gain_label.config(text=f"{optimal_gain:.1f} dB")
            
            # Show feedback message
            peak_level, peak_count, sample_count = self.audio_manager.get_device_peak_info(self.device.id)
            clipping_pct = (peak_count / sample_count * 100) if sample_count > 0 else 0
            
            if clipping_pct > 1.0:
                message = f"Auto gain set to {optimal_gain:.1f} dB\nPeak: {peak_level:.1%}, Clipping: {clipping_pct:.1f}%"
            else:
                message = f"Auto gain set to {optimal_gain:.1f} dB\nPeak level: {peak_level:.1%}"
            
            # Show tooltip or status message (you could implement a status bar)
            print(f"Auto gain for device {self.device.id}: {message}")
        else:
            # No data available or gain would be too extreme
            peak_level, peak_count, sample_count = self.audio_manager.get_device_peak_info(self.device.id)
            if sample_count == 0:
                print("No audio data available for auto gain calculation")
            else:
                print(f"Auto gain not applied - peak level: {peak_level:.1%}, would require extreme gain adjustment")
    
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
        # Keep gain slider and auto label enabled during recording for real-time adjustment
        # self.gain_slider.config(state=state)
        # self.auto_gain_label remains enabled during recording
        self.label_entry.config(state=state)

class ConfigurationDialog:
    """Configuration dialog for export folder and Google Drive settings"""
    
    def __init__(self, parent, audio_manager: AudioManager, settings_manager: SettingsManager):
        self.audio_manager = audio_manager
        self.settings_manager = settings_manager
        self._initializing = True
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configuration")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        self.load_settings()
        
        # Mark initialization as complete
        self._initializing = False
        
        # Set up cleanup on dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Create the configuration dialog widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Configuration", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Export directory section
        export_frame = ttk.LabelFrame(main_frame, text="Export Settings", padding=15)
        export_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Export directory selection
        export_dir_frame = ttk.Frame(export_frame)
        export_dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(export_dir_frame, text="Choose Export Folder", 
                  command=self.choose_export_directory).pack(side=tk.LEFT)
        
        self.export_label = ttk.Label(export_dir_frame, text="No folder selected", 
                                    foreground='orange')
        self.export_label.pack(side=tk.LEFT, padx=10)
        
        
        # Google Drive configuration section
        drive_frame = ttk.LabelFrame(main_frame, text="Google Drive Upload", padding=15)
        drive_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Enable/disable Google Drive upload
        self.drive_enabled_var = tk.BooleanVar()
        self.drive_checkbox = ttk.Checkbutton(
            drive_frame, 
            text="Enable Google Drive Upload", 
            variable=self.drive_enabled_var,
            command=self.on_drive_enabled_changed
        )
        self.drive_checkbox.pack(anchor=tk.W, pady=(0, 10))
        
        # Google Drive folder ID
        folder_frame = ttk.Frame(drive_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(folder_frame, text="Folder ID:").pack(side=tk.LEFT)
        self.folder_id_var = tk.StringVar()
        self.folder_id_entry = ttk.Entry(folder_frame, textvariable=self.folder_id_var, width=30)
        self.folder_id_entry.pack(side=tk.LEFT, padx=5)
        self.folder_id_entry.bind('<KeyRelease>', self.on_folder_id_changed)
        
        # Folder validation button
        self.validate_folder_button = ttk.Button(folder_frame, text="Validate", 
                                                command=self.validate_folder_id)
        self.validate_folder_button.pack(side=tk.LEFT, padx=5)
        
        # Folder status label
        self.folder_status_label = ttk.Label(folder_frame, text="", font=('Arial', 8))
        self.folder_status_label.pack(side=tk.LEFT, padx=5)
        
        # Authentication section
        auth_frame = ttk.Frame(drive_frame)
        auth_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auth_button = ttk.Button(auth_frame, text="Authenticate Google Drive", 
                                     command=self.authenticate_google_drive)
        self.auth_button.pack(side=tk.LEFT)
        
        self.clear_auth_button = ttk.Button(auth_frame, text="Clear Auth", 
                                           command=self.clear_google_drive_auth)
        self.clear_auth_button.pack(side=tk.LEFT, padx=5)
        
        self.auth_status_label = ttk.Label(auth_frame, text="Not authenticated", 
                                          foreground='red')
        self.auth_status_label.pack(side=tk.LEFT, padx=10)
        
        # Help text
        help_text = ttk.Label(drive_frame, 
                             text="To get your folder ID: 1) Open Google Drive, 2) Navigate to your folder, 3) Copy the ID from the URL",
                             font=('Arial', 8), foreground='gray')
        help_text.pack(anchor=tk.W, pady=(10, 0))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Close button
        ttk.Button(buttons_frame, text="Close", command=self.on_closing).pack(side=tk.RIGHT)
    
    def load_settings(self):
        """Load current settings into the dialog"""
        try:
            # Load export directory
            export_dir = self.settings_manager.get_export_directory()
            if export_dir:
                self.export_label.config(text=f"Export to: {export_dir}", foreground='black')
            else:
                self.export_label.config(text="No folder selected", foreground='orange')
            
            
            # Load Google Drive settings
            self.drive_enabled_var.set(self.settings_manager.get_google_drive_enabled())
            
            folder_id = self.settings_manager.get_google_drive_folder_id()
            if folder_id:
                self.folder_id_var.set(folder_id)
            
            # Update authentication status
            self.update_google_drive_ui_state()
            
        except Exception as e:
            print(f"Error loading settings in configuration dialog: {e}")
    
    def choose_export_directory(self):
        """Choose export directory"""
        directory = filedialog.askdirectory(title="Select Export Folder")
        if directory:
            self.audio_manager.set_export_directory(directory)
            self.export_label.config(text=f"Export to: {directory}", foreground='black')
    
    def on_drive_enabled_changed(self):
        """Handle Google Drive enabled checkbox change"""
        enabled = self.drive_enabled_var.get()
        
        # Only update audio manager if not during initialization
        if not self._initializing:
            self.audio_manager.set_google_drive_enabled(enabled)
        
        # Enable/disable folder ID entry based on checkbox
        state = "normal" if enabled else "disabled"
        self.folder_id_entry.config(state=state)
        self.auth_button.config(state=state)
        self.validate_folder_button.config(state=state)
        self.clear_auth_button.config(state=state)
    
    def on_folder_id_changed(self, event=None):
        """Handle Google Drive folder ID change"""
        folder_id = self.folder_id_var.get().strip()
        if folder_id and not self._initializing:
            self.audio_manager.set_google_drive_folder_id(folder_id)
            # Clear status when typing
            self.folder_status_label.config(text="", foreground='black')
    
    def validate_folder_id(self):
        """Validate the Google Drive folder ID"""
        folder_id = self.folder_id_var.get().strip()
        
        if not folder_id:
            self.folder_status_label.config(text="Please enter a folder ID", foreground='red')
            return
        
        if not self.audio_manager.is_google_drive_authenticated():
            self.folder_status_label.config(text="Please authenticate first", foreground='red')
            return
        
        # Show progress
        self.validate_folder_button.config(text="Validating...", state="disabled")
        self.folder_status_label.config(text="Validating...", foreground='blue')
        self.dialog.update_idletasks()
        
        # Validate in background thread
        def validate_task():
            try:
                is_valid, message = self.audio_manager.validate_google_drive_folder_id(folder_id)
                
                # Update UI in main thread
                def update_ui():
                    if is_valid:
                        self.folder_status_label.config(text=message, foreground='green')
                        self.audio_manager.set_google_drive_folder_id(folder_id)
                    else:
                        self.folder_status_label.config(text=message, foreground='red')
                    
                    self.validate_folder_button.config(text="Validate", state="normal")
                
                self.dialog.after_idle(update_ui)
                
            except Exception as e:
                def update_ui_error():
                    self.folder_status_label.config(text=f"Validation error: {e}", foreground='red')
                    self.validate_folder_button.config(text="Validate", state="normal")
                
                self.dialog.after_idle(update_ui_error)
        
        # Run validation in background thread
        threading.Thread(target=validate_task, daemon=True).start()
    
    def authenticate_google_drive(self):
        """Authenticate with Google Drive"""
        try:
            # Check if credentials file exists
            if not os.path.exists("credentials.json"):
                messagebox.showerror("Error", 
                    "Google Drive credentials file 'credentials.json' not found.\n\n"
                    "Please download your OAuth2 credentials from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/\n"
                    "2. Create a new project or select existing one\n"
                    "3. Enable Google Drive API\n"
                    "4. Create OAuth2 credentials\n"
                    "5. Download as 'credentials.json' and place in this directory")
                return
            
            # Show progress
            self.auth_button.config(text="Authenticating...", state="disabled")
            self.dialog.update_idletasks()
            
            # Authenticate in a background thread
            def auth_task():
                try:
                    success = self.audio_manager.authenticate_google_drive()
                    
                    # Update UI in main thread
                    def update_ui():
                        if success:
                            self.auth_status_label.config(text="Authenticated", foreground='green')
                            messagebox.showinfo("Success", "Google Drive authentication successful!")
                        else:
                            self.auth_status_label.config(text="Authentication failed", foreground='red')
                            messagebox.showerror("Error", "Google Drive authentication failed. Please check your credentials.")
                        
                        self.auth_button.config(text="Authenticate Google Drive", state="normal")
                        
                        # Update the entire Google Drive UI state to ensure consistency
                        self.update_google_drive_ui_state()
                    
                    self.dialog.after_idle(update_ui)
                    
                except Exception as e:
                    def update_ui_error():
                        self.auth_status_label.config(text="Authentication failed", foreground='red')
                        self.auth_button.config(text="Authenticate Google Drive", state="normal")
                        messagebox.showerror("Error", f"Google Drive authentication failed: {e}")
                    
                    self.dialog.after_idle(update_ui_error)
            
            # Run authentication in background thread
            threading.Thread(target=auth_task, daemon=True).start()
            
        except Exception as e:
            self.auth_button.config(text="Authenticate Google Drive", state="normal")
            messagebox.showerror("Error", f"Failed to start authentication: {e}")
    
    def clear_google_drive_auth(self):
        """Clear Google Drive authentication"""
        try:
            result = messagebox.askyesno("Clear Authentication", 
                "This will clear your Google Drive authentication tokens.\n"
                "You will need to re-authenticate to use Google Drive upload.\n\n"
                "This is useful if you're having permission issues or need to\n"
                "re-authenticate with updated permissions (e.g., for Shared Drives).\n\n"
                "Do you want to continue?")
            
            if result:
                self.audio_manager.clear_google_drive_authentication()
                self.auth_status_label.config(text="Not authenticated", foreground='red')
                self.folder_status_label.config(text="", foreground='black')
                
                # Update the entire Google Drive UI state to ensure consistency
                self.update_google_drive_ui_state()
                
                messagebox.showinfo("Success", "Google Drive authentication cleared.\nYou can now re-authenticate if needed.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear authentication: {e}")
    
    def update_google_drive_ui_state(self):
        """Update Google Drive UI state based on current settings"""
        try:
            # Update checkbox state from settings
            self.drive_enabled_var.set(self.settings_manager.get_google_drive_enabled())
            
            # Update folder ID from settings
            folder_id = self.settings_manager.get_google_drive_folder_id()
            if folder_id:
                self.folder_id_var.set(folder_id)
            
            # Update authentication status - check both settings and actual authentication state
            is_authenticated_in_settings = self.settings_manager.get_google_drive_authenticated()
            is_actually_authenticated = self.audio_manager.is_google_drive_authenticated()
            
            # Use the actual authentication state if available, otherwise fall back to settings
            if is_actually_authenticated:
                self.auth_status_label.config(text="Authenticated", foreground='green')
            elif is_authenticated_in_settings:
                # Settings say authenticated but actual state is not - this can happen if token expired
                self.auth_status_label.config(text="Authentication expired", foreground='orange')
            else:
                self.auth_status_label.config(text="Not authenticated", foreground='red')
            
            # Clear folder status initially
            self.folder_status_label.config(text="", foreground='black')
            
            # Enable/disable controls based on checkbox
            self.on_drive_enabled_changed()
            
        except Exception as e:
            print(f"Error updating Google Drive UI state: {e}")
    
    def on_closing(self):
        """Handle dialog closing"""
        self.dialog.grab_release()
        self.dialog.destroy()

class MultitrackRecorderGUI:
    """Main GUI application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Multitrack Audio Recorder")
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Disable auto-save during initialization
        self.settings_manager.set_auto_save(False)
        
        # Load window geometry from settings
        geometry = self.settings_manager.get_window_geometry()
        self.root.geometry(geometry)
        
        # Initialize audio manager with settings manager
        self.audio_manager = AudioManager(self.settings_manager)
        self.audio_manager.set_level_callback(self.on_level_update)
        self.audio_manager.set_waveform_callback(self.on_waveform_update)
        
        # Device rows
        self.device_rows: Dict[int, DeviceRow] = {}
        
        # Shutdown flag
        self._shutting_down = False
        
        # Initialization flag to prevent callbacks during setup
        self._initializing = True
        
        self.create_widgets()
        self.populate_devices()
        
        # Initialize session title from settings
        self.update_session_title_display()
        
        # Mark initialization as complete
        self._initializing = False
        
        
        # Set up cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Style configuration for progressbars
        self.setup_styles()
        
        # Enable auto-save after GUI is fully initialized
        self.settings_manager.set_auto_save(True)
        
        # Set up window geometry saving after initialization is complete
        self.root.bind('<Configure>', self.on_window_configure)
    
    def open_configuration_dialog(self):
        """Open the configuration dialog"""
        try:
            ConfigurationDialog(self.root, self.audio_manager, self.settings_manager)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open configuration dialog: {e}")
    
    def setup_styles(self):
        """Set up custom styles for progressbars and buttons"""
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
        
        # Configuration button
        config_button = ttk.Button(title_frame, text="Configuration", 
                                  command=self.open_configuration_dialog)
        config_button.pack(pady=(5, 0))
        
        # Session Title
        session_frame = ttk.Frame(self.root)
        session_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(session_frame, text="Session Title:", 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.session_title_var = tk.StringVar()
        self.session_title_entry = ttk.Entry(session_frame, textvariable=self.session_title_var, width=30)
        self.session_title_entry.pack(side=tk.LEFT, padx=5)
        self.session_title_entry.bind('<KeyRelease>', self.on_session_title_changed)
        
        # Session title help text
        session_help = ttk.Label(session_frame, 
                               text="(Optional - will be used as folder name prefix)", 
                               font=('Arial', 8), foreground='gray')
        session_help.pack(side=tk.LEFT, padx=5)
        
        
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
        self.record_button.pack()
        
        self.recording_status = ttk.Label(recording_frame, text="")
        self.recording_status.pack(pady=(5, 0))
    
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
    
    def on_session_title_changed(self, event=None):
        """Handle session title change"""
        session_title = self.session_title_var.get().strip()
        if not self._initializing:
            self.audio_manager.set_session_title(session_title)
    
    def update_session_title_display(self):
        """Update session title display from settings"""
        try:
            session_title = self.settings_manager.get_session_title()
            if session_title:
                self.session_title_var.set(session_title)
        except Exception as e:
            print(f"Error updating session title display: {e}")
    
    
    def on_window_configure(self, event):
        """Handle window configuration changes (resize, move)"""
        if event.widget == self.root:
            # Save window geometry
            geometry = self.root.geometry()
            self.settings_manager.set_window_geometry(geometry)
    
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
                
                if not self.settings_manager.get_export_directory():
                    messagebox.showwarning("Warning", "Please select an export directory first in Configuration")
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
            
            # Step 3: Save settings
            print("💾 Saving settings...")
            self.settings_manager.force_save()
            print("✅ Settings saved")
            
            # Step 4: Clean up audio manager
            print("🧹 Cleaning up audio resources...")
            self.audio_manager.cleanup()
            print("✅ Audio cleanup completed")
        except Exception as e:
            print(f"Error during shutdown: {e}")

        def shutdown():
            try:
                # Step 5: Force update UI to ensure all changes are visible
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