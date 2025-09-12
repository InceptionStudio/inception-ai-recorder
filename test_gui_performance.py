#!/usr/bin/env python3
"""
Automated GUI Performance Test
Simulates GUI operations and measures performance without requiring manual interaction.
"""

import sys
import time
import threading
import tkinter as tk
from unittest.mock import MagicMock
from performance_profiler import profiler

# Add the project root to Python path
sys.path.insert(0, '/Users/jwhaley/Developer/inception-ai-recorder')

from multitrack_recorder.audio_manager import AudioManager
from multitrack_recorder.settings_manager import SettingsManager
from multitrack_recorder.gui import MultitrackRecorderGUI, WaveformWidget
import numpy as np

class MockGUITest:
    """Simulates GUI operations for performance testing"""
    
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)
        self.mock_widgets = {}
        self.running = False
        
    def create_mock_widgets(self):
        """Create mock waveform widgets that simulate real GUI operations"""
        devices = self.audio_manager.get_input_devices()
        
        print(f"📱 Creating mock widgets for {len(devices)} devices")
        
        for device in devices[:4]:  # Test with up to 4 devices
            # Create a simplified mock widget that performs similar operations
            widget = MagicMock()
            
            # Mock the update methods to perform actual GUI-like work
            def mock_update_level(level):
                # Simulate level meter updates (lightweight)
                return level * 100  # Simple calculation
            
            def mock_update_waveform(data):
                # Simulate waveform rendering operations
                if data and len(data) > 10:
                    # Simulate numpy operations similar to real waveform widget
                    x_data = np.linspace(0, 100, len(data))
                    # Simulate some matplotlib-like operations
                    processed_data = np.array(data) * x_data / 100
                    return processed_data.tolist()
                return []
            
            widget.update_level = mock_update_level
            widget.update_waveform = mock_update_waveform
            
            self.mock_widgets[device.id] = widget
            
        print(f"✅ Created {len(self.mock_widgets)} mock widgets")
    
    def simulate_gui_callbacks(self, device_id, level, waveform_data):
        """Simulate GUI callback operations"""
        if device_id in self.mock_widgets:
            widget = self.mock_widgets[device_id]
            
            # Simulate level update
            widget.update_level(level)
            profiler.record_gui_update()
            
            # Simulate waveform update (more expensive)
            if waveform_data:
                widget.update_waveform(waveform_data)
                profiler.record_gui_update()
    
    def run_performance_test(self, duration=30):
        """Run automated performance test"""
        print("🚀 Starting Automated GUI Performance Test")
        print("="*60)
        
        # Setup
        self.create_mock_widgets()
        devices = list(self.mock_widgets.keys())
        
        if not devices:
            print("❌ No devices available for testing")
            return
        
        # Select devices for testing
        for device_id in devices:
            self.audio_manager.set_device_selected(device_id, True)
            print(f"✅ Selected device {device_id} for testing")
        
        # Set up callbacks
        self.audio_manager.set_level_callback(self._level_callback)
        self.audio_manager.set_waveform_callback(self._waveform_callback)
        
        print(f"\n⏱️  Running {duration}-second GUI performance test...")
        
        # Start profiling
        profiler.start_profiling()
        
        # Generate simulated audio data and GUI updates
        self.running = True
        gui_thread = threading.Thread(target=self._simulate_gui_updates, daemon=True)
        gui_thread.start()
        
        try:
            # Run for specified duration
            for i in range(duration):
                time.sleep(1)
                print(f"   {i+1}/{duration} seconds - GUI simulation running...", end='\r')
        
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted by user")
        
        finally:
            # Stop simulation
            self.running = False
            gui_thread.join(timeout=2)
            
            # Cleanup
            profiler.stop_profiling()
            
            for device_id in devices:
                self.audio_manager.set_device_selected(device_id, False)
            
            self.audio_manager.cleanup()
            
        print("\n✅ GUI performance test completed!")
    
    def _level_callback(self, device_id, level):
        """Audio level callback that triggers GUI updates"""
        self.simulate_gui_callbacks(device_id, level, None)
    
    def _waveform_callback(self, device_id, waveform_data):
        """Waveform callback that triggers GUI updates"""
        self.simulate_gui_callbacks(device_id, 0.5, waveform_data)
    
    def _simulate_gui_updates(self):
        """Background thread to simulate additional GUI operations"""
        while self.running:
            # Simulate periodic GUI operations
            for device_id in self.mock_widgets:
                # Simulate some GUI work
                fake_waveform = np.sin(np.linspace(0, 2*np.pi, 100)) * np.random.random()
                fake_level = np.random.random()
                
                self.simulate_gui_callbacks(device_id, fake_level, fake_waveform.tolist())
            
            time.sleep(0.02)  # ~50 FPS simulation
    
    def print_results(self):
        """Print performance analysis results"""
        print("\n" + "="*80)
        print("AUTOMATED GUI PERFORMANCE RESULTS")
        print("="*80)
        
        profiler.print_summary()
        
        summary = profiler.get_summary()
        if summary:
            print(f"\n🔍 GUI SIMULATION ANALYSIS:")
            print(f"Simulated GUI Updates: {summary['gui_updates_avg']:.1f}/sec")
            print(f"CPU Usage with GUI: {summary['cpu_avg']:.1f}% average")
            print(f"Memory with GUI: {summary['memory_avg_mb']:.1f} MB")
            print(f"Thread Count: {summary['thread_avg']:.1f}")
            
            # Compare with previous headless results
            print(f"\n📊 COMPARISON WITH HEADLESS OPERATION:")
            print(f"Previous headless CPU: ~3.2%")
            print(f"Current GUI CPU: {summary['cpu_avg']:.1f}%")
            gui_overhead = summary['cpu_avg'] - 3.2
            print(f"GUI Overhead: ~{gui_overhead:.1f}% CPU")
            
            if gui_overhead < 5:
                print("✅ EXCELLENT: GUI overhead is minimal")
            elif gui_overhead < 15:
                print("✅ GOOD: Reasonable GUI overhead")  
            elif gui_overhead < 30:
                print("⚠️  MODERATE: GUI has noticeable overhead")
            else:
                print("❌ HIGH: GUI overhead is significant")
            
            # Recommendations
            if summary['gui_updates_avg'] > 200:
                print("\n💡 RECOMMENDATIONS:")
                print("   - Reduce GUI update frequency")
                print("   - Consider lighter rendering methods")
            elif summary['cpu_avg'] > 20:
                print("\n💡 RECOMMENDATIONS:")
                print("   - Monitor CPU usage with real GUI")
                print("   - Consider optimizing matplotlib operations")
            else:
                print("\n🎉 GUI performance is excellent!")

def main():
    """Main function"""
    print("🎬 Automated GUI Performance Testing")
    
    test = MockGUITest()
    
    try:
        test.run_performance_test(30)
    finally:
        test.print_results()

if __name__ == "__main__":
    main()