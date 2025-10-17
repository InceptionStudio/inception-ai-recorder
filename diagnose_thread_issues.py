#!/usr/bin/env python3
"""
Diagnostic tool to identify root causes of thread issues.

This script monitors the audio system in real-time and reports:
1. When threads stop processing audio
2. Why threads exit or die
3. Queue depth and overflow issues
4. Lock contention and blocking
5. Callback failures
"""

import sys
import time
import threading
import queue
import traceback
from collections import defaultdict
from datetime import datetime

# Add package to path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multitrack_recorder.audio_manager import AudioManager, STOP
from multitrack_recorder.settings_manager import SettingsManager


class ThreadDiagnostics:
    """Real-time diagnostics for thread health"""

    def __init__(self):
        self.callback_counts = defaultdict(int)
        self.callback_errors = defaultdict(int)
        self.queue_overflows = defaultdict(int)
        self.thread_exits = []
        self.lock_waits = defaultdict(list)
        self.activity_gaps = defaultdict(list)
        self.last_activity = defaultdict(float)

    def log_callback(self, device_id: str):
        """Log a callback execution"""
        self.callback_counts[device_id] += 1
        self.last_activity[device_id] = time.time()

    def log_callback_error(self, device_id: str, error: str):
        """Log a callback error"""
        self.callback_errors[device_id] += 1
        print(f"🔴 CALLBACK ERROR on device {device_id}: {error}")

    def log_queue_overflow(self, device_id: str):
        """Log a queue overflow"""
        self.queue_overflows[device_id] += 1
        print(f"⚠️ QUEUE OVERFLOW on device {device_id}")

    def log_thread_exit(self, device_id: str, reason: str):
        """Log a thread exit"""
        self.thread_exits.append({
            'device_id': device_id,
            'reason': reason,
            'time': datetime.now(),
            'stack': traceback.format_stack()
        })
        print(f"🛑 THREAD EXIT: device {device_id}, reason: {reason}")

    def check_activity_gaps(self):
        """Check for gaps in activity"""
        current_time = time.time()
        for device_id, last_time in self.last_activity.items():
            gap = current_time - last_time
            if gap > 5.0:  # 5 second gap
                if device_id not in self.activity_gaps or \
                   (self.activity_gaps[device_id] and current_time - self.activity_gaps[device_id][-1] > 10.0):
                    self.activity_gaps[device_id].append(current_time)
                    print(f"⏸️ ACTIVITY GAP: device {device_id} has {gap:.1f}s gap in audio processing")

    def print_summary(self):
        """Print diagnostic summary"""
        print("\n" + "="*80)
        print("THREAD DIAGNOSTICS SUMMARY")
        print("="*80)

        print("\n📊 CALLBACK STATISTICS:")
        for device_id, count in self.callback_counts.items():
            print(f"  Device {device_id}: {count:,} callbacks")
            if device_id in self.callback_errors:
                print(f"    ❌ {self.callback_errors[device_id]} errors")
            if device_id in self.queue_overflows:
                print(f"    ⚠️ {self.queue_overflows[device_id]} queue overflows")

        print("\n🛑 THREAD EXITS:")
        if not self.thread_exits:
            print("  ✅ No unexpected thread exits")
        else:
            for exit_info in self.thread_exits:
                print(f"  Device {exit_info['device_id']}: {exit_info['reason']} at {exit_info['time']}")

        print("\n⏸️ ACTIVITY GAPS:")
        if not self.activity_gaps:
            print("  ✅ No significant activity gaps")
        else:
            for device_id, gaps in self.activity_gaps.items():
                print(f"  Device {device_id}: {len(gaps)} gaps detected")

        print("\n" + "="*80)


