#!/usr/bin/env python3
"""
GUI CPU Monitor - Measures CPU usage while GUI is running
This script starts the GUI application and monitors CPU usage externally
"""

import os
import sys
import time
import psutil
import subprocess
import signal
import threading
from performance_profiler import profiler

def monitor_process_cpu(pid, duration=30):
    """Monitor CPU usage of a specific process"""
    try:
        process = psutil.Process(pid)
        cpu_readings = []
        memory_readings = []
        
        print(f"📊 Monitoring process {pid} for {duration} seconds...")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_mb = process.memory_info().rss / (1024 * 1024)
                thread_count = process.num_threads()
                
                cpu_readings.append(cpu_percent)
                memory_readings.append(memory_mb)
                
                elapsed = int(time.time() - start_time)
                print(f"   {elapsed}/{duration}s - CPU: {cpu_percent:5.1f}% | "
                      f"Memory: {memory_mb:5.1f}MB | Threads: {thread_count}", end='\r')
                
                time.sleep(1)
                
            except psutil.NoSuchProcess:
                print("\n❌ Process terminated")
                break
        
        print("\n✅ Monitoring completed")
        
        return {
            'cpu_readings': cpu_readings,
            'memory_readings': memory_readings,
            'cpu_avg': sum(cpu_readings) / len(cpu_readings) if cpu_readings else 0,
            'cpu_max': max(cpu_readings) if cpu_readings else 0,
            'memory_avg': sum(memory_readings) / len(memory_readings) if memory_readings else 0,
            'memory_max': max(memory_readings) if memory_readings else 0,
            'duration': duration
        }
        
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        return None

def start_gui_with_monitoring():
    """Start GUI and monitor its performance"""
    print("🚀 Starting GUI Application with CPU Monitoring")
    print("="*60)
    
    # Start the GUI application as a subprocess
    env = os.environ.copy()
    env['PYTHONPATH'] = '/Users/jwhaley/Developer/inception-ai-recorder'
    
    gui_process = None
    results = None
    
    try:
        # Start GUI process
        print("📱 Launching GUI application...")
        gui_process = subprocess.Popen([
            sys.executable, 
            'multitrack_recorder/main.py'
        ], 
        cwd='/Users/jwhaley/Developer/inception-ai-recorder',
        env=env)
        
        print(f"✅ GUI started with PID: {gui_process.pid}")
        print("💡 GUI Instructions (if you can see it):")
        print("   - Select 2-4 audio devices by clicking checkboxes")
        print("   - Observe waveforms and level meters")
        print("   - Let it run for 30 seconds for accurate measurement")
        
        # Give GUI time to fully start
        time.sleep(3)
        
        # Monitor CPU usage
        results = monitor_process_cpu(gui_process.pid, duration=30)
        
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring interrupted by user")
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
    finally:
        # Clean up
        if gui_process:
            try:
                print("\n🛑 Terminating GUI process...")
                gui_process.terminate()
                gui_process.wait(timeout=5)
                print("✅ GUI process terminated cleanly")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing GUI process...")
                gui_process.kill()
            except Exception as e:
                print(f"⚠️  Error terminating GUI: {e}")
    
    return results

def analyze_gui_performance(results):
    """Analyze GUI performance results"""
    print("\n" + "="*80)
    print("GUI PERFORMANCE ANALYSIS WITH ACTIVE UI")
    print("="*80)
    
    if not results:
        print("❌ No performance data available")
        return
    
    print(f"Duration: {results['duration']} seconds")
    print(f"CPU Usage: {results['cpu_avg']:.1f}% average, {results['cpu_max']:.1f}% peak")
    print(f"Memory: {results['memory_avg']:.1f} MB average, {results['memory_max']:.1f} MB peak")
    
    # Calculate high CPU percentage
    high_cpu_count = sum(1 for cpu in results['cpu_readings'] if cpu > 80)
    high_cpu_pct = high_cpu_count / len(results['cpu_readings']) * 100 if results['cpu_readings'] else 0
    
    print(f"High CPU (>80%): {high_cpu_count} samples ({high_cpu_pct:.1f}%)")
    
    # Performance comparison
    print(f"\n📊 COMPARISON WITH PREVIOUS RESULTS:")
    print(f"Headless audio processing: ~3.2% CPU")
    print(f"With active GUI: {results['cpu_avg']:.1f}% CPU")
    
    gui_overhead = results['cpu_avg'] - 3.2
    print(f"Estimated GUI overhead: ~{gui_overhead:.1f}% CPU")
    
    # Assessment
    print(f"\n🎯 GUI PERFORMANCE ASSESSMENT:")
    
    if results['cpu_avg'] < 10:
        print("✅ EXCELLENT: Very low CPU usage with GUI")
    elif results['cpu_avg'] < 20:
        print("✅ GOOD: Reasonable CPU usage with GUI")
    elif results['cpu_avg'] < 35:
        print("⚠️  MODERATE: GUI has noticeable CPU impact")
    else:
        print("❌ HIGH: GUI causes significant CPU usage")
    
    if high_cpu_pct < 5:
        print("✅ STABLE: Very few CPU spikes")
    elif high_cpu_pct < 20:
        print("⚠️  OCCASIONAL SPIKES: Some high CPU periods")
    else:
        print("❌ FREQUENT SPIKES: Regular high CPU usage")
    
    # Recommendations
    if gui_overhead > 25:
        print(f"\n💡 HIGH GUI OVERHEAD RECOMMENDATIONS:")
        print("   - Consider reducing waveform update frequency")
        print("   - Optimize matplotlib rendering operations")
        print("   - Reduce concurrent visual updates")
    elif gui_overhead > 10:
        print(f"\n💡 MODERATE GUI OVERHEAD - ACCEPTABLE:")
        print("   - GUI performance is reasonable for real-time audio")
        print("   - Monitor for any audio dropouts during heavy visual activity")
    else:
        print(f"\n🎉 EXCELLENT GUI EFFICIENCY:")
        print("   - GUI overhead is minimal")
        print("   - Optimizations are working very well")
    
    # Detailed breakdown
    if len(results['cpu_readings']) > 10:
        cpu_variance = max(results['cpu_readings']) - min(results['cpu_readings'])
        print(f"\n📈 CPU USAGE PATTERN:")
        print(f"CPU Variance: {cpu_variance:.1f}% (max - min)")
        
        if cpu_variance < 10:
            print("✅ CONSISTENT: Stable CPU usage")
        elif cpu_variance < 25:
            print("📊 VARIABLE: Some CPU usage fluctuation")
        else:
            print("⚠️  VOLATILE: Significant CPU usage variation")

def main():
    """Main function"""
    print("🎬 GUI Performance Monitoring with Active UI")
    
    results = start_gui_with_monitoring()
    analyze_gui_performance(results)

if __name__ == "__main__":
    main()