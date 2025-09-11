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
from typing import Dict, Any, Optional, List, Tuple
import threading


class SettingsManager:
    """Manages application settings with automatic save/load functionality"""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = Path(settings_file)
        self.__settings: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._auto_save = True
        
        # Default settings
        from platformdirs import user_downloads_path
        downloads_path = str(user_downloads_path())
        
        self._default_settings = {
            "google_drive": {
                "enabled": False,
                "folder_id": "",
                "authenticated": False,
                "output_format": "opus"  # Output format: wav, mp3, opus
            },
            "export_directory": downloads_path,
            "session_title": "",
            "device_labels": {},
            "device_gains": {},  # Device gain settings in dB
            "device_mapping": {},  # Dict mapping id -> name for persistence
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
                    self.__settings = self._default_settings.copy()
                    self.__settings.update(loaded_settings)
                    
                    print(f"✅ Loaded settings from {self.settings_file}")
                    return True
                else:
                    # Use defaults if file doesn't exist
                    self.__settings = self._default_settings.copy()
                    print("📝 Using default settings")
                    return True
                    
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
            self.__settings = self._default_settings.copy()
            return False
    
    def save_settings(self) -> bool:
        """Save settings to file"""
        try:
            with self._lock:
                return self.__save_settings_internal()
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            return False
    
    def __save_settings_internal(self) -> bool:
        """Internal save method that assumes lock is already held"""
        try:
            # Ensure directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.__settings, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved settings to {self.settings_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        with self._lock:
            keys = key.split('.')
            value = self.__settings
            
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
                current = self.__settings
                
                # Navigate to the parent of the target key
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # Set the value
                current[keys[-1]] = value
                
                # Auto-save if enabled
                if auto_save and self._auto_save:
                    self.__save_settings_internal()
                
                return True
                
        except Exception as e:
            print(f"❌ Error setting {key}: {e}")
            return False
    
    def get_google_drive_enabled(self) -> bool:
        """Get Google Drive enabled setting"""
        return bool(self.get_setting("google_drive.enabled", False))
    
    def set_google_drive_enabled(self, enabled: bool) -> bool:
        """Set Google Drive enabled setting"""
        return self.set_setting("google_drive.enabled", enabled)
    
    def get_google_drive_folder_id(self) -> str:
        """Get Google Drive folder ID setting"""
        return str(self.get_setting("google_drive.folder_id", ""))
    
    def set_google_drive_folder_id(self, folder_id: str) -> bool:
        """Set Google Drive folder ID setting"""
        return self.set_setting("google_drive.folder_id", folder_id)
    
    def get_google_drive_authenticated(self) -> bool:
        """Get Google Drive authenticated setting"""
        return bool(self.get_setting("google_drive.authenticated", False))
    
    def set_google_drive_authenticated(self, authenticated: bool) -> bool:
        """Set Google Drive authenticated setting"""
        return self.set_setting("google_drive.authenticated", authenticated)
    
    def get_export_directory(self) -> str:
        """Get export directory setting"""
        return str(self.get_setting("export_directory", ""))
    
    def set_export_directory(self, directory: str) -> bool:
        """Set export directory setting"""
        return self.set_setting("export_directory", directory)
    
    def get_session_title(self) -> str:
        """Get session title setting"""
        return str(self.get_setting("session_title", ""))
    
    def set_session_title(self, title: str) -> bool:
        """Set session title setting"""
        return self.set_setting("session_title", title)
    
    def get_device_label(self, device_id: str) -> str:
        """Get device label setting"""
        labels = self.get_setting("device_labels", {})
        return str(labels.get(device_id, ""))
    
    def set_device_label(self, device_id: str, label: str) -> bool:
        """Set device label setting"""
        labels = self.get_setting("device_labels", {})
        if label:
            labels[device_id] = label
        else:
            labels.pop(device_id, None)
        return self.set_setting("device_labels", labels)
    
    def get_device_gain(self, device_id: str) -> float:
        """Get device gain setting in dB"""
        gains = self.get_setting("device_gains", {})
        return float(gains.get(device_id, 0.0))
    
    def set_device_gain(self, device_id: str, gain_db: float) -> bool:
        """Set device gain setting in dB"""
        gains = self.get_setting("device_gains", {})
        gains[device_id] = gain_db
        return self.set_setting("device_gains", gains)
    
    def get_last_used_devices(self) -> list:
        """Get last used device IDs"""
        return list(self.get_setting("last_used_devices", []))
    
    def set_last_used_devices(self, device_ids: list) -> bool:
        """Set last used device IDs"""
        return self.set_setting("last_used_devices", device_ids)
    
    def get_window_geometry(self) -> str:
        """Get window geometry setting"""
        return str(self.get_setting("window_geometry", "900x600"))
    
    def set_window_geometry(self, geometry: str) -> bool:
        """Set window geometry setting"""
        return self.set_setting("window_geometry", geometry)
    
    def get_google_drive_output_format(self) -> str:
        """Get Google Drive output format setting"""
        drive_settings = self.get_setting("google_drive", {})
        return str(drive_settings.get("output_format", "opus"))
    
    def set_google_drive_output_format(self, output_format: str) -> bool:
        """Set Google Drive output format setting"""
        drive_settings = self.get_setting("google_drive", {})
        drive_settings["output_format"] = output_format
        return self.set_setting("google_drive", drive_settings)
    
    def clear_google_drive_settings(self) -> bool:
        """Clear all Google Drive settings"""
        return self.set_setting("google_drive", {
            "enabled": False,
            "folder_id": "",
            "authenticated": False,
            "output_format": "opus"
        })
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings (for debugging)"""
        with self._lock:
            return self.__settings.copy()
    
    def set_auto_save(self, enabled: bool) -> None:
        """Enable or disable auto-save"""
        self._auto_save = enabled
    
    def force_save(self) -> bool:
        """Force save settings regardless of auto-save setting"""
        return self.save_settings()
    
    def mark_file_uploaded(self, file_path: str, file_size: int, file_mtime: float) -> None:
        """Mark a file as uploaded with its metadata"""
        with self._lock:
            uploaded_files = self.__settings.get("uploaded_files", {})
            uploaded_files[file_path] = {
                "size": file_size,
                "mtime": file_mtime,
                "uploaded_at": time.time()
            }
            self.__settings["uploaded_files"] = uploaded_files
            
            if self._auto_save:
                self.__save_settings_internal()
    
    def is_file_uploaded(self, file_path: str) -> bool:
        """Check if a file has already been uploaded"""
        with self._lock:
            uploaded_files = self.__settings.get("uploaded_files", {})
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
                    self.__settings["uploaded_files"] = uploaded_files
                    return False
                
                return True
            except (OSError, KeyError):
                # File doesn't exist or entry is corrupted
                if file_path in uploaded_files:
                    del uploaded_files[file_path]
                    self.__settings["uploaded_files"] = uploaded_files
                return False
    
    def clear_uploaded_files(self) -> None:
        """Clear all uploaded file tracking"""
        with self._lock:
            self.__settings["uploaded_files"] = {}
            if self._auto_save:
                self.__save_settings_internal()
    
    def get_device_mapping(self) -> Dict[str, str]:
        """Get device mapping (dict mapping id -> name)"""
        mapping = self.get_setting("device_mapping", {})
        return {str(k): str(v) for k, v in mapping.items()}
    
    def set_device_mapping(self, mapping: Dict[str, str]) -> bool:
        """Set device mapping (dict mapping id -> name)"""
        return self.set_setting("device_mapping", mapping)
    
    def remap_device_ids(self, current_devices: Dict[str, str]) -> bool:
        """
        Remap device IDs in settings based on current device mapping.
        
        Args:
            current_devices: Dict mapping id -> name for current devices
            
        Returns:
            bool: True if remapping was successful
        """
        try:
            with self._lock:
                # Get the stored device mapping (id -> name)
                stored_devices = self.__settings.get("device_mapping", {})
                
                if not stored_devices:
                    # No stored mapping, just save current devices
                    self.__settings["device_mapping"] = current_devices
                    self.__save_settings_internal()
                    return True
                
                # Create mapping from old ID to new ID using best match strategy
                old_to_new_id = {}
                next_negative_id = -1
                used_current_ids = set()
                
                # For each stored device, find the best match in current devices
                for stored_id, stored_name in stored_devices.items():
                    # Find matching current devices with the same name
                    matching_current = [(dev_id, name) for dev_id, name in current_devices.items() if name == stored_name]
                    
                    if len(matching_current) == 1:
                        # Perfect match - one device with same name
                        new_id = matching_current[0][0]  # dev_id is first element
                        if new_id not in used_current_ids:
                            old_to_new_id[stored_id] = new_id
                            used_current_ids.add(new_id)
                            if stored_id != new_id:
                                print(f"⚠️ Remapping {stored_name} from {stored_id} to {new_id}")
                    elif len(matching_current) > 1:
                        # Multiple devices with same name - use position-based matching
                        for new_id, _ in matching_current:  # dev_id, name
                            if new_id not in used_current_ids:
                                # This ID has not been matched before, match it now.
                                old_to_new_id[stored_id] = new_id
                                used_current_ids.add(new_id)
                                if stored_id != new_id:
                                    print(f"⚠️ Remapping {stored_name} (non-unique) from {stored_id} to {new_id}")
                                break

                    if stored_id not in old_to_new_id:
                        # No match - assign negative ID to preserve settings
                        new_id = str(next_negative_id)
                        old_to_new_id[stored_id] = new_id
                        if stored_id != new_id:
                            print(f"⚠️ Preserving old device {stored_name} (ID {stored_id}) with negative ID {new_id}")
                        next_negative_id -= 1
                
                # Remap device_labels - keep all labels, including those with negative IDs for old devices
                device_labels = self.__settings.get("device_labels", {})
                new_device_labels = {}
                for old_id_str, label in device_labels.items():
                    if old_id_str in old_to_new_id:
                        new_id = old_to_new_id[old_id_str]
                        new_device_labels[new_id] = label
                self.__settings["device_labels"] = new_device_labels
                
                # Remap device_gains - keep all gains, including those with negative IDs for old devices
                device_gains = self.__settings.get("device_gains", {})
                new_device_gains = {}
                for old_id_str, gain in device_gains.items():
                    if old_id_str in old_to_new_id:
                        new_id = old_to_new_id[old_id_str]
                        new_device_gains[new_id] = gain
                self.__settings["device_gains"] = new_device_gains
                
                # Remap last_used_devices - only keep devices with positive IDs (current devices)
                last_used_devices = self.__settings.get("last_used_devices", [])
                new_last_used_devices = []
                for old_id in last_used_devices:
                    if old_id in old_to_new_id:
                        try:
                            # Only add to last_used_devices if it's a positive ID (current device)
                            new_id = old_to_new_id[old_id]
                            if int(new_id) >= 0:
                                new_last_used_devices.append(new_id)
                        except ValueError:
                            # Not an integer, skip it.
                            pass
                self.__settings["last_used_devices"] = new_last_used_devices
                
                # Update the device mapping - include current devices and old devices with negative IDs
                updated_device_mapping = current_devices.copy()
                
                # Add old devices with negative IDs to the mapping
                for stored_id, stored_name in stored_devices.items():
                    if stored_id in old_to_new_id:
                        new_id = old_to_new_id[stored_id]
                        if new_id not in updated_device_mapping:
                            # This is an old device with negative ID
                            updated_device_mapping[new_id] = stored_name
                
                self.__settings["device_mapping"] = updated_device_mapping
                
                # Save all changes
                self.__save_settings_internal()
                
                print(f"✅ Remapped {len(old_to_new_id)} device IDs")
                return True
                
        except Exception as e:
            print(f"❌ Error remapping device IDs: {e}")
            return False