def inject_diagnostics(audio_manager: AudioManager, diagnostics: ThreadDiagnostics):
    """Inject diagnostic hooks into the audio manager"""

    # We'll monitor by inspecting internal state periodically
    # This is less invasive than patching methods

    def monitor_worker():
        """Background monitoring thread"""
        print("🔍 Diagnostic monitor started")

        while True:
            try:
                time.sleep(1.0)

                # Check for activity gaps
                diagnostics.check_activity_gaps()

                # Check thread states
                with audio_manager._lock:
                    threads = audio_manager._AudioManager__listening_threads
                    queues = audio_manager._AudioManager__audio_data_queues
                    streams = audio_manager._AudioManager__listening_streams
                    selected = audio_manager._AudioManager__selected_devices

                    # Check for selected devices without threads
                    for device_id, is_selected in selected.items():
                        if is_selected:
                            if device_id not in threads:
                                print(f"❌ MISSING THREAD: Device {device_id} is selected but has no thread")
                            elif device_id not in queues:
                                print(f"❌ MISSING QUEUE: Device {device_id} is selected but has no queue")
                            elif device_id not in streams:
                                print(f"❌ MISSING STREAM: Device {device_id} is selected but has no stream")
                            else:
                                # Check thread is alive
                                thread = threads[device_id]
                                if not thread.is_alive():
                                    diagnostics.log_thread_exit(device_id, "Thread died unexpectedly")

                                # Check queue depth
                                q = queues[device_id]
                                qsize = q.qsize()
                                if qsize > 10:
                                    print(f"⚠️ QUEUE BUILDUP: Device {device_id} queue has {qsize} items")

                                # Estimate callback activity by queue activity
                                if qsize > 0:
                                    diagnostics.log_callback(device_id)

            except Exception as e:
                print(f"❌ Monitor error: {e}")
                traceback.print_exc()

    monitor_thread = threading.Thread(target=monitor_worker, daemon=True, name="DiagnosticMonitor")
    monitor_thread.start()


def run_diagnostics(duration: int = 60):
    """Run diagnostic monitoring for specified duration"""
    print("="*80)
    print("AUDIO THREAD DIAGNOSTICS")
    print("="*80)
    print(f"Monitoring for {duration} seconds...")
    print()

    # Create audio manager
    settings_manager = SettingsManager()
    audio_manager = AudioManager(settings_manager)

    # Create diagnostics tracker
    diagnostics = ThreadDiagnostics()

    # Get available devices
    devices = audio_manager.get_input_devices()
    if len(devices) == 0:
        print("❌ No audio devices found")
        return

    print(f"📱 Found {len(devices)} audio devices:")
    for device in devices:
        print(f"  {device.id}: {device.name}")
    print()

    # Select first device for testing
    test_device = devices[0]
    print(f"🎤 Testing with device: {test_device.name}")
    print()

    # Inject diagnostics
    inject_diagnostics(audio_manager, diagnostics)

    # Select device to start thread
    print("▶️ Starting device stream...")
    audio_manager.set_device_selected(test_device.id, True)
    time.sleep(2.0)

    # Monitor for duration
    print(f"⏱️ Monitoring for {duration} seconds...")
    print("   Watch for:")
    print("   - Thread exits")
    print("   - Activity gaps")
    print("   - Queue overflows")
    print("   - Missing threads/queues/streams")
    print()

    start_time = time.time()
    last_status = time.time()

    try:
        while time.time() - start_time < duration:
            time.sleep(1.0)

            # Print status every 10 seconds
            if time.time() - last_status > 10.0:
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                print(f"⏳ {elapsed:.0f}s elapsed, {remaining:.0f}s remaining...")
                last_status = time.time()

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring interrupted by user")

    # Print summary
    diagnostics.print_summary()

    # Cleanup
    print("\n🧹 Cleaning up...")
    audio_manager.set_device_selected(test_device.id, False)
    time.sleep(1.0)
    audio_manager.cleanup()

    print("\n✅ Diagnostics complete")


# ROOT CAUSE ANALYSIS SCENARIOS

def test_scenario_queue_starvation():
    """Test if thread can starve waiting on empty queue"""
    print("\n" + "="*80)
    print("SCENARIO 1: Queue Starvation Test")
    print("="*80)
    print("Testing if thread gets stuck waiting for queue data...")
    print()

    settings_manager = SettingsManager()
    audio_manager = AudioManager(settings_manager)

    devices = audio_manager.get_input_devices()
    if len(devices) == 0:
        print("❌ No devices available")
        return

    device_id = devices[0].id
    print(f"Testing with device {device_id}")

    # Start device
    audio_manager.set_device_selected(device_id, True)
    time.sleep(2.0)

    # Check if thread is processing
    with audio_manager._lock:
        last_activity = audio_manager._AudioManager__thread_last_activity.get(device_id, 0)

    print(f"Initial activity: {last_activity}")

    # Wait and check again
    time.sleep(3.0)

    with audio_manager._lock:
        new_activity = audio_manager._AudioManager__thread_last_activity.get(device_id, 0)
        thread = audio_manager._AudioManager__listening_threads.get(device_id)

    print(f"Activity after 3s: {new_activity}")
    print(f"Thread alive: {thread.is_alive() if thread else 'No thread'}")

    if new_activity > last_activity:
        print("✅ Thread is actively processing audio")
    else:
        print("❌ Thread appears stuck - no activity updates")

    # Cleanup
    audio_manager.set_device_selected(device_id, False)
    audio_manager.cleanup()


