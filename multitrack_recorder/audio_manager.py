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

@dataclass
class AudioDevice:
    """Represents an audio input device"""
    id: int
    name: str
    host_api: str
    max_input_channels: int
    max_output_channels: int
    default_low_input_latency: float
    default_sample_rate: float

STOP = object()

class AudioManager:
    """Manages audio devices and recording functionality"""
    
    # Fields/methods that start with "__" should only be accessed when _lock is held
    # or during initialization.
    def __init__(self):
        self.__audio = pyaudio.PyAudio()
        self.__input_devices: List[AudioDevice] = []
        self.__selected_devices: Dict[int, bool] = {}
        self.__listening_streams: Dict[int, pyaudio.Stream] = {}
        self.__listening_threads: Dict[int, threading.Thread] = {}
        self.__recording_files: Dict[int, wave.Wave_write] = {}
        self.__audio_data_queues: Dict[int, queue.Queue] = {}
        
        # Callbacks for UI updates
        self.__level_callback: Optional[Callable[[int, float], None]] = None
        self.__waveform_callback: Optional[Callable[[int, List[float]], None]] = None
        
        # Listening settings
        self.__sample_rate = 44100
        self.__channels = 1
        self.__sample_format = pyaudio.paInt16
        self.__chunk_size = 1024
        
        # Device labels
        self.__device_labels: Dict[int, str] = {}
        
        # Export directory
        self.__export_directory: Optional[Path] = None
        
        self.__is_recording = False
        self.__shutting_down = False
        self._lock = threading.Lock()
        self._bg_thread_pool = ThreadPoolExecutor(max_workers=1)
        self._callback_thread_pool = ThreadPoolExecutor(max_workers=2)
        
        self.__load_input_devices()
    
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
                    
                    device = AudioDevice(
                        id=i,
                        name=device_info['name'],
                        host_api=host_api_info['name'],
                        max_input_channels=device_info['maxInputChannels'],
                        max_output_channels=device_info['maxOutputChannels'],
                        default_low_input_latency=device_info['defaultLowInputLatency'],
                        default_sample_rate=device_info['defaultSampleRate']
                    )
                    self.__input_devices.append(device)
                    self.__selected_devices[i] = False
                    
            except Exception as e:
                print(f"Error loading device {i}: {e}")
        
        print(f"Loaded {len(self.__input_devices)} input devices")
    
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
    
    def __get_device_by_id(self, device_id: int) -> Optional[AudioDevice]:
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
    
    def set_device_selected(self, device_id: int, selected: bool):
        """Set device selection status"""
        should_start = False
        should_stop = False
        
        with self._lock:
            if device_id in self.__selected_devices:
                was_selected = self.__selected_devices[device_id]
                self.__selected_devices[device_id] = selected
                
                if selected and not was_selected:
                    should_start = True
                elif not selected and was_selected:
                    should_stop = True
        
        # Start or stop stream outside of lock to avoid deadlock
        if should_start:
            self._start_device_stream(device_id)
        elif should_stop:
            self._stop_device_stream(device_id)
    
    def is_device_selected(self, device_id: int) -> bool:
        """Check if device is selected"""
        with self._lock:
            return self.__selected_devices.get(device_id, False)
    
    def get_selected_device_ids(self) -> List[int]:
        """Get list of selected device IDs"""
        with self._lock:
            return self.__get_selected_device_ids()
    
    def __get_selected_device_ids(self) -> List[int]:
        """Get list of selected device IDs"""
        return [device_id for device_id, selected in self.__selected_devices.items() if selected]

    def set_device_label(self, device_id: int, label: str):
        """Set custom label for device"""
        with self._lock:
            self.__device_labels[device_id] = label
    
    def get_device_label(self, device_id: int) -> str:
        """Get custom label for device"""
        with self._lock:
            return self.__get_device_label(device_id)
    
    def __get_device_label(self, device_id: int) -> str:
        """Get custom label for device"""
        return self.__device_labels.get(device_id, "")
    
    def clear_device_label(self, device_id: int):
        """Clear custom label for device"""
        with self._lock:
            self.__device_labels.pop(device_id, None)
    
    def set_export_directory(self, directory: str):
        """Set the export directory for recordings"""
        with self._lock:
            self.__export_directory = Path(directory)
            if not self.__export_directory.exists():
                self.__export_directory.mkdir(parents=True, exist_ok=True)
    
    def get_export_directory(self) -> Optional[Path]:
        """Get the export directory for recordings"""
        with self._lock:
            return self.__export_directory
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        with self._lock:
            return self.__is_recording
    
    def set_level_callback(self, callback: Callable[[int, float], None]):
        """Set callback for audio level updates"""
        with self._lock:
            self.__level_callback = callback
    
    def set_waveform_callback(self, callback: Callable[[int, List[float]], None]):
        """Set callback for waveform data updates"""
        with self._lock:
            self.__waveform_callback = callback
    
    def _start_device_stream(self, device_id: int):
        """Start audio stream for a device"""
        with self._lock:
            if device_id in self.__listening_streams:
                return
            
            device = self.__get_device_by_id(device_id)
            if not device:
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
                    audio_data = np.frombuffer(in_data, dtype=np.int16).copy()
                    
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

                    self._bg_thread_pool.submit(_bg_audio_callback_ops)

                    return (in_data, pyaudio.paContinue)
                
                # Open stream
                stream = self.__audio.open(
                    format=self.__sample_format,
                    channels=self.__channels,
                    rate=self.__sample_rate,
                    frames_per_buffer=self.__chunk_size,
                    input=True,
                    input_device_index=device_id,
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
    
    def __stop_device_stream(self, device_id: int) -> threading.Thread:
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
        
    def _stop_device_stream(self, device_id: int):
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
    
    def __stop_all_streams(self):
        """Stop all active streams"""
        if not self.__listening_streams:
            return
        
        print(f"🛑 Stopping {len(self.__listening_streams)} active streams...")
        
        # Create a copy of the keys to avoid dictionary changed during iteration
        stream_ids = list(self.__listening_streams.keys())
        
        for device_id in stream_ids:
            try:
                self.__stop_device_stream(device_id)
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
                
                filepath = self.__export_directory / filename
                
                try:
                    # Create WAV file
                    wav_file = wave.open(str(filepath), 'wb')
                    wav_file.setnchannels(self.__channels)
                    wav_file.setsampwidth(2)  # 16-bit
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
    
    def _listening_worker(self, device_id: int):
        """Worker thread to handle listening on a specific device"""
        while True:
            wav_file = None
            is_recording = False
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
            
            try:
                # Get audio data from queue with timeout
                audio_data = audio_queue.get(timeout=2.0)
                if audio_data is STOP:
                    print(f"BGThread({device_id}): Exiting gracefully")
                    return
                
                # Process callbacks
                level_cb = None
                waveform_cb = None
                with self._lock:
                    if not self.__shutting_down and device_id in self.__listening_streams:
                        level_cb = self.__level_callback
                        waveform_cb = self.__waveform_callback

                if level_cb and not self.__shutting_down:
                    # Calculate RMS level (normalize int16 to 0-1 range)
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                    scaled_rms = min(1.0, rms / 32767.0)  # Normalize by max int16 value

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
                        self._callback_thread_pool.submit(_level_cb_task)
                else:
                    print(f"BGThread({device_id}): No level callback")

                if waveform_cb and not self.__shutting_down:
                    # Update waveform data (downsample for display)
                    downsample_factor = max(1, len(audio_data) // 100)
                    downsampled = audio_data[::downsample_factor]

                    # Scale int16 to -1.0 to 1.0 range for display
                    scaled_waveform = np.clip(downsampled.astype(np.float32) / 32767.0, -1.0, 1.0).tolist()

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
                        self._callback_thread_pool.submit(_waveform_cb_task)
                else:
                    print(f"BGThread({device_id}): No waveform callback")

                if wav_file is not None:
                    # Write int16 audio_data to WAV file
                    wav_file.writeframes(audio_data.tobytes())

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
                        print(f"BGThread({device_id}): Finalized recording {wav_file._file.name}")
                    except Exception as e:
                        print(f"BGThread({device_id}): Error closing file {wav_file._file.name}: {e}")
            
    
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