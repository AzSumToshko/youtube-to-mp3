# YouTube to MP3 Converter

A simple Python utility that downloads YouTube videos and converts them to MP3 format.

## Prerequisites

- Python 3.6 or higher
- Internet connection
- FFmpeg (for MP3 conversion)

## Installation

1. Clone or download this repository:

```bash
# Clone this repository
git clone https://github.com/yourusername/youtube-to-mp3.git
cd youtube-to-mp3

# Or download just the scripts
curl -O https://raw.githubusercontent.com/yourusername/youtube-to-mp3/main/youtube_to_mp3_yt_dlp.py
chmod +x youtube_to_mp3_yt_dlp.py
```

2. Set up a virtual environment (recommended):

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate.bat  # CMD
.\venv\Scripts\Activate.ps1  # PowerShell

# On macOS/Linux:
source venv/bin/activate
```

3. Install required Python dependencies:

```bash
pip install -r requirements.txt
```

4. Install FFmpeg (required for MP3 conversion):

- **Windows**:
  1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
  2. Extract the downloaded archive
  3. Add the `bin` folder to your PATH environment variable

- **macOS**:
  ```bash
  brew install ffmpeg
  ```

- **Ubuntu/Debian**:
  ```bash
  sudo apt-get install ffmpeg
  ```

- **Fedora**:
  ```bash
  sudo dnf install ffmpeg
  ```

- **Arch Linux**:
  ```bash
  sudo pacman -S ffmpeg
  ```

## Usage

### Recommended Script (yt-dlp)

The recommended script uses the `yt-dlp` library, which is more reliable and actively maintained:

```bash
python youtube_to_mp3_yt_dlp.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

#### Options

- `-o, --output`: Specify output directory (default: current directory)
- `-v, --verbose`: Enable verbose output
- `-k, --keep`: Keep original video/audio file after conversion

### Alternative Script (pytube)

An alternative script using `pytube` is also provided, but it may be less reliable as YouTube frequently updates their platform:

```bash
python youtube_to_mp3.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

#### Options

- `-o, --output`: Specify output directory (default: current directory)
- `-v, --verbose`: Enable verbose output

## Features

- Downloads the highest quality audio stream available
- Shows download progress
- Automatically sanitizes filenames
- Creates output directory if it doesn't exist
- Proper error handling for common issues
- Automatically installs required Python dependencies

## Troubleshooting

### FFmpeg Not Found

If you see a message like:
```
ffmpeg not found! Converting to MP3 requires ffmpeg.
```

Follow the FFmpeg installation instructions above and ensure it's added to your system PATH.

### Download Errors

If you encounter download errors:

1. Make sure you have an active internet connection
2. Check if the video URL is valid and accessible
3. Some videos may have restrictions that prevent downloading
4. YouTube may have updated their platform, requiring updates to the libraries

## License

This project is licensed under the MIT License - see the LICENSE file for details. 