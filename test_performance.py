#!/usr/bin/env python3
"""
Performance test script for the optimized multitrack recorder.
Run this to verify performance improvements.
"""

import sys
import time
import threading
from performance_profiler import profiler

def main():
    print("🚀 Starting Performance Test")
    print("="*50)
    
    # Import here to ensure profiler is ready
    try:
        from multitrack_recorder.audio_manager import AudioManager
        from multitrack_recorder.settings_manager import SettingsManager
    except ImportError as e:
        print(f"❌ Import error: {e}")
        sys.exit(1)
    
    # Create audio manager
    settings_manager = SettingsManager()
    audio_manager = AudioManager(settings_manager)
    
    print("🎤 Available audio devices:")
    devices = audio_manager.get_input_devices()
    for i, device in enumerate(devices):
        print(f"  {i}: {device.name} ({device.host_api})")
    
    if len(devices) == 0:
        print("❌ No audio devices found")
        audio_manager.cleanup()
        return
    
    # Select first few devices for testing (up to 4)
    selected_devices = devices[:min(4, len(devices))]
    print(f"\n🔊 Testing with {len(selected_devices)} devices:")
    for device in selected_devices:
        print(f"  - {device.name}")
        audio_manager.set_device_selected(device.id, True)
    
    # Start profiling
    profiler.start_profiling()
    
    print("\n⏱️  Running 30-second performance test...")
    print("   (This simulates multi-channel recording load)")
    
    try:
        # Let the system run for 30 seconds
        for i in range(30):
            time.sleep(1)
            print(f"  {i+1}/30 seconds", end='\r')
        
        print("\n✅ Test completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    
    finally:
        # Stop profiling and get results
        profiler.stop_profiling()
        
        # Cleanup
        print("🧹 Cleaning up...")
        for device in selected_devices:
            audio_manager.set_device_selected(device.id, False)
        audio_manager.cleanup()
        
        # Show results
        print("\n📊 PERFORMANCE RESULTS:")
        profiler.print_summary()
        
        # Performance assessment
        summary = profiler.get_summary()
        if summary:
            print("\n🎯 ASSESSMENT:")
            if summary['cpu_avg'] < 30:
                print("✅ EXCELLENT: Low CPU usage, should handle many channels")
            elif summary['cpu_avg'] < 50:
                print("✅ GOOD: Moderate CPU usage, good for normal use")
            elif summary['cpu_avg'] < 70:
                print("⚠️  WARNING: High CPU usage, may cause issues with many channels")
            else:
                print("❌ CRITICAL: Very high CPU usage, optimization needed")
                
            if summary['high_cpu_percentage'] < 5:
                print("✅ LOW PEAK USAGE: Stable performance")
            elif summary['high_cpu_percentage'] < 20:
                print("⚠️  MODERATE PEAKS: Occasional high CPU usage")
            else:
                print("❌ HIGH PEAKS: Frequent CPU spikes may cause audio dropouts")

if __name__ == "__main__":
    main()