def test_scenario_callback_failure():
    """Test what happens if audio callback stops being called"""
    print("\n" + "="*80)
    print("SCENARIO 2: Callback Failure Detection")
    print("="*80)
    print("Monitoring callback frequency...")
    print()

    settings_manager = SettingsManager()
    audio_manager = AudioManager(settings_manager)

    devices = audio_manager.get_input_devices()
    if len(devices) == 0:
        print("❌ No devices available")
        return

    device_id = devices[0].id

    # Start device
    audio_manager.set_device_selected(device_id, True)
    time.sleep(1.0)

    # Monitor queue activity as proxy for callback activity
    activity_samples = []

    for i in range(10):
        time.sleep(1.0)
        with audio_manager._lock:
            queue_obj = audio_manager._AudioManager__audio_data_queues.get(device_id)
            if queue_obj:
                qsize = queue_obj.qsize()
                activity_samples.append(qsize)
                print(f"  Sample {i+1}: queue depth = {qsize}")
            else:
                print(f"  Sample {i+1}: no queue found")

    # Analysis
    avg_depth = sum(activity_samples) / len(activity_samples) if activity_samples else 0
    print(f"\nAverage queue depth: {avg_depth:.1f}")

    if avg_depth > 0:
        print("✅ Audio callback is actively pushing data")
    else:
        print("❌ Audio callback may not be functioning")

    # Cleanup
    audio_manager.set_device_selected(device_id, False)
    audio_manager.cleanup()


def test_scenario_lock_contention():
    """Test for lock contention between threads"""
    print("\n" + "="*80)
    print("SCENARIO 3: Lock Contention Test")
    print("="*80)
    print("Monitoring lock acquisition times...")
    print()

    settings_manager = SettingsManager()
    audio_manager = AudioManager(settings_manager)

    devices = audio_manager.get_input_devices()
    if len(devices) == 0:
        print("❌ No devices available")
        return

    # Select multiple devices to increase contention
    num_devices = min(2, len(devices))
    for i in range(num_devices):
        audio_manager.set_device_selected(devices[i].id, True)

    time.sleep(2.0)

    # Try to acquire lock multiple times and measure
    lock_times = []
    for i in range(10):
        start = time.time()
        with audio_manager._lock:
            pass  # Just acquire and release
        elapsed = time.time() - start
        lock_times.append(elapsed)
        print(f"  Lock acquisition {i+1}: {elapsed*1000:.2f}ms")
        time.sleep(0.1)

    avg_lock_time = sum(lock_times) / len(lock_times)
    max_lock_time = max(lock_times)

    print(f"\nAverage lock time: {avg_lock_time*1000:.2f}ms")
    print(f"Max lock time: {max_lock_time*1000:.2f}ms")

    if max_lock_time > 0.1:  # 100ms
        print("⚠️ Significant lock contention detected")
    else:
        print("✅ Lock contention appears minimal")

    # Cleanup
    for i in range(num_devices):
        audio_manager.set_device_selected(devices[i].id, False)
    audio_manager.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Diagnose audio thread issues")
    parser.add_argument("--scenario", choices=["all", "monitor", "queue", "callback", "lock"],
                       default="all", help="Which scenario to run")
    parser.add_argument("--duration", type=int, default=60,
                       help="Monitoring duration in seconds (for monitor scenario)")

    args = parser.parse_args()

    if args.scenario == "all" or args.scenario == "monitor":
        run_diagnostics(args.duration)

    if args.scenario == "all" or args.scenario == "queue":
        test_scenario_queue_starvation()

    if args.scenario == "all" or args.scenario == "callback":
        test_scenario_callback_failure()

    if args.scenario == "all" or args.scenario == "lock":
        test_scenario_lock_contention()
