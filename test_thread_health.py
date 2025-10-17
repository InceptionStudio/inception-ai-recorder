#!/usr/bin/env python3
"""
Test cases for thread health monitoring and recovery.

These tests verify that the audio processing threads:
1. Start correctly when devices are selected
2. Continue running during normal operation
3. Are detected when they die unexpectedly
4. Are automatically recovered by the health monitor
5. Handle edge cases like rapid device selection/deselection
"""

import sys
import time
import threading
import unittest
from unittest.mock import Mock, patch, MagicMock
import queue
import numpy as np

# Add package to path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multitrack_recorder.audio_manager import AudioManager, STOP
from multitrack_recorder.settings_manager import SettingsManager


class TestThreadHealth(unittest.TestCase):
    """Test thread health monitoring and recovery"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        """Clean up after tests"""
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_thread_starts_when_device_selected(self):
        """Test that a thread is created when a device is selected"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select the device
        self.audio_manager.set_device_selected(device_id, True)

        # Give it a moment to start
        time.sleep(0.5)

        # Verify thread exists and is alive
        with self.audio_manager._lock:
            self.assertIn(device_id, self.audio_manager._AudioManager__listening_threads)
            thread = self.audio_manager._AudioManager__listening_threads[device_id]
            self.assertTrue(thread.is_alive(), "Thread should be alive after device selection")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_thread_stops_when_device_deselected(self):
        """Test that a thread stops when a device is deselected"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select the device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get thread reference
        with self.audio_manager._lock:
            thread = self.audio_manager._AudioManager__listening_threads.get(device_id)

        self.assertIsNotNone(thread, "Thread should exist when device is selected")

        # Deselect the device
        self.audio_manager.set_device_selected(device_id, False)

        # Wait for thread to stop (with timeout)
        thread.join(timeout=5.0)

        # Verify thread is no longer alive
        self.assertFalse(thread.is_alive(), "Thread should stop after device deselection")

        # Verify thread is removed from tracking
        with self.audio_manager._lock:
            self.assertNotIn(device_id, self.audio_manager._AudioManager__listening_threads)

    def test_thread_processes_audio_data(self):
        """Test that thread processes audio data and updates activity timestamp"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select the device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get initial activity timestamp
        with self.audio_manager._lock:
            initial_time = self.audio_manager._AudioManager__thread_last_activity.get(device_id, 0)

        # Wait for some audio processing
        time.sleep(2.0)

        # Get updated activity timestamp
        with self.audio_manager._lock:
            updated_time = self.audio_manager._AudioManager__thread_last_activity.get(device_id, 0)

        # Verify timestamp was updated (thread is processing data)
        self.assertGreater(updated_time, initial_time,
                          "Activity timestamp should be updated as thread processes audio")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_health_monitor_detects_dead_thread(self):
        """Test that health monitor detects when a thread dies"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select the device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get thread reference
        with self.audio_manager._lock:
            thread = self.audio_manager._AudioManager__listening_threads[device_id]
            audio_queue = self.audio_manager._AudioManager__audio_data_queues[device_id]

        self.assertTrue(thread.is_alive(), "Thread should be alive initially")

        # Force thread to exit by sending STOP signal
        audio_queue.put(STOP)

        # Wait for thread to die
        thread.join(timeout=5.0)
        self.assertFalse(thread.is_alive(), "Thread should be dead after STOP signal")

        # Wait for health monitor to detect and recover (runs every 5 seconds)
        # Give it up to 10 seconds to detect and recover
        recovered = False
        for _ in range(20):  # Check 20 times over 10 seconds
            time.sleep(0.5)
            with self.audio_manager._lock:
                new_thread = self.audio_manager._AudioManager__listening_threads.get(device_id)
                if new_thread and new_thread != thread and new_thread.is_alive():
                    recovered = True
                    break

        self.assertTrue(recovered, "Health monitor should detect dead thread and recover it")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_multiple_devices_have_separate_threads(self):
        """Test that multiple selected devices each have their own thread"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) < 2:
            self.skipTest("Need at least 2 audio devices")

        device_ids = [devices[0].id, devices[1].id]

        # Select both devices
        for device_id in device_ids:
            self.audio_manager.set_device_selected(device_id, True)

        time.sleep(0.5)

        # Verify each has a separate thread
        with self.audio_manager._lock:
            threads = {}
            for device_id in device_ids:
                self.assertIn(device_id, self.audio_manager._AudioManager__listening_threads)
                thread = self.audio_manager._AudioManager__listening_threads[device_id]
                self.assertTrue(thread.is_alive())
                threads[device_id] = thread

        # Verify threads are different objects
        self.assertNotEqual(threads[device_ids[0]], threads[device_ids[1]],
                           "Each device should have its own thread")

        # Clean up
        for device_id in device_ids:
            self.audio_manager.set_device_selected(device_id, False)

    def test_rapid_device_selection_deselection(self):
        """Test that rapid device selection/deselection doesn't cause thread issues"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Rapidly select and deselect the device
        for _ in range(5):
            self.audio_manager.set_device_selected(device_id, True)
            time.sleep(0.1)
            self.audio_manager.set_device_selected(device_id, False)
            time.sleep(0.1)

        # Final selection
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Verify thread is alive and healthy
        with self.audio_manager._lock:
            thread = self.audio_manager._AudioManager__listening_threads.get(device_id)

        self.assertIsNotNone(thread, "Thread should exist after rapid selection/deselection")
        self.assertTrue(thread.is_alive(), "Thread should be alive after rapid selection/deselection")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_thread_continues_during_recording(self):
        """Test that thread continues processing during recording"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Set export directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            self.audio_manager.set_export_directory(tmpdir)

            # Select device
            self.audio_manager.set_device_selected(device_id, True)
            time.sleep(0.5)

            # Get thread reference
            with self.audio_manager._lock:
                thread = self.audio_manager._AudioManager__listening_threads[device_id]

            # Start recording
            self.audio_manager.start_recording()

            # Wait a bit
            time.sleep(2.0)

            # Verify thread is still alive during recording
            self.assertTrue(thread.is_alive(), "Thread should remain alive during recording")

            # Verify activity is being tracked
            with self.audio_manager._lock:
                activity_time = self.audio_manager._AudioManager__thread_last_activity.get(device_id, 0)

            self.assertGreater(activity_time, 0, "Thread should be tracking activity during recording")

            # Stop recording
            self.audio_manager.stop_recording()

            # Thread should still be alive after recording stops
            time.sleep(0.5)
            self.assertTrue(thread.is_alive(), "Thread should remain alive after recording stops")

            # Clean up
            self.audio_manager.set_device_selected(device_id, False)

    def test_health_monitor_running(self):
        """Test that health monitor thread is running"""
        # Give health monitor a moment to start
        time.sleep(0.5)

        # Check for health monitor thread
        health_monitor_found = False
        for thread in threading.enumerate():
            if "HealthMonitor" in thread.name:
                health_monitor_found = True
                self.assertTrue(thread.is_alive(), "Health monitor should be alive")
                self.assertTrue(thread.daemon, "Health monitor should be a daemon thread")
                break

        self.assertTrue(health_monitor_found, "Health monitor thread should exist")

    def test_thread_has_correct_name(self):
        """Test that threads are created with correct naming convention"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get thread
        with self.audio_manager._lock:
            thread = self.audio_manager._AudioManager__listening_threads[device_id]

        # Verify thread name follows convention
        expected_name = f"AudioListener-{device_id}"
        self.assertEqual(thread.name, expected_name,
                        f"Thread name should be '{expected_name}'")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_activity_timestamp_updates_regularly(self):
        """Test that activity timestamp updates regularly during normal operation"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Collect activity timestamps over 5 seconds
        timestamps = []
        for _ in range(5):
            with self.audio_manager._lock:
                timestamp = self.audio_manager._AudioManager__thread_last_activity.get(device_id, 0)
            timestamps.append(timestamp)
            time.sleep(1.0)

        # Verify timestamps are increasing (thread is active)
        for i in range(1, len(timestamps)):
            self.assertGreaterEqual(timestamps[i], timestamps[i-1],
                                   "Activity timestamp should be non-decreasing")

        # Verify we have multiple distinct timestamps (not stuck)
        unique_timestamps = len(set(timestamps))
        self.assertGreater(unique_timestamps, 1,
                          "Activity timestamp should update over time")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)


