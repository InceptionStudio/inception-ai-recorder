#!/usr/bin/env python3
"""
Detailed performance profiling script that measures CPU usage during multi-channel recording.
This script provides comprehensive analysis of where time is being spent.
"""

import sys
import time
import threading
import cProfile
import pstats
import io
from contextlib import contextmanager
from performance_profiler import profiler

# Add the project root to Python path
sys.path.insert(0, '/Users/jwhaley/Developer/inception-ai-recorder')

from multitrack_recorder.audio_manager import AudioManager
from multitrack_recorder.settings_manager import SettingsManager

class DetailedProfiler:
    def __init__(self):
        self.pr = cProfile.Profile()
        self.profiling = False
        
    @contextmanager
    def profile_context(self):
        """Context manager for code profiling"""
        self.pr.enable()
        self.profiling = True
        try:
            yield
        finally:
            self.pr.disable()
            self.profiling = False
    
    def get_stats(self, sort_by='cumulative', top_n=20):
        """Get formatted profiling statistics"""
        s = io.StringIO()
        ps = pstats.Stats(self.pr, stream=s)
        ps.sort_stats(sort_by)
        ps.print_stats(top_n)
        return s.getvalue()
    
    def print_hotspots(self):
        """Print the most time-consuming functions"""
        print("\n" + "="*80)
        print("TOP CPU HOTSPOTS (by cumulative time)")
        print("="*80)
        print(self.get_stats('cumulative', 30))
        
        print("\n" + "="*80)
        print("TOP CPU HOTSPOTS (by total time)")
        print("="*80)
        print(self.get_stats('tottime', 30))

def main():
    print("🔬 DETAILED PERFORMANCE PROFILING")
    print("="*60)
    
    # Initialize components
    settings_manager = SettingsManager()
    audio_manager = AudioManager(settings_manager)
    detailed_profiler = DetailedProfiler()
    
    # Get available devices
    devices = audio_manager.get_input_devices()
    print(f"📱 Found {len(devices)} audio devices")
    
    if len(devices) == 0:
        print("❌ No audio devices found")
        audio_manager.cleanup()
        return
    
    # Select multiple devices for testing (up to 4)
    selected_devices = devices[:min(4, len(devices))]
    print(f"🎙️  Testing with {len(selected_devices)} devices:")
    
    for device in selected_devices:
        print(f"   • {device.name} ({device.host_api})")
        audio_manager.set_device_selected(device.id, True)
    
    print(f"\n⏱️  Running 30-second profiled recording simulation...")
    
    # Start system-level profiling
    profiler.start_profiling()
    
    try:
        # Profile the audio processing
        with detailed_profiler.profile_context():
            print("🎯 Profiling started - simulating heavy load...")
            
            # Add some callback counting hooks
            original_level_callback = audio_manager._AudioManager__level_callback
            original_waveform_callback = audio_manager._AudioManager__waveform_callback
            
            def counting_level_callback(device_id, level):
                profiler.record_gui_update()
                if original_level_callback:
                    original_level_callback(device_id, level)
            
            def counting_waveform_callback(device_id, waveform):
                profiler.record_gui_update()
                if original_waveform_callback:
                    original_waveform_callback(device_id, waveform)
            
            # Set up counting callbacks
            audio_manager.set_level_callback(counting_level_callback)
            audio_manager.set_waveform_callback(counting_waveform_callback)
            
            # Let it run for 30 seconds
            for i in range(30):
                time.sleep(1)
                profiler.record_audio_callback()  # Simulate callback tracking
                print(f"   {i+1}/30 seconds - monitoring...", end='\r')
        
        print("\n✅ Profiling completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Profiling interrupted by user")
    
    finally:
        # Stop profiling
        profiler.stop_profiling()
        
        # Cleanup
        print("🧹 Cleaning up...")
        for device in selected_devices:
            audio_manager.set_device_selected(device.id, False)
        
        time.sleep(1)  # Allow cleanup to complete
        audio_manager.cleanup()
    
    # Analyze results
    print("\n📊 PERFORMANCE ANALYSIS")
    print("="*60)
    
    # System-level metrics
    profiler.print_summary()
    
    # Code-level hotspots
    detailed_profiler.print_hotspots()
    
    # Additional analysis
    summary = profiler.get_summary()
    if summary:
        print("\n🔍 DETAILED ANALYSIS:")
        print(f"Average threads: {summary['thread_avg']:.1f}")
        print(f"Peak threads: {summary['thread_max']}")
        print(f"Audio callback rate: {summary['audio_callbacks_avg']:.1f}/sec")
        print(f"GUI update rate: {summary['gui_updates_avg']:.1f}/sec")
        
        if summary['cpu_avg'] > 0:
            print(f"\n⚡ CPU EFFICIENCY:")
            callback_efficiency = summary['audio_callbacks_avg'] / summary['cpu_avg'] if summary['cpu_avg'] > 0 else 0
            print(f"Callbacks per CPU %: {callback_efficiency:.1f}")
            
            if callback_efficiency > 5:
                print("✅ EXCELLENT: High callback throughput per CPU unit")
            elif callback_efficiency > 2:
                print("✅ GOOD: Reasonable efficiency")
            else:
                print("⚠️  LOW EFFICIENCY: High CPU cost per callback")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    if summary and summary['cpu_avg'] > 50:
        print("❌ HIGH CPU: Consider reducing concurrent channels")
        print("💡 Try: Increase chunk size, reduce GUI update rate")
    elif summary and summary['gui_updates_avg'] > 60:
        print("⚠️  HIGH GUI LOAD: Consider reducing update frequency")
        print("💡 Try: Increase UI update interval")
    else:
        print("✅ Performance looks good for multi-channel recording")

if __name__ == "__main__":
    main()