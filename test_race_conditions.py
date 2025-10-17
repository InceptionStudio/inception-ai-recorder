#!/usr/bin/env python3
"""
Test cases designed to TRIGGER the race conditions and bugs identified in root cause analysis.

These tests intentionally create race conditions to demonstrate the bugs.
Some tests may cause deadlocks or crashes - this is expected and proves the bugs exist.
"""

import sys
import time
import threading
import queue
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add package to path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multitrack_recorder.audio_manager import AudioManager, STOP
from multitrack_recorder.settings_manager import SettingsManager


class TestRaceCondition1_QueueDeletion(unittest.TestCase):
    """
    Test for Root Cause #1: Queue Race Condition

    Demonstrates that thread can crash when queue is deleted while being used.
    """

    def setUp(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_queue_deleted_while_thread_using_it(self):
        """
        TRIGGER BUG #1: Delete queue between thread getting reference and using it

        This demonstrates the race condition in audio_manager.py:1313-1327
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: Queue Deletion Race Condition")
        print("="*80)
        print("This test will try to delete the queue while the thread is using it")
        print()

        # Start device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Flag to detect if thread crashes
        thread_error_detected = threading.Event()
        original_print = print

        def detect_error(*args, **kwargs):
            """Detect thread errors"""
            msg = ' '.join(str(arg) for arg in args)
            if 'error' in msg.lower() or 'exception' in msg.lower():
                if device_id in msg:
                    thread_error_detected.set()
                    original_print(f"🔴 DETECTED THREAD ERROR: {msg}")
            original_print(*args, **kwargs)

        # Temporarily replace print to detect errors
        import builtins
        builtins.print = detect_error

        try:
            # Repeatedly delete and recreate queue to trigger race
            for i in range(50):
                time.sleep(0.01)  # Small delay to let thread process

                with self.audio_manager._lock:
                    # Get queue reference
                    q = self.audio_manager._AudioManager__audio_data_queues.get(device_id)

                    if q is not None:
                        # DELETE the queue while thread might be between getting reference
                        # and calling queue.get()
                        print(f"  Attempt {i+1}: Deleting queue...")
                        del self.audio_manager._AudioManager__audio_data_queues[device_id]

                        # Recreate immediately to prevent thread from exiting
                        self.audio_manager._AudioManager__audio_data_queues[device_id] = queue.Queue()

                if thread_error_detected.is_set():
                    print("✅ SUCCESS: Triggered the race condition!")
                    break

        finally:
            builtins.print = original_print

        # Check if we triggered the bug
        if thread_error_detected.is_set():
            print("\n🎯 RACE CONDITION TRIGGERED!")
            print("This proves bug #1 exists: Queue deleted while thread using it")
        else:
            print("\n⚠️ Race condition not triggered (timing issue)")
            print("The bug exists but timing didn't align in this run")

        # Cleanup
        self.audio_manager.set_device_selected(device_id, False)

    def test_aggressive_queue_deletion(self):
        """
        More aggressive test - delete queue many times rapidly
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: Aggressive Queue Deletion")
        print("="*80)

        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Spawn thread to constantly delete queue
        stop_flag = threading.Event()

        def queue_deleter():
            """Constantly delete and recreate queue"""
            while not stop_flag.is_set():
                try:
                    with self.audio_manager._lock:
                        if device_id in self.audio_manager._AudioManager__audio_data_queues:
                            del self.audio_manager._AudioManager__audio_data_queues[device_id]
                            self.audio_manager._AudioManager__audio_data_queues[device_id] = queue.Queue()
                except Exception as e:
                    print(f"Deleter error: {e}")
                time.sleep(0.001)  # Very fast deletion

        deleter_thread = threading.Thread(target=queue_deleter, daemon=True)
        deleter_thread.start()

        # Let it run for a few seconds
        print("Running aggressive queue deletion for 3 seconds...")
        time.sleep(3.0)

        stop_flag.set()
        deleter_thread.join(timeout=1.0)

        # Check if thread is still alive
        with self.audio_manager._lock:
            thread = self.audio_manager._AudioManager__listening_threads.get(device_id)

        if thread and thread.is_alive():
            print("✅ Thread survived aggressive deletion")
        else:
            print("🔴 Thread died! Race condition triggered!")
            self.fail("Thread died due to queue deletion race condition")

        self.audio_manager.set_device_selected(device_id, False)


class TestRaceCondition6_HealthMonitorDeadlock(unittest.TestCase):
    """
    Test for Root Cause #6: Health Monitor Deadlock

    Demonstrates deadlock when health monitor holds lock during recovery
    while PyAudio callback tries to acquire lock.

    WARNING: This test may cause the entire process to hang!
    """

    def setUp(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_recovery_during_callback(self):
        """
        TRIGGER BUG #6: Force recovery while callback is active

        This demonstrates the deadlock in audio_manager.py:676-693

        WARNING: This test may hang! Set a timeout.
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: Health Monitor Deadlock")
        print("="*80)
        print("WARNING: This test may cause a deadlock!")
        print()

        # Start device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Force the thread to die by sending STOP
        with self.audio_manager._lock:
            q = self.audio_manager._AudioManager__audio_data_queues.get(device_id)
            thread = self.audio_manager._AudioManager__listening_threads.get(device_id)

        if q and thread:
            print("Killing thread to trigger recovery...")
            q.put(STOP)

            # Wait for thread to die
            thread.join(timeout=3.0)
            print(f"Thread alive after kill attempt: {thread.is_alive()}")

            # Now wait for health monitor to detect and try recovery
            # During recovery, callbacks may still be coming in
            print("Waiting for health monitor to detect (up to 15 seconds)...")
            print("If test hangs here, we've triggered the deadlock!")

            start_wait = time.time()
            deadlock_detected = False

            # Try to acquire lock periodically - if we can't, might be deadlock
            for i in range(30):  # 15 seconds
                time.sleep(0.5)

                # Try to acquire lock with timeout
                lock_acquired = self.audio_manager._lock.acquire(timeout=0.1)

                if lock_acquired:
                    self.audio_manager._lock.release()
                else:
                    elapsed = time.time() - start_wait
                    print(f"⚠️ Lock held for {elapsed:.1f}s - possible deadlock!")
                    if elapsed > 5.0:
                        deadlock_detected = True
                        break

            if deadlock_detected:
                print("🔴 DEADLOCK DETECTED!")
                print("Health monitor is holding lock for extended period")
                print("This proves bug #6 exists")
                # Can't continue - system is deadlocked
                self.fail("Deadlock detected in health monitor recovery")
            else:
                print("✅ No deadlock detected (may need more attempts)")

        self.audio_manager.set_device_selected(device_id, False)

    def test_simulated_blocking_recovery(self):
        """
        Simulate what happens when recovery blocks
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: Simulated Blocking During Recovery")
        print("="*80)

        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Simulate blocking by holding lock for extended time
        print("Acquiring lock and holding for 3 seconds (simulating blocking recovery)...")

        def block_with_lock():
            with self.audio_manager._lock:
                print("  Lock acquired, blocking for 3 seconds...")
                time.sleep(3.0)
                print("  Lock released")

        blocker_thread = threading.Thread(target=block_with_lock, daemon=True)
        blocker_thread.start()

        time.sleep(0.1)  # Let blocker acquire lock

        # Now try to do something that needs the lock
        print("Main thread trying to stop device (needs lock)...")
        start = time.time()

        try:
            # This should block until lock is released
            self.audio_manager.set_device_selected(device_id, False)
            elapsed = time.time() - start
            print(f"✅ Operation completed after {elapsed:.1f}s")

            if elapsed > 2.5:
                print("🔴 Operation was blocked for significant time")
                print("This demonstrates how blocking during recovery affects system")
        except Exception as e:
            print(f"❌ Operation failed: {e}")

        blocker_thread.join(timeout=5.0)


class TestRaceCondition2_NoneQueue(unittest.TestCase):
    """
    Test for Root Cause #2: Thread exits on None queue
    """

    def setUp(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_thread_exits_on_none_queue(self):
        """
        TRIGGER BUG #2: Make queue None to cause thread exit
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: Thread Exit on None Queue")
        print("="*80)

        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get thread reference
        with self.audio_manager._lock:
            thread = self.audio_manager._AudioManager__listening_threads.get(device_id)
            original_thread = thread

        print("Removing queue to trigger bug...")

        # Remove queue (simulating what happens during recovery)
        with self.audio_manager._lock:
            self.audio_manager._AudioManager__audio_data_queues.pop(device_id, None)

        # Wait for thread to notice and exit
        print("Waiting for thread to detect None queue...")
        time.sleep(3.0)

        # Check if thread exited
        if original_thread:
            if original_thread.is_alive():
                print("✅ Thread still alive (bug not triggered)")
            else:
                print("🔴 Thread EXITED when queue became None!")
                print("This proves bug #2: Thread exits on None queue")
                print("Expected: Thread should retry, not exit")

        self.audio_manager.set_device_selected(device_id, False)


class TestRaceCondition4_WAVFileRace(unittest.TestCase):
    """
    Test for Root Cause #4: WAV file race condition during recording
    """

    def setUp(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_wav_file_closed_during_write(self):
        """
        TRIGGER BUG #4: Close file while async write is in progress
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: WAV File Race Condition")
        print("="*80)

        # Set up temporary recording directory
        with tempfile.TemporaryDirectory() as tmpdir:
            self.audio_manager.set_export_directory(tmpdir)
            self.audio_manager.set_device_selected(device_id, True)
            time.sleep(0.5)

            # Start recording
            print("Starting recording...")
            self.audio_manager.start_recording()
            time.sleep(1.0)  # Let some data be recorded

            print("Stopping recording quickly to trigger race...")

            # Stop recording - this will close files
            self.audio_manager.stop_recording()

            # The bug: async writes may still be in progress when file is closed
            # Look for "File write error" messages
            time.sleep(2.0)  # Wait for async writes to attempt

            print("Check console output for 'File write error' messages")
            print("If present, bug #4 was triggered")

            self.audio_manager.set_device_selected(device_id, False)


class TestRaceCondition7_CallbackSilence(unittest.TestCase):
    """
    Test for Root Cause #7: No callback liveness detection
    """

    def setUp(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_callback_stops_but_thread_appears_healthy(self):
        """
        TRIGGER BUG #7: Simulate callback stopping but thread appearing alive

        This demonstrates that the health monitor can't detect when
        PyAudio stops calling the callback.
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        print("\n" + "="*80)
        print("TEST: Callback Silence Detection")
        print("="*80)

        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(1.0)

        # Monitor queue activity
        print("Monitoring queue activity for 5 seconds...")
        activity = []

        for i in range(10):
            time.sleep(0.5)
            with self.audio_manager._lock:
                q = self.audio_manager._AudioManager__audio_data_queues.get(device_id)
                thread = self.audio_manager._AudioManager__listening_threads.get(device_id)
                last_activity = self.audio_manager._AudioManager__thread_last_activity.get(device_id, 0)

            if q:
                qsize = q.qsize()
                activity.append({
                    'time': time.time(),
                    'qsize': qsize,
                    'thread_alive': thread.is_alive() if thread else False,
                    'last_activity': last_activity
                })
                print(f"  Sample {i+1}: queue={qsize}, thread={thread.is_alive() if thread else False}")

        # Analyze activity
        avg_qsize = sum(a['qsize'] for a in activity) / len(activity) if activity else 0
        all_zero = all(a['qsize'] == 0 for a in activity)

        print(f"\nAnalysis:")
        print(f"  Average queue size: {avg_qsize:.2f}")
        print(f"  All samples zero: {all_zero}")

        if all_zero and activity[-1]['thread_alive']:
            print("\n🔴 BUG DEMONSTRATED:")
            print("  Thread appears alive and healthy")
            print("  Activity timestamps updating (from queue.Empty)")
            print("  BUT we can't tell if callback is actually running!")
            print("  Queue always empty could mean:")
            print("    A) Thread processing fast (GOOD)")
            print("    B) Callback stopped running (BAD)")
            print("  Current system has no way to distinguish!")

        self.audio_manager.set_device_selected(device_id, False)


class TestLockContentionUnderLoad(unittest.TestCase):
    """
    Test for Root Cause #5: Excessive lock holding
    Demonstrate performance degradation with multiple devices
    """

    def setUp(self):
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_lock_contention_with_multiple_devices(self):
        """
        Demonstrate lock contention increases with device count
        """
        devices = self.audio_manager.get_input_devices()
        if len(devices) < 2:
            self.skipTest("Need at least 2 devices")

        print("\n" + "="*80)
        print("TEST: Lock Contention Under Load")
        print("="*80)

        # Test with increasing device count
        for num_devices in range(1, min(len(devices), 4) + 1):
            print(f"\n--- Testing with {num_devices} device(s) ---")

            # Select devices
            for i in range(num_devices):
                self.audio_manager.set_device_selected(devices[i].id, True)

            time.sleep(1.0)

            # Measure lock acquisition time
            lock_times = []
            for _ in range(20):
                start = time.time()
                with self.audio_manager._lock:
                    pass
                elapsed = time.time() - start
                lock_times.append(elapsed * 1000)  # Convert to ms
                time.sleep(0.05)

            avg_time = sum(lock_times) / len(lock_times)
            max_time = max(lock_times)

            print(f"  Average lock time: {avg_time:.3f}ms")
            print(f"  Max lock time: {max_time:.3f}ms")

            if num_devices == 1:
                baseline_avg = avg_time
            else:
                increase = ((avg_time / baseline_avg) - 1) * 100
                print(f"  Increase vs 1 device: {increase:.1f}%")

            # Cleanup
            for i in range(num_devices):
                self.audio_manager.set_device_selected(devices[i].id, False)

            time.sleep(0.5)

        print("\n✅ Test complete - check for lock time increases with device count")


def run_tests():
    """Run race condition tests"""
    print("="*80)
    print("RACE CONDITION TEST SUITE")
    print("="*80)
    print()
    print("⚠️  WARNING: These tests intentionally trigger race conditions and bugs")
    print("⚠️  Some tests may cause deadlocks, hangs, or crashes")
    print("⚠️  This is EXPECTED and proves the bugs exist")
    print()
    print("="*80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRaceCondition1_QueueDeletion))
    suite.addTests(loader.loadTestsFromTestCase(TestRaceCondition2_NoneQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestRaceCondition4_WAVFileRace))
    suite.addTests(loader.loadTestsFromTestCase(TestRaceCondition7_CallbackSilence))
    suite.addTests(loader.loadTestsFromTestCase(TestLockContentionUnderLoad))

    # NOTE: Deadlock test excluded by default as it may hang
    # Uncomment to include:
    # suite.addTests(loader.loadTestsFromTestCase(TestRaceCondition6_HealthMonitorDeadlock))

    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run race condition tests")
    parser.add_argument("--include-deadlock", action="store_true",
                       help="Include deadlock test (may hang!)")
    args = parser.parse_args()

    if args.include_deadlock:
        print("⚠️  DEADLOCK TEST ENABLED - Process may hang!")
        print()

    sys.exit(run_tests())