class TestThreadRecovery(unittest.TestCase):
    """Test thread recovery scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        """Clean up after tests"""
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_recovery_after_thread_crash(self):
        """Test recovery when thread crashes with an exception"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select device to start thread
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get original thread
        with self.audio_manager._lock:
            original_thread = self.audio_manager._AudioManager__listening_threads[device_id]

        # Force thread to exit
        with self.audio_manager._lock:
            audio_queue = self.audio_manager._AudioManager__audio_data_queues[device_id]
        audio_queue.put(STOP)

        # Wait for original thread to die
        original_thread.join(timeout=5.0)

        # Wait for health monitor to recover (up to 15 seconds)
        recovered = False
        new_thread = None
        for _ in range(30):  # 15 seconds
            time.sleep(0.5)
            with self.audio_manager._lock:
                new_thread = self.audio_manager._AudioManager__listening_threads.get(device_id)
                if new_thread and new_thread != original_thread and new_thread.is_alive():
                    recovered = True
                    break

        # Verify recovery happened
        self.assertTrue(recovered, "Thread should be recovered after crash")
        self.assertIsNotNone(new_thread)
        self.assertNotEqual(new_thread, original_thread, "Should be a new thread")
        self.assertTrue(new_thread.is_alive(), "Recovered thread should be alive")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_stream_restart_after_recovery(self):
        """Test that audio stream is restarted after thread recovery"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Force thread to exit
        with self.audio_manager._lock:
            audio_queue = self.audio_manager._AudioManager__audio_data_queues[device_id]
            original_thread = self.audio_manager._AudioManager__listening_threads[device_id]
        audio_queue.put(STOP)
        original_thread.join(timeout=5.0)

        # Wait for recovery (up to 15 seconds)
        time.sleep(15.0)

        # Verify stream exists and is active
        with self.audio_manager._lock:
            stream = self.audio_manager._AudioManager__listening_streams.get(device_id)
            new_thread = self.audio_manager._AudioManager__listening_threads.get(device_id)

        self.assertIsNotNone(stream, "Stream should exist after recovery")
        self.assertIsNotNone(new_thread, "Thread should exist after recovery")

        if stream:
            self.assertTrue(stream.is_active(), "Stream should be active after recovery")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)

    def test_queue_recreated_after_recovery(self):
        """Test that audio queue is recreated after thread recovery"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Select device
        self.audio_manager.set_device_selected(device_id, True)
        time.sleep(0.5)

        # Get original queue
        with self.audio_manager._lock:
            original_queue = self.audio_manager._AudioManager__audio_data_queues[device_id]
            original_thread = self.audio_manager._AudioManager__listening_threads[device_id]

        # Force thread to exit
        original_queue.put(STOP)
        original_thread.join(timeout=5.0)

        # Wait for recovery
        time.sleep(15.0)

        # Verify new queue exists
        with self.audio_manager._lock:
            new_queue = self.audio_manager._AudioManager__audio_data_queues.get(device_id)

        self.assertIsNotNone(new_queue, "Queue should exist after recovery")
        self.assertIsInstance(new_queue, queue.Queue, "Should be a valid queue")

        # Clean up
        self.audio_manager.set_device_selected(device_id, False)


