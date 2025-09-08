"""
Settings Manager for Multitrack Audio Recorder

Handles saving and loading application settings including:
- Google Drive configuration
- Export directory
- Device labels
- Other user preferences
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import threading


class SettingsManager:
    """Manages application settings with automatic save/load functionality"""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = Path(settings_file)
        self._settings: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._auto_save = True
        
        # Default settings
        from platformdirs import user_downloads_path
        downloads_path = str(user_downloads_path())
        
        self._default_settings = {
            "google_drive": {
                "enabled": False,
                "folder_id": "",
                "authenticated": False
            },
            "export_directory": downloads_path,
            "session_title": "",
            "device_labels": {},
            "device_gains": {},  # Device gain settings in dB
            "window_geometry": "900x600",
            "last_used_devices": [],
            "uploaded_files": {}  # Track uploaded files by file path and modification time
        }
        
        self.load_settings()
    
    def load_settings(self) -> bool:
        """Load settings from file"""
        try:
            with self._lock:
                if self.settings_file.exists():
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        loaded_settings = json.load(f)
                    
                    # Merge with defaults to handle new settings
                    self._settings = self._default_settings.copy()
                    self._settings.update(loaded_settings)
                    
                    print(f"✅ Loaded settings from {self.settings_file}")
                    return True
                else:
                    # Use defaults if file doesn't exist
                    self._settings = self._default_settings.copy()
                    print("📝 Using default settings")
                    return True
                    
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
            self._settings = self._default_settings.copy()
            return False
    
    def save_settings(self) -> bool:
        """Save settings to file"""
        try:
            with self._lock:
                return self._save_settings_internal()
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            return False
    
    def _save_settings_internal(self) -> bool:
        """Internal save method that assumes lock is already held"""
        try:
            # Ensure directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved settings to {self.settings_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        with self._lock:
            keys = key.split('.')
            value = self._settings
            
            try:
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default
    
    def set_setting(self, key: str, value: Any, auto_save: bool = True) -> bool:
        """Set a setting value"""
        try:
            with self._lock:
                keys = key.split('.')
                current = self._settings
                
                # Navigate to the parent of the target key
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # Set the value
                current[keys[-1]] = value
                
                # Auto-save if enabled
                if auto_save and self._auto_save:
                    self._save_settings_internal()
                
                return True
                
        except Exception as e:
            print(f"❌ Error setting {key}: {e}")
            return False
    
    def get_google_drive_enabled(self) -> bool:
        """Get Google Drive enabled setting"""
        return self.get_setting("google_drive.enabled", False)
    
    def set_google_drive_enabled(self, enabled: bool) -> bool:
        """Set Google Drive enabled setting"""
        return self.set_setting("google_drive.enabled", enabled)
    
    def get_google_drive_folder_id(self) -> str:
        """Get Google Drive folder ID setting"""
        return self.get_setting("google_drive.folder_id", "")
    
    def set_google_drive_folder_id(self, folder_id: str) -> bool:
        """Set Google Drive folder ID setting"""
        return self.set_setting("google_drive.folder_id", folder_id)
    
    def get_google_drive_authenticated(self) -> bool:
        """Get Google Drive authenticated setting"""
        return self.get_setting("google_drive.authenticated", False)
    
    def set_google_drive_authenticated(self, authenticated: bool) -> bool:
        """Set Google Drive authenticated setting"""
        return self.set_setting("google_drive.authenticated", authenticated)
    
    def get_export_directory(self) -> str:
        """Get export directory setting"""
        return self.get_setting("export_directory", "")
    
    def set_export_directory(self, directory: str) -> bool:
        """Set export directory setting"""
        return self.set_setting("export_directory", directory)
    
    def get_session_title(self) -> str:
        """Get session title setting"""
        return self.get_setting("session_title", "")
    
    def set_session_title(self, title: str) -> bool:
        """Set session title setting"""
        return self.set_setting("session_title", title)
    
    def get_device_label(self, device_id: int) -> str:
        """Get device label setting"""
        labels = self.get_setting("device_labels", {})
        return labels.get(str(device_id), "")
    
    def set_device_label(self, device_id: int, label: str) -> bool:
        """Set device label setting"""
        labels = self.get_setting("device_labels", {})
        if label:
            labels[str(device_id)] = label
        else:
            labels.pop(str(device_id), None)
        return self.set_setting("device_labels", labels)
    
    def get_device_gain(self, device_id: int) -> float:
        """Get device gain setting in dB"""
        gains = self.get_setting("device_gains", {})
        return gains.get(str(device_id), 0.0)
    
    def set_device_gain(self, device_id: int, gain_db: float) -> bool:
        """Set device gain setting in dB"""
        gains = self.get_setting("device_gains", {})
        gains[str(device_id)] = gain_db
        return self.set_setting("device_gains", gains)
    
    def get_last_used_devices(self) -> list:
        """Get last used device IDs"""
        return self.get_setting("last_used_devices", [])
    
    def set_last_used_devices(self, device_ids: list) -> bool:
        """Set last used device IDs"""
        return self.set_setting("last_used_devices", device_ids)
    
    def get_window_geometry(self) -> str:
        """Get window geometry setting"""
        return self.get_setting("window_geometry", "900x600")
    
    def set_window_geometry(self, geometry: str) -> bool:
        """Set window geometry setting"""
        return self.set_setting("window_geometry", geometry)
    
    def clear_google_drive_settings(self) -> bool:
        """Clear all Google Drive settings"""
        return self.set_setting("google_drive", {
            "enabled": False,
            "folder_id": "",
            "authenticated": False
        })
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings (for debugging)"""
        with self._lock:
            return self._settings.copy()
    
    def set_auto_save(self, enabled: bool):
        """Enable or disable auto-save"""
        self._auto_save = enabled
    
    def force_save(self) -> bool:
        """Force save settings regardless of auto-save setting"""
        return self.save_settings()
    
    def mark_file_uploaded(self, file_path: str, file_size: int, file_mtime: float):
        """Mark a file as uploaded with its metadata"""
        with self._lock:
            uploaded_files = self._settings.get("uploaded_files", {})
            uploaded_files[file_path] = {
                "size": file_size,
                "mtime": file_mtime,
                "uploaded_at": time.time()
            }
            self._settings["uploaded_files"] = uploaded_files
            
            if self._auto_save:
                self._save_settings_internal()
    
    def is_file_uploaded(self, file_path: str) -> bool:
        """Check if a file has already been uploaded"""
        with self._lock:
            uploaded_files = self._settings.get("uploaded_files", {})
            if file_path not in uploaded_files:
                return False
            
            # Check if file still exists and has same size/mtime
            try:
                import os
                stat = os.stat(file_path)
                file_info = uploaded_files[file_path]
                
                # File has been modified if size or mtime changed
                if (stat.st_size != file_info["size"] or 
                    stat.st_mtime != file_info["mtime"]):
                    # Remove outdated entry
                    del uploaded_files[file_path]
                    self._settings["uploaded_files"] = uploaded_files
                    return False
                
                return True
            except (OSError, KeyError):
                # File doesn't exist or entry is corrupted
                if file_path in uploaded_files:
                    del uploaded_files[file_path]
                    self._settings["uploaded_files"] = uploaded_files
                return False
    
    def clear_uploaded_files(self):
        """Clear all uploaded file tracking"""
        with self._lock:
            self._settings["uploaded_files"] = {}
            if self._auto_save:
                self._save_settings_internal()
