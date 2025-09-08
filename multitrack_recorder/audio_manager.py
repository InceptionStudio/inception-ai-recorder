import pyaudio
import wave
import threading
import queue
import time
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import json
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .settings_manager import SettingsManager

@dataclass
class AudioDevice:
    """Represents an audio input device"""
    id: str
    name: str
    host_api: str
    max_input_channels: int
    max_output_channels: int
    default_low_input_latency: float
    default_sample_rate: float

class GoogleDriveUploader:
    """Handles Google Drive upload functionality"""
    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.folder_id = None
        self._lock = threading.Lock()
    
    def authenticate(self, credentials_file: str = "credentials.json") -> bool:
        """Authenticate with Google Drive API"""
        try:
            with self._lock:
                # The file token.pickle stores the user's access and refresh tokens.
                # It is created automatically when the authorization flow completes for the first time.
                if os.path.exists('token.pickle'):
                    with open('token.pickle', 'rb') as token:
                        self.credentials = pickle.load(token)
                
                # If there are no (valid) credentials available, let the user log in.
                if not self.credentials or not self.credentials.valid:
                    if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                        self.credentials.refresh(Request())
                    else:
                        if not os.path.exists(credentials_file):
                            print(f"❌ Google Drive credentials file '{credentials_file}' not found.")
                            print("Please download your OAuth2 credentials from Google Cloud Console.")
                            return False
                        
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_file, self.SCOPES)
                        self.credentials = flow.run_local_server(port=0)
                    
                    # Save the credentials for the next run
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(self.credentials, token)
                
                self.service = build('drive', 'v3', credentials=self.credentials)
                print("✅ Google Drive authentication successful")
                return True
                
        except Exception as e:
            print(f"❌ Google Drive authentication failed: {e}")
            return False
    
    def set_folder_id(self, folder_id: str):
        """Set the Google Drive folder ID for uploads"""
        with self._lock:
            self.folder_id = folder_id
            print(f"📁 Google Drive folder ID set to: {folder_id}")
    
    def validate_folder_id(self, folder_id: str) -> tuple[bool, str]:
        """Validate that a folder ID exists and is accessible"""
        if not self.is_authenticated():
            return False, "Not authenticated with Google Drive"
        
        if not folder_id or not folder_id.strip():
            return False, "Folder ID cannot be empty"
        
        try:
            with self._lock:
                folder_info = self.service.files().get(
                    fileId=folder_id.strip(),
                    fields='id,name,mimeType',
                    supportsAllDrives=True
                ).execute()
                
                if folder_info.get('mimeType') != 'application/vnd.google-apps.folder':
                    return False, f"The specified ID is not a folder: {folder_id}"
                
                folder_name = folder_info.get('name', 'Unknown')
                return True, f"Valid folder: {folder_name}"
                
        except Exception as e:
            return False, f"Cannot access folder: {e}"
    
    def get_folder_id(self) -> Optional[str]:
        """Get the current Google Drive folder ID"""
        with self._lock:
            return self.folder_id
    
    def is_authenticated(self) -> bool:
        """Check if authenticated with Google Drive"""
        with self._lock:
            return self.service is not None and self.credentials is not None
    
    def clear_authentication(self):
        """Clear authentication tokens (useful for re-authentication with new scopes)"""
        with self._lock:
            self.service = None
            self.credentials = None
            
        # Remove token file if it exists
        try:
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
                print("🗑️ Cleared Google Drive authentication tokens")
        except Exception as e:
            print(f"⚠️ Could not remove token file: {e}")
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Create a folder in Google Drive and return its ID"""
        if not self.is_authenticated():
            print("❌ Not authenticated with Google Drive")
            return None
        
        try:
            with self._lock:
                # Use the main folder ID if no parent specified
                parent_id = parent_folder_id or self.folder_id
                if not parent_id:
                    print("❌ No parent folder ID available")
                    return None
                
                # Check if folder already exists
                existing_folder_id = self._find_folder_by_name(folder_name, parent_id)
                if existing_folder_id:
                    print(f"📁 Using existing folder: {folder_name}")
                    return existing_folder_id
                
                # Create folder metadata
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                
                # Create the folder
                folder = self.service.files().create(
                    body=folder_metadata,
                    fields='id,name',
                    supportsAllDrives=True
                ).execute()
                
                folder_id = folder.get('id')
                print(f"📁 Created Google Drive folder: {folder_name} (ID: {folder_id})")
                return folder_id
                
        except Exception as e:
            print(f"❌ Failed to create Google Drive folder '{folder_name}': {e}")
            return None
    
    def _find_folder_by_name(self, folder_name: str, parent_folder_id: str) -> Optional[str]:
        """Find a folder by name within a parent folder"""
        try:
            # Search for folders with the exact name in the parent folder
            query = f"name='{folder_name}' and parents in '{parent_folder_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                fields='files(id,name)',
                supportsAllDrives=True
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']  # Return the first match
            
            return None
            
        except Exception as e:
            print(f"❌ Error searching for folder '{folder_name}': {e}")
            return None

    def upload_file(self, file_path: str, file_name: Optional[str] = None, parent_folder_id: Optional[str] = None, settings_manager=None) -> bool:
        """Upload a file to Google Drive"""
        if not self.is_authenticated():
            print("❌ Not authenticated with Google Drive")
            return False
        
        if not self.folder_id:
            print("❌ No Google Drive folder ID set")
            return False
        
        try:
            with self._lock:
                if not os.path.exists(file_path):
                    print(f"❌ File not found: {file_path}")
                    return False
                
                if file_name is None:
                    file_name = os.path.basename(file_path)
                
                # Check if file has already been uploaded
                if settings_manager and settings_manager.is_file_uploaded(file_path):
                    print(f"⏭️ Skipping {file_name} - already uploaded")
                    return True
                
                # Use the specified parent folder or the main folder
                target_folder_id = parent_folder_id or self.folder_id
                
                # First, verify the target folder exists and we have access
                try:
                    folder_info = self.service.files().get(
                        fileId=target_folder_id,
                        fields='id,name,mimeType',
                        supportsAllDrives=True
                    ).execute()
                    
                    if folder_info.get('mimeType') != 'application/vnd.google-apps.folder':
                        print(f"❌ The specified ID is not a folder: {target_folder_id}")
                        return False
                    
                    folder_name = folder_info.get('name', 'Unknown')
                    if parent_folder_id:
                        print(f"📁 Uploading to session folder: {folder_name}")
                    else:
                        print(f"📁 Uploading to folder: {folder_name}")
                    
                except Exception as folder_error:
                    print(f"❌ Cannot access Google Drive folder {target_folder_id}: {folder_error}")
                    print("💡 Please check:")
                    print("   - The folder ID is correct")
                    print("   - You have access to the folder")
                    print("   - The folder exists in your Google Drive")
                    return False
                
                # Create file metadata
                file_metadata = {
                    'name': file_name,
                    'parents': [target_folder_id]
                }
                
                # Upload file
                media = MediaFileUpload(file_path, resumable=True)
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                
                print(f"✅ Uploaded {file_name} to Google Drive (ID: {file.get('id')})")
                
                # Mark file as uploaded
                if settings_manager:
                    stat = os.stat(file_path)
                    settings_manager.mark_file_uploaded(file_path, stat.st_size, stat.st_mtime)
                
                return True
                
        except Exception as e:
            print(f"❌ Failed to upload {file_path} to Google Drive: {e}")
            return False
    
    def upload_files(self, file_paths: List[str], parent_folder_id: Optional[str] = None, settings_manager=None) -> Dict[str, bool]:
        """Upload multiple files to Google Drive"""
        results = {}
        for file_path in file_paths:
            results[file_path] = self.upload_file(file_path, parent_folder_id=parent_folder_id, settings_manager=settings_manager)
        return results

STOP = object()

class AudioManager:
    """Manages audio devices and recording functionality"""
    
    # Fields/methods that start with "__" should only be accessed when _lock is held
    # or during initialization.
    def __init__(self, settings_manager: Optional[SettingsManager] = None):
        self.__audio = pyaudio.PyAudio()
        self.__input_devices: List[AudioDevice] = []
        self.__selected_devices: Dict[str, bool] = {}
        self.__listening_streams: Dict[str, pyaudio.Stream] = {}
        self.__listening_threads: Dict[str, threading.Thread] = {}
        self.__recording_files: Dict[str, wave.Wave_write] = {}
        self.__audio_data_queues: Dict[str, queue.Queue] = {}
        
        # Callbacks for UI updates
        self.__level_callback: Optional[Callable[[str, float], None]] = None
        self.__waveform_callback: Optional[Callable[[str, List[float]], None]] = None
        
        # Listening settings
        self.__sample_rate = 48000
        self.__channels = 1
        self.__sample_format = pyaudio.paFloat32
        self.__chunk_size = 1024
        
        # Device labels
        self.__device_labels: Dict[str, str] = {}
        
        # Device gain settings (in dB)
        self.__device_gains: Dict[str, float] = {}
        
        # Peak level tracking for auto gain
        self.__device_peak_levels: Dict[str, float] = {}  # Peak level (0.0 to 1.0)
        self.__device_peak_counts: Dict[str, int] = {}    # How many times peak was hit
        self.__device_sample_counts: Dict[str, int] = {}  # Total samples processed
        
        # Export directory
        self.__export_directory: Optional[Path] = None
        
        # Session title
        self.__session_title: str = ""
        
        # Current session folder (set when recording starts)
        self.__current_session_folder: Optional[Path] = None
        
        # Google Drive uploader
        self.__drive_uploader = GoogleDriveUploader()
        self.__upload_to_drive = False
        
        # Settings manager
        self.__settings_manager = settings_manager or SettingsManager()
        
        self.__is_recording = False
        self.__shutting_down = False
        self._lock = threading.Lock()
        self._bg_thread_pool = ThreadPoolExecutor(max_workers=1)
        self._callback_thread_pool = ThreadPoolExecutor(max_workers=2)
        
        self.__load_input_devices()
        self.__load_settings()
        self.__load_device_settings()
        self.__load_selected_devices()
    
    def __load_settings(self):
        """Load settings from settings manager"""
        try:
            # Load export directory
            export_dir = self.__settings_manager.get_export_directory()
            if export_dir:
                self.set_export_directory(export_dir)
            else:
                # If no export directory is set, use the default Downloads folder
                from platformdirs import user_downloads_path
                default_dir = str(user_downloads_path())
                self.set_export_directory(default_dir)
            
            # Load session title
            session_title = self.__settings_manager.get_session_title()
            if session_title:
                self.__session_title = session_title
            
            # Load Google Drive settings
            self.__upload_to_drive = self.__settings_manager.get_google_drive_enabled()
            folder_id = self.__settings_manager.get_google_drive_folder_id()
            if folder_id:
                self.__drive_uploader.set_folder_id(folder_id)
            
            # Load selected devices
            self.__load_selected_devices()
            
            print("✅ Loaded settings from settings manager")
            
            # Attempt automatic Google Drive authentication if enabled
            if self.__upload_to_drive:
                self.try_auto_authenticate_google_drive()
            
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
    
    def __load_device_settings(self):
        """Load device-specific settings (labels and gains) after remapping"""
        try:
            # Load device labels and gains after remapping has occurred
            for device in self.__input_devices:
                label = self.__settings_manager.get_device_label(device.id)
                self.__device_labels[device.id] = label
                
                # Load device gains
                gain = self.__settings_manager.get_device_gain(device.id)
                self.__device_gains[device.id] = gain
            
            print("✅ Loaded device-specific settings")
            
        except Exception as e:
            print(f"❌ Error loading device settings: {e}")
    
    def __load_selected_devices(self):
        """Load selected devices from settings"""
        try:
            last_used_devices = self.__settings_manager.get_last_used_devices()
            for device_id in last_used_devices:
                if device_id in self.__selected_devices:
                    self.__selected_devices[device_id] = True
                    # Start the device stream
                    self.__start_device_stream(device_id)
        except Exception as e:
            print(f"❌ Error loading selected devices: {e}")
    
    def __save_selected_devices(self):
        """Save selected devices to settings"""
        try:
            selected_devices = [device_id for device_id, selected in self.__selected_devices.items() if selected]
            self.__settings_manager.set_last_used_devices(selected_devices)
        except Exception as e:
            print(f"❌ Error saving selected devices: {e}")
    
    def __load_input_devices(self):
        """Load all available input audio devices"""
        # Assumed to be the only thread accessing this
        self.__input_devices.clear()
        device_count = self.__audio.get_device_count()
        
        for i in range(device_count):
            try:
                device_info = self.__audio.get_device_info_by_index(i)
                
                # Only include input devices
                if device_info['maxInputChannels'] > 0:
                    host_api_info = self.__audio.get_host_api_info_by_index(device_info['hostApi'])
                    print(f"🎤 {host_api_info['name']} Input Device Found: {device_info}")
                    
                    device = AudioDevice(
                        id=str(i),
                        name=device_info['name'],
                        host_api=host_api_info['name'],
                        max_input_channels=device_info['maxInputChannels'],
                        max_output_channels=device_info['maxOutputChannels'],
                        default_low_input_latency=device_info['defaultLowInputLatency'],
                        default_sample_rate=device_info['defaultSampleRate']
                    )
                    self.__input_devices.append(device)
                    self.__selected_devices[str(i)] = False
                    # Initialize peak tracking for new device
                    self.__reset_device_peak_tracking(i)
                    
            except Exception as e:
                print(f"Error loading device {i}: {e}")
        
        print(f"Loaded {len(self.__input_devices)} input devices")
        
        # Create current device mapping and remap settings
        current_devices = {}
        for device in self.__input_devices:
            current_devices[str(device.id)] = device.name
        self.__settings_manager.remap_device_ids(current_devices)
    
    def refresh_devices(self):
        """Refresh the list of available devices"""
        with self._lock:
            if self.__is_recording:
                print("Cannot refresh devices while recording")
                return
        
            print("🔄 Refreshing devices...")
            import time
            
            try:
                # Set shutdown flag to prevent callbacks during refresh
                self.__shutting_down = True
                
                # Stop any existing streams
                self.__stop_all_streams()
                
                # Clear existing data
                self.__selected_devices.clear()
                
                # Terminate PyAudio with error handling
                old_audio = self.__audio
                self.__audio = None  # Clear reference immediately
                
                try:
                    if old_audio:
                        old_audio.terminate()
                    print("✅ Terminated PyAudio")
                except Exception as e:
                    print(f"⚠️ Warning during PyAudio termination: {e}")
                
                # Small delay before reinitializing
                time.sleep(0.2)
                
                # Reinitialize PyAudio
                self.__audio = pyaudio.PyAudio()
                print("✅ Reinitialized PyAudio")
                
                # Reload devices
                self.__load_input_devices()
                
                # Reload device-specific settings after remapping
                self.__load_device_settings()
                
                # Reload selected devices after remapping
                self.__load_selected_devices()
                
                print("✅ Device refresh completed")
                
            except Exception as e:
                print(f"❌ Error during device refresh: {e}")
                
                # Try to recover by creating a new PyAudio instance
                try:
                    self.__audio = pyaudio.PyAudio()
                    self.__load_input_devices()
                    print("✅ Recovered from refresh error")
                except Exception as recovery_error:
                    print(f"❌ Failed to recover: {recovery_error}")
                    raise RuntimeError("Device refresh failed - please restart the application")
            finally:
                # Always clear the shutdown flag
                self.__shutting_down = False
    
    def __get_device_by_id(self, device_id: str) -> Optional[AudioDevice]:
        """Get device by ID"""
        return next((device for device in self.__input_devices if device.id == device_id), None)
    
    def get_input_devices(self) -> List[AudioDevice]:
        """Get list of input devices"""
        with self._lock:
            return self.__input_devices.copy()
    
    def get_device_count(self) -> int:
        """Get number of input devices"""
        with self._lock:
            return len(self.__input_devices)
    
    def set_device_selected(self, device_id: str, selected: bool):
        """Set device selection status"""
        should_stop = False
        
        with self._lock:
            if device_id in self.__selected_devices:
                was_selected = self.__selected_devices[device_id]
                self.__selected_devices[device_id] = selected
                
                if selected and not was_selected:
                    self.__start_device_stream(device_id)
                elif not selected and was_selected:
                    should_stop = True
                    # Reset peak tracking when device is deselected
                    self.__reset_device_peak_tracking(device_id)
            # Save selected devices to settings
            self.__save_selected_devices()
        
        # Do it outside of lock so we can block until the thread disappears
        if should_stop:
            self._stop_device_stream(device_id)
    
    def is_device_selected(self, device_id: str) -> bool:
        """Check if device is selected"""
        with self._lock:
            return self.__selected_devices.get(device_id, False)
    
    def get_selected_device_ids(self) -> List[str]:
        """Get list of selected device IDs"""
        with self._lock:
            return self.__get_selected_device_ids()
    
    def __get_selected_device_ids(self) -> List[str]:
        """Get list of selected device IDs"""
        return [device_id for device_id, selected in self.__selected_devices.items() if selected]

    def set_device_label(self, device_id: str, label: str):
        """Set custom label for device"""
        with self._lock:
            self.__device_labels[device_id] = label
        
        # Save to settings
        self.__settings_manager.set_device_label(device_id, label)
    
    def get_device_label(self, device_id: str) -> str:
        """Get custom label for device"""
        with self._lock:
            return self.__get_device_label(device_id)
    
    def __get_device_label(self, device_id: str) -> str:
        """Get custom label for device"""
        return self.__device_labels.get(device_id, "")
    
    def clear_device_label(self, device_id: str):
        """Clear custom label for device"""
        with self._lock:
            self.__device_labels.pop(device_id, None)
        
        # Save to settings
        self.__settings_manager.set_device_label(device_id, "")
    
    def set_device_gain(self, device_id: str, gain_db: float):
        """Set gain for device in dB"""
        with self._lock:
            self.__device_gains[device_id] = gain_db
        
        # Save to settings
        self.__settings_manager.set_device_gain(device_id, gain_db)
    
    def get_device_gain(self, device_id: str) -> float:
        """Get gain for device in dB"""
        with self._lock:
            return self.__device_gains.get(device_id, 0.0)
    
    def __reset_device_peak_tracking(self, device_id: str):
        """Reset peak tracking for a device"""
        self.__device_peak_levels[device_id] = 0.0
        self.__device_peak_counts[device_id] = 0
        self.__device_sample_counts[device_id] = 0
    
    def get_device_peak_info(self, device_id: str) -> tuple[float, int, int]:
        """Get peak tracking info: (peak_level, peak_count, sample_count)"""
        with self._lock:
            return (
                self.__device_peak_levels.get(device_id, 0.0),
                self.__device_peak_counts.get(device_id, 0),
                self.__device_sample_counts.get(device_id, 0)
            )
    
    def calculate_auto_gain(self, device_id: str) -> Optional[float]:
        """Calculate optimal gain based on peak levels and clipping detection"""
        with self._lock:
            peak_level = self.__device_peak_levels.get(device_id, 0.0)
            peak_count = self.__device_peak_counts.get(device_id, 0)
            sample_count = self.__device_sample_counts.get(device_id, 0)
        
        if sample_count == 0 or peak_level == 0.0:
            return None  # No data to work with
        
        # Calculate clipping percentage
        clipping_percentage = (peak_count / sample_count) * 100.0 if sample_count > 0 else 0.0
        
        # Target level (aim for -3dB headroom)
        target_level = 0.708  # -3dB in linear scale
        
        # Calculate required gain
        if peak_level > 0.0:
            required_gain_linear = target_level / peak_level
            required_gain_db = 20.0 * np.log10(required_gain_linear)
            
            # Apply clipping penalty - reduce gain if clipping detected
            if clipping_percentage > 1.0:  # More than 1% clipping
                clipping_penalty = min(6.0, clipping_percentage * 2.0)  # Up to 6dB penalty
                required_gain_db -= clipping_penalty
            
            # Don't apply if gain would be too high (>24dB) or too low (<-24dB)
            if -24.0 <= required_gain_db <= 24.0:
                return float(required_gain_db)  # Convert numpy float32 to Python float
        
        return None
    
    def set_export_directory(self, directory: str):
        """Set the export directory for recordings"""
        with self._lock:
            self.__export_directory = Path(directory)
            if not self.__export_directory.exists():
                self.__export_directory.mkdir(parents=True, exist_ok=True)
        
        # Save to settings
        self.__settings_manager.set_export_directory(directory)
    
    def get_export_directory(self) -> Optional[Path]:
        """Get the export directory for recordings"""
        with self._lock:
            return self.__export_directory
    
    def set_session_title(self, title: str):
        """Set the session title for recordings"""
        with self._lock:
            self.__session_title = title
            print(f"📝 Session title set to: {title}")
        
        # Save to settings
        self.__settings_manager.set_session_title(title)
    
    def get_session_title(self) -> str:
        """Get the session title for recordings"""
        with self._lock:
            return self.__session_title
    
    def _generate_session_folder_name(self) -> str:
        """Generate session folder name from title and timestamp"""
        from datetime import datetime
        import re
        
        # Get current local time
        now = datetime.now()
        
        # Format timestamp as YYYY-MM-DD_HH-MM-SS (no invalid path characters)
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        
        # Get session title and sanitize it
        session_title = self.__session_title.strip()
        
        if session_title:
            # Remove or replace invalid path characters
            # Replace spaces with underscores, remove other problematic characters
            sanitized_title = re.sub(r'[<>:"/\\|?*]', '', session_title)
            sanitized_title = re.sub(r'\s+', '_', sanitized_title)
            sanitized_title = sanitized_title.strip('_')
            
            if sanitized_title:
                return f"{sanitized_title}_{timestamp}"
        
        # If no title or title becomes empty after sanitization, just use timestamp
        return timestamp
    
    def get_current_session_folder(self) -> Optional[Path]:
        """Get the current session folder path"""
        with self._lock:
            return self.__current_session_folder
    
    def set_google_drive_enabled(self, enabled: bool):
        """Enable or disable Google Drive upload"""
        with self._lock:
            self.__upload_to_drive = enabled
            print(f"📤 Google Drive upload {'enabled' if enabled else 'disabled'}")
        
        # Save to settings
        self.__settings_manager.set_google_drive_enabled(enabled)
    
    def is_google_drive_enabled(self) -> bool:
        """Check if Google Drive upload is enabled"""
        with self._lock:
            return self.__upload_to_drive
    
    def authenticate_google_drive(self, credentials_file: str = "credentials.json") -> bool:
        """Authenticate with Google Drive"""
        success = self.__drive_uploader.authenticate(credentials_file)
        if success:
            # Save authentication status
            self.__settings_manager.set_google_drive_authenticated(True)
        return success
    
    def try_auto_authenticate_google_drive(self, credentials_file: str = "credentials.json") -> bool:
        """Try to automatically authenticate with Google Drive using stored credentials"""
        try:
            # Only attempt auto-authentication if Google Drive is enabled
            if not self.__upload_to_drive:
                return False
            
            # Check if credentials file exists
            if not os.path.exists(credentials_file):
                print("📁 Google Drive credentials file not found, skipping auto-authentication")
                return False
            
            # Check if we have a stored token
            if not os.path.exists('token.pickle'):
                print("📁 No stored Google Drive token found, skipping auto-authentication")
                return False
            
            print("🔄 Attempting automatic Google Drive authentication...")
            success = self.__drive_uploader.authenticate(credentials_file)
            
            if success:
                print("✅ Automatic Google Drive authentication successful")
                # Save authentication status
                self.__settings_manager.set_google_drive_authenticated(True)
            else:
                print("❌ Automatic Google Drive authentication failed")
                # Clear authentication status
                self.__settings_manager.set_google_drive_authenticated(False)
            
            return success
            
        except Exception as e:
            print(f"❌ Error during automatic Google Drive authentication: {e}")
            # Clear authentication status on error
            self.__settings_manager.set_google_drive_authenticated(False)
            return False
    
    def set_google_drive_folder_id(self, folder_id: str):
        """Set the Google Drive folder ID for uploads"""
        self.__drive_uploader.set_folder_id(folder_id)
        # Save to settings
        self.__settings_manager.set_google_drive_folder_id(folder_id)
    
    def validate_google_drive_folder_id(self, folder_id: str) -> tuple[bool, str]:
        """Validate that a Google Drive folder ID exists and is accessible"""
        return self.__drive_uploader.validate_folder_id(folder_id)
    
    def get_google_drive_folder_id(self) -> Optional[str]:
        """Get the current Google Drive folder ID"""
        return self.__drive_uploader.get_folder_id()
    
    def is_google_drive_authenticated(self) -> bool:
        """Check if authenticated with Google Drive"""
        return self.__drive_uploader.is_authenticated()
    
    def clear_google_drive_authentication(self):
        """Clear Google Drive authentication tokens"""
        self.__drive_uploader.clear_authentication()
        # Save authentication status
        self.__settings_manager.set_google_drive_authenticated(False)
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        with self._lock:
            return self.__is_recording
    
    def set_level_callback(self, callback: Callable[[str, float], None]):
        """Set callback for audio level updates"""
        with self._lock:
            self.__level_callback = callback
    
    def set_waveform_callback(self, callback: Callable[[str, List[float]], None]):
        """Set callback for waveform data updates"""
        with self._lock:
            self.__waveform_callback = callback
    
    def _start_device_stream(self, device_id: str):
        """Start audio stream for a device"""
        with self._lock:
            self.__start_device_stream(device_id)

    def __start_device_stream(self, device_id: str):
        """Start audio stream for a device"""
        if device_id in self.__listening_streams:
            return
        
        device = self.__get_device_by_id(device_id)
        if not device:
            return
        
        device_index = -1
        try:
            device_index = int(device_id)
        except ValueError:
            pass
        if device_index < 0:
            print(f"  ⚠️ Invalid device ID {device_id}")
            return
        
        try:
            # Create audio data queue for this device
            self.__audio_data_queues[device_id] = queue.Queue()
            
            # Create callback function
            def audio_callback(in_data, frame_count, time_info, status):
                # This runs in a separate high-priority thread. Make sure it is highly
                # efficient and there is no blocking code here.
                if status:
                    print(f"Audio callback status: {status}")
                
                # Copy bytes into a new numpy array
                audio_data = np.frombuffer(in_data, dtype=np.float32).copy()
                
                # Enqueue all other operations in a background thread, so we can return immediately.
                def _bg_audio_callback_ops():
                    with self._lock:
                        if not self.__shutting_down and device_id in self.__listening_streams:
                            queue_ref = self.__audio_data_queues[device_id]
                    
                    # Queue audio data if needed (outside of lock to avoid deadlock)
                    if queue_ref is not None:
                        try:
                            queue_ref.put_nowait(audio_data)
                        except queue.Full:
                            pass  # Drop data if queue is full

                # Only submit to thread pool if not shutting down
                if self.__shutting_down:
                    print(f"Shutting down, returning paAbort")
                    return (in_data, pyaudio.paAbort)
                    
                try:
                    self._bg_thread_pool.submit(_bg_audio_callback_ops)
                except RuntimeError:
                    # Thread pool is shut down, ignore the error
                    pass

                return (in_data, pyaudio.paContinue)
            
            # Open stream
            stream = self.__audio.open(
                format=self.__sample_format,
                channels=self.__channels,
                rate=self.__sample_rate,
                frames_per_buffer=self.__chunk_size,
                input=True,
                input_device_index=device_index,
                stream_callback=audio_callback
            )
            
            # Start stream
            stream.start_stream()
            self.__listening_streams[device_id] = stream
            
            # Start listening thread
            thread = threading.Thread(
                target=self._listening_worker,
                args=(device_id,),
                daemon=True
            )
            thread.start()
            self.__listening_threads[device_id] = thread

            print(f"Started stream for device {device_id}: {device.name}")
            
        except Exception as e:
            print(f"Failed to start stream for device {device_id}: {e}")
    
    def __stop_device_stream(self, device_id: str) -> threading.Thread:
        if device_id not in self.__listening_streams:
            return None
        
        stream = self.__listening_streams[device_id]
        print(f"Stopping stream for device {device_id}...")
        
        # Try to stop stream
        try:
            if stream.is_active():
                stream.stop_stream()
            print(f"  ✅ Stopped stream for device {device_id}")
        except Exception as e:
            print(f"  ⚠️ Warning stopping stream for device {device_id}: {e}")
        
        # Try to close stream
        try:
            if not stream.is_stopped():
                stream.close()
            print(f"  ✅ Closed stream for device {device_id}")
        except Exception as e:
            print(f"  ⚠️ Warning closing stream for device {device_id}: {e}")
        
        # Remove from tracking
        del self.__listening_streams[device_id]
        
        queue_ref = self.__audio_data_queues[device_id]
        if queue_ref is not None:
            # Wake up thread if it is waiting
            print(f"✅ Notifying listener thread for {device_id} to stop")
            queue_ref.put_nowait(STOP)
            del self.__audio_data_queues[device_id]
        
        # Stop listening thread if it exists
        thread = None
        if device_id in self.__listening_threads:
            thread = self.__listening_threads[device_id]
            del self.__listening_threads[device_id]
            # Do the join outside of the lock
        
        print(f"✅ Stopped device {device_id}")
        return thread
        
    def _stop_device_stream(self, device_id: str):
        """Stop audio stream for a device"""
        thread = None
        stream = None
        try:
            with self._lock:
                thread = self.__stop_device_stream(device_id)
        except Exception as e:
            print(f"❌ Error stopping device {device_id}: {e}")
            # Force cleanup even if there were errors
            with self._lock:
                self.__listening_streams.pop(device_id, None)
                self.__audio_data_queues.pop(device_id, None)
                self.__listening_threads.pop(device_id, None)
        
        # Join thread outside of lock to avoid deadlock
        if thread and thread.is_alive():
            print(f"  🔄 Waiting for listening thread {device_id}...")
            thread.join(timeout=5.0)
            if thread.is_alive():
                print(f"  ⚠️ Listening thread {device_id} did not stop gracefully")
            else:
                print(f"  ✅ Listening thread {device_id} exited")
    
    def stop_all_streams(self):
        with self._lock:
            self.__stop_all_streams()

    def __stop_all_streams(self):
        """Stop all active streams"""
        if not self.__listening_streams:
            return
        
        print(f"🛑 Stopping {len(self.__listening_streams)} active streams...")
        
        # Create a copy of the keys to avoid dictionary changed during iteration
        stream_ids = list(self.__listening_streams.keys())
        
        for device_id in stream_ids:
            try:
                thread = self.__stop_device_stream(device_id)
                # XXX: Abandon threads
            except Exception as e:
                print(f"❌ Failed to stop stream {device_id}: {e}")
                # Force cleanup
                self.__listening_streams.pop(device_id, None)
                self.__audio_data_queues.pop(device_id, None)
                self.__listening_threads.pop(device_id, None)
        
        # Final cleanup - ensure all dictionaries are clear
        self.__listening_streams.clear()
        self.__audio_data_queues.clear()
        self.__listening_threads.clear()
        
        print("✅ All streams stopped")
    
    def start_recording(self):
        """Start recording from all selected devices"""
        with self._lock:
            if not self.__export_directory:
                raise ValueError("Export directory not set")
            if self.__is_recording:
                return

            selected_devices = self.__get_selected_device_ids()
            if not selected_devices:
                raise ValueError("No devices selected for recording")
            
            # Generate session folder name and create the folder
            session_folder_name = self._generate_session_folder_name()
            self.__current_session_folder = self.__export_directory / session_folder_name
            
            # Create the session folder
            try:
                self.__current_session_folder.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created session folder: {self.__current_session_folder}")
            except Exception as e:
                raise ValueError(f"Failed to create session folder: {e}")
            
            self.__is_recording = True
            
            # Create recording files for selected devices
            for device_id in selected_devices:
                device = self.__get_device_by_id(device_id)
                if not device:
                    continue
                
                # Generate filename
                label = self.__get_device_label(device_id)
                if label:
                    filename = f"{label}_recording.wav"
                else:
                    filename = f"device_{device_id}_recording.wav"
                
                filepath = self.__current_session_folder / filename
                
                try:
                    # Create WAV file
                    wav_file = wave.open(str(filepath), 'wb')
                    wav_file.setnchannels(self.__channels)
                    wav_file.setsampwidth(4)  # 32-bit float
                    wav_file.setframerate(self.__sample_rate)
                    
                    self.__recording_files[device_id] = wav_file
                    
                    print(f"Started recording for device {device_id} to {filepath}")
                    
                except Exception as e:
                    print(f"Failed to start recording for device {device_id}: {e}")
        
        print("Recording started")
    
    def stop_recording(self):
        """Stop recording and finalize files"""
        with self._lock:
            if not self.__is_recording:
                return
            self.__is_recording = False
            
            # Each listening worker is responsible for closing the file
            # and removing it from self.__recording_files
        
        print("Recording stopped")
        
        # Upload to Google Drive if enabled
        if self.__upload_to_drive and self.__export_directory:
            self._upload_recordings_to_drive()
        
        # Clear the current session folder reference
        with self._lock:
            self.__current_session_folder = None
    
    def _upload_recordings_to_drive(self):
        """Upload recorded files to Google Drive"""
        try:
            if not self.__drive_uploader.is_authenticated():
                print("❌ Google Drive not authenticated, skipping upload")
                return
            
            if not self.__drive_uploader.get_folder_id():
                print("❌ No Google Drive folder ID set, skipping upload")
                return
            
            # Get the current session folder
            session_folder = self.get_current_session_folder()
            if not session_folder or not session_folder.exists():
                print("❌ No session folder found for upload")
                return
            
            # Wait a moment for all files to be finalized
            time.sleep(1.0)
            
            # Find all .wav files in the session folder
            wav_files = list(session_folder.glob("*.wav"))
            
            if not wav_files:
                print(f"📁 No .wav files found in session folder: {session_folder}")
                return
            
            # Get the session folder name (without path)
            session_folder_name = session_folder.name
            
            # Get output format setting
            output_format = self.get_google_drive_output_format()
            
            print(f"📤 Uploading {len(wav_files)} files from session folder '{session_folder_name}' to Google Drive...")
            if output_format != 'wav':
                print(f"🎵 {output_format.upper()} conversion enabled - files will be converted before upload")
            
            # Upload files in a background thread to avoid blocking
            def upload_task():
                # Create a session folder in Google Drive
                drive_session_folder_id = self.__drive_uploader.create_folder(session_folder_name)
                
                if not drive_session_folder_id:
                    print("❌ Failed to create session folder in Google Drive")
                    return
                
                # Prepare files for upload (convert to target format if needed)
                files_to_upload = []
                
                for wav_file in wav_files:
                    if output_format != 'wav':
                        # Convert WAV to target format
                        converted_file_path = self.convert_wav_to_format(str(wav_file), output_format)
                        if converted_file_path:
                            files_to_upload.append(converted_file_path)
                        else:
                            # Fallback to WAV if conversion failed
                            print(f"⚠️ {output_format.upper()} conversion failed for {wav_file}, uploading WAV instead")
                            files_to_upload.append(str(wav_file))
                    else:
                        files_to_upload.append(str(wav_file))
                
                # Upload files to the session folder
                results = self.__drive_uploader.upload_files(
                    files_to_upload, 
                    parent_folder_id=drive_session_folder_id,
                    settings_manager=self.__settings_manager
                )
                
                successful_uploads = sum(1 for success in results.values() if success)
                total_files = len(results)
                
                if successful_uploads == total_files:
                    print(f"✅ Successfully uploaded all {total_files} files to Google Drive session folder '{session_folder_name}'")
                else:
                    print(f"⚠️ Uploaded {successful_uploads}/{total_files} files to Google Drive session folder '{session_folder_name}'")
            
            # Submit upload task to background thread pool
            self._bg_thread_pool.submit(upload_task)
            
        except Exception as e:
            print(f"❌ Error during Google Drive upload: {e}")
    
    def _listening_worker(self, device_id: str):
        """Worker thread to handle listening on a specific device"""
        while True:
            wav_file = None
            is_recording = False
            gain_db = 0.0
            with self._lock:
                audio_queue = self.__audio_data_queues.get(device_id)
                if not audio_queue:
                    print(f"BGThread({device_id}): Listening queue not found, exiting.")
                    break
            
                is_recording = self.__is_recording
                wav_file = self.__recording_files.get(device_id)
                if not is_recording and wav_file is not None:
                    print(f"BGThread({device_id}): Getting ready to close file")
                    self.__recording_files.pop(device_id, None)
                gain_db = self.__device_gains.get(device_id, 0.0)
            
            try:
                # Get audio data from queue with timeout
                audio_data = audio_queue.get(timeout=2.0)
                if audio_data is STOP:
                    print(f"BGThread({device_id}): Exiting gracefully")
                    return
                
                # Track peak levels (before gain adjustment)
                if not self.__shutting_down:
                    # Calculate peak level in this chunk (audio_data is already float32)
                    chunk_peak = np.max(np.abs(audio_data))
                    
                    # Update peak tracking
                    with self._lock:
                        if device_id in self.__listening_streams:
                            current_peak = self.__device_peak_levels.get(device_id, 0.0)
                            if chunk_peak > current_peak:
                                self.__device_peak_levels[device_id] = float(chunk_peak)
                            
                            # Count samples at peak level (for clipping detection)
                            if chunk_peak >= 0.99:  # Near maximum
                                self.__device_peak_counts[device_id] = self.__device_peak_counts.get(device_id, 0) + 1
                            
                            # Increment sample count
                            self.__device_sample_counts[device_id] = self.__device_sample_counts.get(device_id, 0) + 1
                
                # Apply gain adjustment
                if gain_db != 0.0:
                    # Convert dB to linear gain
                    gain_linear = 10.0 ** (gain_db / 20.0)
                    # Apply gain and clip to prevent overflow (audio_data is already float32)
                    audio_data = np.clip(audio_data * gain_linear, -1.0, 1.0)
                
                # Process callbacks
                level_cb = None
                waveform_cb = None
                with self._lock:
                    if not self.__shutting_down and device_id in self.__listening_streams:
                        level_cb = self.__level_callback
                        waveform_cb = self.__waveform_callback

                if level_cb and not self.__shutting_down:
                    # Calculate RMS level (audio_data is already float32 normalized to -1.0 to 1.0)
                    rms = np.sqrt(np.mean(audio_data**2))
                    scaled_rms = min(1.0, rms)

                    # Only submit to thread pool if not shutting down
                    if not self.__shutting_down:
                        # Run level_cb on the _callback_thread_pool
                        def _level_cb_task():
                            try:
                                # Double-check shutdown state and callback validity
                                if not self.__shutting_down and level_cb is not None:
                                    level_cb(device_id, scaled_rms)
                            except Exception as e:
                                print(f"BGThread({device_id}): Error during level callback: {e}")
                        try:
                            self._callback_thread_pool.submit(_level_cb_task)
                        except RuntimeError:
                            # Thread pool is shut down, ignore the error
                            pass

                if waveform_cb and not self.__shutting_down:
                    # Update waveform data (downsample for display)
                    downsample_factor = max(1, len(audio_data) // 100)
                    downsampled = audio_data[::downsample_factor]

                    # Scale to -1.0 to 1.0 range for display
                    scaled_waveform = downsampled.tolist()

                    # Only submit to thread pool if not shutting down
                    if not self.__shutting_down:
                        # Run waveform_cb on the _callback_thread_pool
                        def _waveform_cb_task():
                            try:
                                # Double-check shutdown state and callback validity
                                if not self.__shutting_down and waveform_cb is not None:
                                    waveform_cb(device_id, scaled_waveform)
                            except Exception as e:
                                print(f"BGThread({device_id}): Error during waveform callback: {e}")
                        try:
                            self._callback_thread_pool.submit(_waveform_cb_task)
                        except RuntimeError:
                            # Thread pool is shut down, ignore the error
                            pass

                if wav_file is not None:
                    # Convert float32 audio_data to 32-bit int for WAV file
                    # Scale float32 (-1.0 to 1.0) to int32 range
                    int32_data = (audio_data * 2147483647).astype(np.int32)
                    wav_file.writeframes(int32_data.tobytes())

            except queue.Empty:
                continue  # No data available, keep trying
            except Exception as e:
                print(f"BGThread({device_id}): Recording error: {e}")
                continue
            finally:
                if not is_recording and wav_file is not None:
                    # Close WAV file
                    try:
                        wav_file.close()
                        print(f"BGThread({device_id}): Finalized recording")
                    except Exception as e:
                        print(f"BGThread({device_id}): Error closing file: {e}")
            
    
    def cleanup(self):
        """Cleanup resources"""
        print("🧹 Cleaning up AudioManager...")
        
        # Set shutdown flag to prevent new callbacks
        with self._lock:
            self.__shutting_down = True
        
        # Shutdown thread pools without waiting to prevent deadlock
        try:
            print("🔄 Shutting down thread pools...")
            # Shutdown thread pools without waiting to prevent deadlock
            self._callback_thread_pool.shutdown(wait=False)
            self._bg_thread_pool.shutdown(wait=False)
            print("✅ Thread pools shutdown requested")
        except Exception as e:
            print(f"Error shutting down thread pools: {e}")
        
        # Clear callbacks AFTER thread pools are shut down
        with self._lock:
            self.__level_callback = None
            self.__waveform_callback = None
        
        if self.__is_recording:
            self.stop_recording()
        
        with self._lock:
            self.__stop_all_streams()
        
        # Small delay to let any pending operations finish
        import time
        time.sleep(0.1)
        
        try:
            self.__audio.terminate()
            print("✅ AudioManager cleanup completed")
        except Exception as e:
            print(f"Error terminating PyAudio: {e}")
    
    def convert_wav_to_format(self, wav_file_path: str, output_format: str, output_file_path: str = None, bitrate: int = 128) -> Optional[str]:
        """Convert WAV file to specified format using ffmpeg
        
        Args:
            wav_file_path: Path to the input WAV file
            output_format: Target format (wav, mp3, opus)
            output_file_path: Path for the output file (optional, defaults to same name with new extension)
            bitrate: Audio bitrate in kbps (default: 128)
            
        Returns:
            Path to the converted file if successful, None if failed
        """
        try:
            # Generate output file path if not provided
            if output_file_path is None:
                wav_path = Path(wav_file_path)
                output_file_path = str(wav_path.with_suffix(f'.{output_format}'))
            
            # If output format is WAV, no conversion needed
            if output_format.lower() == 'wav':
                return wav_file_path
            
            print(f"🔄 Converting {wav_file_path} to {output_format.upper()}...")
            
            # Use ffmpeg to convert WAV to target format
            import subprocess
            
            cmd = ['ffmpeg', '-i', wav_file_path, '-y']  # -y overwrites output file
            
            # Add format-specific parameters
            if output_format.lower() == 'mp3':
                cmd.extend(['-codec:a', 'libmp3lame', '-b:a', f'{bitrate}k'])
            elif output_format.lower() == 'opus':
                cmd.extend(['-codec:a', 'libopus', '-b:a', f'{bitrate}k'])
            else:
                print(f"❌ Unsupported output format: {output_format}")
                return None
            
            cmd.append(output_file_path)
            
            # Run ffmpeg conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ ffmpeg conversion failed: {result.stderr}")
                return None
            
            # Get file sizes for comparison
            wav_size = os.path.getsize(wav_file_path)
            output_size = os.path.getsize(output_file_path)
            compression_ratio = (wav_size - output_size) / wav_size * 100
            
            print(f"✅ {output_format.upper()} conversion completed: {output_file_path}")
            print(f"   WAV: {wav_size:,} bytes → {output_format.upper()}: {output_size:,} bytes ({compression_ratio:.1f}% smaller)")
            
            return output_file_path
            
        except Exception as e:
            print(f"❌ Error converting WAV to {output_format.upper()}: {e}")
            return None
    
    # Google Drive Settings Methods
    def set_google_drive_enabled(self, enabled: bool):
        """Set Google Drive upload enabled"""
        self.__settings_manager.set_google_drive_enabled(enabled)
    
    def get_google_drive_enabled(self) -> bool:
        """Get Google Drive upload enabled"""
        return self.__settings_manager.get_google_drive_enabled()
    
    def set_google_drive_folder_id(self, folder_id: str):
        """Set Google Drive folder ID"""
        self.__settings_manager.set_google_drive_folder_id(folder_id)
    
    def get_google_drive_folder_id(self) -> str:
        """Get Google Drive folder ID"""
        return self.__settings_manager.get_google_drive_folder_id()
    
    def set_google_drive_output_format(self, output_format: str):
        """Set Google Drive output format"""
        self.__settings_manager.set_google_drive_output_format(output_format)
    
    def get_google_drive_output_format(self) -> str:
        """Get Google Drive output format"""
        return self.__settings_manager.get_google_drive_output_format()
    
    def is_google_drive_authenticated(self) -> bool:
        """Check if Google Drive is authenticated"""
        return self.__settings_manager.get_google_drive_authenticated()
    
    def validate_google_drive_folder_id(self, folder_id: str) -> tuple[bool, str]:
        """Validate Google Drive folder ID"""
        # TODO: Implement actual validation
        return True, "Folder validation not implemented yet"
    
    def clear_google_drive_authentication(self):
        """Clear Google Drive authentication"""
        self.__settings_manager.set_google_drive_authenticated(False)
        # TODO: Remove authentication tokens