#!/usr/bin/env python3
"""
Multitrack Audio Recorder - Main Entry Point

A Python port of the Swift multitrack-recorder application.
Records from multiple audio input devices simultaneously with real-time visualization.
"""

import sys
import os

# Add the package directory to Python path
package_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(package_dir))

def main():
    """Main entry point for the application"""
    try:
        from multitrack_recorder.gui import MultitrackRecorderGUI
        
        # Create and run the GUI application
        app = MultitrackRecorderGUI()
        app.run()
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all dependencies are installed:")
        print("pip install PyAudio numpy matplotlib")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()