class TestThreadEdgeCases(unittest.TestCase):
    """Test edge cases and race conditions"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)

    def tearDown(self):
        """Clean up after tests"""
        try:
            self.audio_manager.cleanup()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def test_device_refresh_stops_all_threads(self):
        """Test that device refresh properly stops all threads"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        # Select all available devices (up to 3)
        device_ids = [d.id for d in devices[:3]]
        threads = {}

        for device_id in device_ids:
            self.audio_manager.set_device_selected(device_id, True)

        time.sleep(0.5)

        # Get thread references
        with self.audio_manager._lock:
            for device_id in device_ids:
                threads[device_id] = self.audio_manager._AudioManager__listening_threads[device_id]

        # Refresh devices
        self.audio_manager.refresh_devices()

        # Wait for cleanup
        time.sleep(1.0)

        # Verify all old threads are stopped
        for device_id, thread in threads.items():
            self.assertFalse(thread.is_alive(),
                           f"Thread for device {device_id} should stop after refresh")

    def test_cleanup_stops_all_threads(self):
        """Test that cleanup properly stops all threads"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        # Select devices
        device_ids = [d.id for d in devices[:2]]
        threads = []

        for device_id in device_ids:
            self.audio_manager.set_device_selected(device_id, True)

        time.sleep(0.5)

        # Get thread references
        with self.audio_manager._lock:
            for device_id in device_ids:
                thread = self.audio_manager._AudioManager__listening_threads.get(device_id)
                if thread:
                    threads.append(thread)

        # Cleanup
        self.audio_manager.cleanup()

        # Wait for threads to stop
        time.sleep(2.0)

        # Verify all threads stopped
        for thread in threads:
            self.assertFalse(thread.is_alive(), "All threads should stop after cleanup")

    def test_no_thread_leak_with_repeated_selection(self):
        """Test that repeatedly selecting/deselecting doesn't leak threads"""
        devices = self.audio_manager.get_input_devices()
        if len(devices) == 0:
            self.skipTest("No audio devices available")

        device_id = devices[0].id

        # Get initial thread count
        initial_thread_count = threading.active_count()

        # Repeatedly select and deselect
        for _ in range(10):
            self.audio_manager.set_device_selected(device_id, True)
            time.sleep(0.2)
            self.audio_manager.set_device_selected(device_id, False)
            time.sleep(0.2)

        # Wait for all threads to clean up
        time.sleep(2.0)

        # Get final thread count
        final_thread_count = threading.active_count()

        # Allow for some variance (health monitor, etc.) but shouldn't leak 10+ threads
        thread_difference = final_thread_count - initial_thread_count
        self.assertLess(thread_difference, 5,
                       f"Should not leak threads (difference: {thread_difference})")


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestThreadHealth))
    suite.addTests(loader.loadTestsFromTestCase(TestThreadRecovery))
    suite.addTests(loader.loadTestsFromTestCase(TestThreadEdgeCases))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
