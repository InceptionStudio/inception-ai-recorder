# Multitrack Audio Recorder (Python)

A Python port of the [multitrack-recorder-swift](https://github.com/joewhaley/multitrack-recorder-swift) application. This professional multitrack audio recording application uses PortAudio (via PyAudio) to record from multiple audio input devices simultaneously with real-time waveform visualization and individual device control.

## Features

### 🎙️ Multi-Device Recording
- **Simultaneous Recording**: Record from multiple audio input devices at the same time
- **Device Management**: Easy device selection with checkboxes for each available input
- **Real-time Monitoring**: Live audio level meters and waveform visualization for each device
- **Device Refresh**: Dynamically refresh the input device list without restarting the app

### 🎵 Audio Features
- **High-Quality Recording**: 48kHz sample rate with 32-bit float precision
- **Multiple Output Formats**: WAV (uncompressed), MP3 (compressed), or Opus (highly compressed)
- **Streaming Recording**: Real-time audio streaming to disk for efficient memory usage
- **Individual Device Control**: Start/stop recording for each device independently
- **Gain Control**: Individual gain adjustment (-24dB to +24dB) for each device
- **Auto Gain**: Intelligent automatic gain adjustment based on peak levels
- **Peak Monitoring**: Real-time peak level tracking and clipping detection

### 🎨 User Interface
- **Cross-Platform GUI**: Built with tkinter for compatibility across operating systems
- **Real-time Waveforms**: Visual representation of audio input for each device using matplotlib
- **Audio Level Meters**: Live monitoring of input levels with color-coded indicators
- **Device Labeling**: Add custom labels to identify your audio devices
- **Responsive Design**: Scrollable interface that works with any number of devices
- **Custom Icon**: Professional microphone icon in dock/taskbar
- **Configuration Dialog**: Easy access to export settings and Google Drive configuration
- **Session Management**: Optional session titles for organized recording sessions

### 🔧 Technical Features
- **Thread-Safe Audio Processing**: Robust audio callback handling with proper thread management
- **Memory Efficient**: Streaming audio data directly to disk without excessive memory usage
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Persistent Settings**: Automatic saving of device labels, gains, and preferences
- **Google Drive Integration**: Automatic upload of recordings to Google Drive
- **Settings Management**: Comprehensive settings system with auto-save functionality

### ☁️ Cloud Integration
- **Google Drive Upload**: Automatic upload of recordings to Google Drive folders
- **Multiple Output Formats**: Choose between WAV, MP3, or Opus for cloud uploads
- **OAuth2 Authentication**: Secure Google Drive authentication with token management
- **Folder Validation**: Verify Google Drive folder access before recording
- **Shared Drive Support**: Works with both personal and Google Shared Drives

## Requirements

- **Python**: 3.8 or later
- **PortAudio**: Audio I/O library (required by PyAudio)
- **Audio Devices**: Any audio input device compatible with your operating system

### Python Dependencies
- PyAudio (0.2.14+)
- numpy (1.21.0+)
- matplotlib (3.5.0+)
- google-api-python-client (2.0.0+) - For Google Drive integration
- google-auth-httplib2 (0.1.0+) - For Google authentication
- google-auth-oauthlib (0.5.0+) - For OAuth2 authentication
- platformdirs (3.0.0+) - For cross-platform directory handling
- tkinter (included with Python)

## Installation

### Step 1: Install PortAudio

#### macOS (using Homebrew)
```bash
brew install portaudio
brew install python-tk  # Required for tkinter GUI
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
```

#### Windows
Download and install the PortAudio binaries, or use conda:
```bash
conda install portaudio
```

### Step 2: Clone and Install

```bash
git clone <repository-url>
cd inception-ai-recorder

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
# Note: On macOS with Apple Silicon, you may need special PyAudio installation:
pip install --global-option='build_ext' --global-option='-I/opt/homebrew/include' --global-option='-L/opt/homebrew/lib' pyaudio
pip install -r requirements.txt
```

### Step 3: Install the Package (Optional)

```bash
pip install -e .
```

## Usage

### Running the Application

#### Method 1: Direct execution
```bash
python multitrack_recorder/main.py
```

#### Method 2: As installed package (if installed with pip)
```bash
multitrack-recorder
```

#### Method 3: As module
```bash
python -m multitrack_recorder.main
```

### Getting Started

1. **Launch the Application**: Run the application using one of the methods above
2. **Configure Settings**: Click "Configuration" to set up export directory and Google Drive (optional)
3. **Select Export Directory**: Choose where recordings will be saved locally
4. **Enable Devices**: Check the boxes next to the audio devices you want to record from
5. **Add Labels** (Optional): Add custom labels to identify your devices
6. **Adjust Gain** (Optional): Use the gain sliders or "Auto" button to optimize audio levels
7. **Set Session Title** (Optional): Add a title for organized recording sessions
8. **Monitor Audio**: Watch the real-time waveforms and level meters for each device
9. **Start Recording**: Click "Start Recording" to begin capturing audio from all selected devices
10. **Stop Recording**: Click "Stop Recording" to finalize your files (automatically uploaded to Google Drive if configured)

### Device Management

- **Refresh Devices**: Click "Refresh" to update the list of available audio devices (detects newly connected/disconnected devices)
- **Add Labels**: Enter custom names in the label field next to each device
- **Gain Control**: Adjust individual gain levels (-24dB to +24dB) for each device
- **Auto Gain**: Click "Auto" to automatically calculate optimal gain based on peak levels
- **Individual Control**: Each device can be enabled/disabled independently
- **Real-time Monitoring**: Audio levels and waveforms update in real-time
- **Peak Tracking**: Monitor peak levels and clipping detection for each device
- **Hot-plugging**: Use refresh to detect USB audio devices that are connected after startup

### Recording Features

- **Simultaneous Recording**: All selected devices record simultaneously
- **Individual Files**: Each device creates its own audio file
- **Multiple Formats**: Choose between WAV, MP3, or Opus output formats
- **File Naming**: Files are automatically named with device labels and timestamps
- **Session Organization**: Optional session titles create organized folder structures
- **Streaming**: Audio is written to disk in real-time for efficient memory usage
- **Google Drive Upload**: Automatic cloud backup of recordings (optional)

## File Structure

```
multitrack_recorder/
├── __init__.py                 # Package initialization
├── main.py                     # Main entry point
├── audio_manager.py            # Core audio management and PyAudio integration
├── gui.py                      # GUI components and layout
└── settings_manager.py         # Settings management and persistence

# Additional files
├── app_icon.png                # Custom application icon
├── app_icon.ico                # Windows icon format
├── settings.json               # User settings and preferences
├── credentials.json            # Google Drive OAuth2 credentials (user-provided)
├── token.pickle                # Google Drive authentication token
├── requirements.txt            # Python dependencies
├── setup.py                    # Package installation script
└── GOOGLE_DRIVE_SETUP.md       # Google Drive setup guide
```

## Technical Details

### Architecture

- **tkinter**: Cross-platform GUI framework
- **PyAudio**: Python bindings for PortAudio for low-latency audio processing
- **matplotlib**: Real-time waveform visualization
- **Threading**: Background processing for audio and file I/O operations

### Audio Processing

- **Sample Rate**: 48kHz
- **Bit Depth**: 32-bit float (internal), 32-bit PCM (WAV output)
- **Channels**: Mono (1 channel per device)
- **Buffer Size**: 1024 frames
- **Formats**: WAV (RIFF PCM), MP3 (compressed), Opus (highly compressed)
- **Gain Range**: -24dB to +24dB per device
- **Peak Monitoring**: Real-time clipping detection and level tracking

### Thread Safety

- **Audio Callbacks**: Run on high-priority audio threads
- **UI Updates**: Scheduled on main thread for thread safety
- **File I/O**: Background thread processing to prevent audio dropouts
- **Queue-based Communication**: Thread-safe data passing between audio and recording threads

## Google Drive Setup

For automatic cloud backup of your recordings, you can configure Google Drive integration:

1. **Follow the Setup Guide**: See [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md) for detailed instructions
2. **Get Credentials**: Download OAuth2 credentials from Google Cloud Console
3. **Configure in App**: Use the Configuration dialog to set up Google Drive folder
4. **Choose Format**: Select output format (WAV, MP3, or Opus) for cloud uploads
5. **Automatic Upload**: Recordings are automatically uploaded after each session

### Google Drive Features
- **OAuth2 Authentication**: Secure, token-based authentication
- **Folder Validation**: Verify folder access before recording
- **Shared Drive Support**: Works with Google Shared Drives
- **Multiple Formats**: Different formats for local vs. cloud storage
- **Automatic Upload**: Background upload after recording stops

## Troubleshooting

### Common Issues

**PyAudio Installation Fails**:
- Ensure PortAudio is installed first
- On Windows, try: `pip install pipwin && pipwin install pyaudio`
- On macOS with Apple Silicon, try: `arch -x86_64 pip install pyaudio`

**No Audio Devices Found**:
- Ensure your audio devices are connected and recognized by the OS
- Check system audio settings to verify device availability
- Try clicking "Refresh" to update the device list
- Restart the application if devices were recently connected

**Recording Not Working**:
- Ensure you've selected an export directory
- Check that at least one device is enabled (checkbox checked)
- Verify audio device permissions if prompted by the OS

**Poor Audio Quality**:
- Check your audio interface settings in system preferences
- Ensure adequate disk space for recording
- Close unnecessary applications that might interfere with audio

**Application Crashes**:
- Check that all dependencies are properly installed
- Try running from command line to see error messages
- Ensure PortAudio is compatible with your system

**Google Drive Issues**:
- Ensure `credentials.json` is in the application directory
- Check that Google Drive API is enabled in your Google Cloud project
- Verify folder ID is correct (use the Validate button)
- Try clearing authentication and re-authenticating
- Check internet connection for uploads

**Gain Control Issues**:
- Use "Auto" gain for optimal levels based on current audio
- Monitor peak levels to avoid clipping
- Adjust gain during recording for real-time optimization

**Refresh Button Issues**:
- ✅ **Crash Protection**: Refresh is now crash-resistant and handles GIL-related threading issues
- **Force Stream Cleanup**: Refresh forcefully stops all active streams before device scanning
- **Callback Safety**: Audio callbacks are temporarily disabled during refresh to prevent conflicts
- **Non-blocking Operation**: Refresh uses a non-threaded approach to avoid deadlocks
- **Multiple Refreshes**: Rapid successive refreshes are handled gracefully
- **Recovery**: If refresh encounters issues, automatic recovery creates a new audio instance

### Performance Tips

- **Close Unnecessary Apps**: Free up system resources for audio processing
- **Use SSD Storage**: Faster disk I/O for better recording performance
- **Monitor CPU Usage**: High CPU usage can cause audio dropouts
- **Limit Active Devices**: Recording from many devices simultaneously requires more resources

## Development

### Building from Source

1. **Prerequisites**:
   - Python 3.8+
   - PortAudio library
   - Git

2. **Setup Development Environment**:
   ```bash
   git clone <repository-url>
   cd inception-ai-recorder
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Running Tests** (if available):
   ```bash
   python -m pytest
   ```

## Differences from Swift Version

This Python port maintains the core functionality while adapting to Python conventions:

- **GUI Framework**: tkinter instead of SwiftUI for cross-platform compatibility
- **Audio Library**: PyAudio instead of direct PortAudio C bindings
- **Visualization**: matplotlib for waveforms instead of SwiftUI Canvas
- **File Format**: Same WAV output format and quality
- **Threading Model**: Python threading with queue-based communication

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Add docstrings for classes and functions
- Maintain thread safety in all audio-related code

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Original Swift Version**: [multitrack-recorder-swift](https://github.com/joewhaley/multitrack-recorder-swift)
- **PortAudio**: Cross-platform audio I/O library
- **PyAudio**: Python bindings for PortAudio
- **tkinter**: Python's standard GUI library
- **matplotlib**: Python plotting library

## Support

- **Issues**: Report bugs and request features on GitHub Issues
- **Documentation**: Check this README for detailed information
- **Original Project**: Reference the Swift version for additional context

---

**Ported to Python with ❤️ for cross-platform audio recording**