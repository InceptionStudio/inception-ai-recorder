#!/usr/bin/env python3
"""
Performance profiler for the multitrack recorder.
Identifies CPU bottlenecks during multi-channel recording.
"""

import time
import threading
from typing import Dict, List
import os
from dataclasses import dataclass
import psutil

@dataclass  
class PerformanceMetrics:
    timestamp: float
    cpu_percent: float
    memory_mb: float
    thread_count: int
    audio_callbacks_per_sec: float = 0
    gui_updates_per_sec: float = 0

class PerformanceProfiler:
    """Real-time performance profiler for audio recording"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.running = False
        self.thread = None
        self.process = psutil.Process()
        
        # Counters for callbacks
        self.audio_callback_count = 0
        self.gui_update_count = 0
        self.last_callback_count = 0
        self.last_gui_count = 0
        
    def start_profiling(self):
        """Start performance monitoring"""
        self.running = True
        self.metrics.clear()
        self.thread = threading.Thread(target=self._profile_loop, daemon=True)
        self.thread.start()
        print("🔬 Performance profiler started")
        
    def stop_profiling(self):
        """Stop performance monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("🛑 Performance profiler stopped")
        
    def record_audio_callback(self):
        """Record audio callback occurrence"""
        self.audio_callback_count += 1
        
    def record_gui_update(self):
        """Record GUI update occurrence"""
        self.gui_update_count += 1
        
    def _profile_loop(self):
        """Main profiling loop"""
        last_time = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                time_delta = current_time - last_time
                
                # Get detailed system metrics
                cpu_percent = self.process.cpu_percent()
                memory_mb = self.process.memory_info().rss / (1024 * 1024)
                thread_count = self.process.num_threads()
                
                # Calculate callback rates
                audio_rate = (self.audio_callback_count - self.last_callback_count) / time_delta if time_delta > 0 else 0
                gui_rate = (self.gui_update_count - self.last_gui_count) / time_delta if time_delta > 0 else 0
                
                # Store metrics
                metrics = PerformanceMetrics(
                    timestamp=current_time,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    thread_count=thread_count,
                    audio_callbacks_per_sec=audio_rate,
                    gui_updates_per_sec=gui_rate
                )
                self.metrics.append(metrics)
                
                # Update counters
                self.last_callback_count = self.audio_callback_count
                self.last_gui_count = self.gui_update_count
                last_time = current_time
                
                # Log high CPU usage
                if cpu_percent > 80:
                    print(f"⚠️  HIGH CPU: {cpu_percent:.1f}% | "
                          f"Audio: {audio_rate:.1f}/s | GUI: {gui_rate:.1f}/s | "
                          f"Threads: {thread_count}")
                
                time.sleep(1.0)  # Sample every second
                
            except Exception as e:
                print(f"Profiler error: {e}")
                break
                
    def get_summary(self) -> Dict:
        """Get performance summary"""
        if not self.metrics:
            return {}
            
        cpu_values = [m.cpu_percent for m in self.metrics]
        memory_values = [m.memory_mb for m in self.metrics]
        thread_values = [m.thread_count for m in self.metrics]
        audio_values = [m.audio_callbacks_per_sec for m in self.metrics]
        gui_values = [m.gui_updates_per_sec for m in self.metrics]
        
        return {
            'duration_seconds': len(self.metrics),
            'cpu_avg': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            'cpu_max': max(cpu_values) if cpu_values else 0,
            'cpu_min': min(cpu_values) if cpu_values else 0,
            'memory_avg_mb': sum(memory_values) / len(memory_values) if memory_values else 0,
            'memory_max_mb': max(memory_values) if memory_values else 0,
            'thread_avg': sum(thread_values) / len(thread_values) if thread_values else 0,
            'thread_max': max(thread_values) if thread_values else 0,
            'audio_callbacks_avg': sum(audio_values) / len(audio_values) if audio_values else 0,
            'audio_callbacks_max': max(audio_values) if audio_values else 0,
            'gui_updates_avg': sum(gui_values) / len(gui_values) if gui_values else 0,
            'gui_updates_max': max(gui_values) if gui_values else 0,
            'high_cpu_samples': sum(1 for cpu in cpu_values if cpu > 80),
            'high_cpu_percentage': sum(1 for cpu in cpu_values if cpu > 80) / len(cpu_values) * 100 if cpu_values else 0
        }
        
    def print_summary(self):
        """Print performance summary"""
        summary = self.get_summary()
        if not summary:
            print("No performance data collected")
            return
            
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Duration: {summary['duration_seconds']} seconds")
        print(f"CPU Usage: {summary['cpu_avg']:.1f}% avg, {summary['cpu_max']:.1f}% peak")
        print(f"Memory: {summary['memory_avg_mb']:.1f} MB avg, {summary['memory_max_mb']:.1f} MB peak")
        print(f"Threads: {summary['thread_avg']:.1f} avg, {summary['thread_max']:.0f} peak")
        print(f"Audio Callbacks: {summary['audio_callbacks_avg']:.1f}/sec avg, {summary['audio_callbacks_max']:.1f}/sec peak")
        print(f"GUI Updates: {summary['gui_updates_avg']:.1f}/sec avg, {summary['gui_updates_max']:.1f}/sec peak")
        print(f"High CPU (>80%): {summary['high_cpu_samples']} samples ({summary['high_cpu_percentage']:.1f}%)")
        
        # Performance analysis
        print("\nPERFORMANCE ISSUES:")
        if summary['cpu_avg'] > 50:
            print("❌ HIGH: Average CPU usage is excessive")
        if summary['cpu_max'] > 90:
            print("❌ CRITICAL: Peak CPU usage causes audio dropouts")
        if summary['audio_callbacks_avg'] > 200:
            print("❌ HIGH: Too many audio callbacks per second")  
        if summary['gui_updates_avg'] > 100:
            print("❌ HIGH: Too many GUI updates per second")
        if summary['thread_max'] > 20:
            print("⚠️  Many threads active - potential contention")
            
        print("="*60)

# Global profiler instance
profiler = PerformanceProfiler()

if __name__ == "__main__":
    print("Performance profiler module - import and use profiler.start_profiling()")