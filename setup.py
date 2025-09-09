from setuptools import setup, find_packages

setup(
    name="multitrack-audio-recorder",
    version="1.0.0",
    description="A multi-track audio recorder with real-time visualization",
    author="John Whaley",
    packages=find_packages(),
    install_requires=[
        "PyAudio>=0.2.14",
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "google-api-python-client>=2.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=0.5.0",
        "platformdirs>=3.0.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "multitrack-recorder=multitrack_recorder.main:main",
        ],
    },
)