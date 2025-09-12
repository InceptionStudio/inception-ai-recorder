#!/usr/bin/env python3
"""
GUI Performance Profiling Script
Measures CPU usage and performance bottlenecks while the full GUI is active.
"""

import sys
import time
import threading
import cProfile
import pstats
import io
import os
from contextlib import contextmanager
from performance_profiler import profiler

# Add the project root to Python path
sys.path.insert(0, '/Users/jwhaley/Developer/inception-ai-recorder')

from multitrack_recorder.gui import MultitrackRecorderGUI
from multitrack_recorder.audio_manager import AudioManager
from multitrack_recorder.settings_manager import SettingsManager

class GUIProfiler:
    def __init__(self):
        self.pr = cProfile.Profile()
        self.gui_app = None
        self.profiling_thread = None
        self.stop_profiling = False
        
    def start_gui_profiling(self):
        """Start the GUI with integrated profiling"""
        print("🚀 Starting GUI Performance Profiler")
        print("="*60)
        
        # Start system profiling
        profiler.start_profiling()
        
        # Start code profiling in a separate thread
        self.profiling_thread = threading.Thread(target=self._profile_gui_thread, daemon=True)
        self.profiling_thread.start()
        
        print("📱 Launching GUI application...")
        print("👋 GUI Instructions:")
        print("   1. Select 2-4 audio devices")
        print("   2. Let it run for 30 seconds to collect metrics")
        print("   3. Close the application to see results")
        print("   4. Observe waveforms and level meters during operation")
        
        # Launch GUI
        try:
            self.gui_app = MultitrackRecorderGUI()
            
            # Hook into audio callbacks to count them
            original_level_callback = self.gui_app.on_level_update
            original_waveform_callback = self.gui_app.on_waveform_update
            
            def counting_level_callback(*args, **kwargs):
                profiler.record_gui_update()
                return original_level_callback(*args, **kwargs)
            
            def counting_waveform_callback(*args, **kwargs):
                profiler.record_gui_update()
                return original_waveform_callback(*args, **kwargs)
            
            # Replace callbacks with counting versions
            self.gui_app.on_level_update = counting_level_callback
            self.gui_app.on_waveform_update = counting_waveform_callback
            
            # Start the GUI main loop
            print("✅ GUI launched - interact with it now!")
            self.gui_app.root.mainloop()
            
        except KeyboardInterrupt:
            print("\n⏹️  GUI interrupted by user")
        except Exception as e:
            print(f"❌ GUI error: {e}")
        finally:
            self.stop_profiling = True
            
            # Stop system profiling
            profiler.stop_profiling()
            
            # Wait for profiling thread to finish
            if self.profiling_thread and self.profiling_thread.is_alive():
                self.profiling_thread.join(timeout=2)
    
    def _profile_gui_thread(self):
        """Background thread to profile GUI operations"""
        self.pr.enable()
        
        # Monitor for 60 seconds or until GUI closes
        start_time = time.time()
        while not self.stop_profiling and (time.time() - start_time) < 60:
            time.sleep(0.1)  # Small sleep to not overwhelm
            profiler.record_audio_callback()  # Simulate some activity tracking
        
        self.pr.disable()
    
    def get_profiling_stats(self):
        """Get formatted profiling statistics"""
        s = io.StringIO()
        ps = pstats.Stats(self.pr, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(40)  # Show top 40 functions
        return s.getvalue()
    
    def analyze_results(self):
        """Analyze and display performance results"""
        print("\n" + "="*80)
        print("GUI PERFORMANCE ANALYSIS RESULTS")
        print("="*80)
        
        # System-level metrics
        profiler.print_summary()
        
        # GUI-specific code profiling
        print("\n" + "="*80)
        print("TOP GUI PERFORMANCE HOTSPOTS")
        print("="*80)
        print(self.get_profiling_stats())
        
        # Analysis
        summary = profiler.get_summary()
        if summary:
            print(f"\n🔍 GUI PERFORMANCE ANALYSIS:")
            print(f"Average CPU: {summary['cpu_avg']:.1f}%")
            print(f"Peak CPU: {summary['cpu_max']:.1f}%")
            print(f"GUI Updates: {summary['gui_updates_avg']:.1f}/sec average")
            print(f"Thread Count: {summary['thread_avg']:.1f} average")
            print(f"Memory Usage: {summary['memory_avg_mb']:.1f} MB average")
            
            # GUI-specific recommendations
            print(f"\n🎯 GUI PERFORMANCE ASSESSMENT:")
            
            if summary['cpu_avg'] > 25:
                print("⚠️  HIGH CPU: GUI operations consuming significant resources")
                print("💡 Recommendations:")
                print("   - Reduce waveform update frequency")
                print("   - Consider simpler waveform rendering")
                print("   - Limit concurrent GUI updates")
            elif summary['cpu_avg'] > 15:
                print("⚠️  MODERATE CPU: GUI has some overhead")
                print("💡 Consider: Optimizing matplotlib operations")
            else:
                print("✅ EXCELLENT: GUI is very CPU efficient")
            
            if summary['gui_updates_avg'] > 100:
                print("⚠️  HIGH UPDATE RATE: Too many GUI updates")
                print("💡 Reduce update frequency to improve performance")
            elif summary['gui_updates_avg'] > 50:
                print("📊 MODERATE UPDATE RATE: GUI updates are reasonable")
            else:
                print("✅ OPTIMAL UPDATE RATE: GUI updates are well-controlled")
            
            # Memory analysis
            if summary['memory_max_mb'] - summary['memory_avg_mb'] > 20:
                print("⚠️  MEMORY VARIANCE: Significant memory fluctuation")
            else:
                print("✅ STABLE MEMORY: Memory usage is consistent")

def main():
    """Main function to run GUI profiling"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("GUI Performance Profiler")
        print("========================")
        print("This script launches the full GUI application with performance monitoring.")
        print("")
        print("Usage: python run_gui_profiler.py")
        print("")
        print("Instructions:")
        print("1. The GUI will launch automatically")
        print("2. Select multiple audio devices (2-4 recommended)")
        print("3. Observe the real-time waveforms and level meters")
        print("4. Let it run for at least 30 seconds")
        print("5. Close the application to see performance results")
        return
    
    profiler_instance = GUIProfiler()
    
    try:
        profiler_instance.start_gui_profiling()
    finally:
        # Always show results
        profiler_instance.analyze_results()

if __name__ == "__main__":
    main()