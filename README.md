# YouTube to MP3 Converter

A comprehensive Python utility that downloads YouTube videos, converts them to MP3 format, and automatically embeds rich metadata including album art for optimal use with music servers like Navidrome and Jellyfin.

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

### Enhanced yt-dlp Script with Metadata Support

The enhanced script uses `yt-dlp` with comprehensive metadata extraction and embedding:

#### Single Track Download
```bash
# Basic download with full metadata and album art
python youtube_to_mp3_yt_dlp.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download without metadata (faster processing)
python youtube_to_mp3_yt_dlp.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --no-metadata

# Verbose output to see metadata extraction process
python youtube_to_mp3_yt_dlp.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -v
```

#### Batch Processing with JSON Configuration
```bash
# Process tracks from configuration file
python youtube_to_mp3_yt_dlp.py -c inputs/emilia.json

# Save to local outputs/ directory instead of remote server
python youtube_to_mp3_yt_dlp.py -c inputs/emilia.json --local

# Process with verbose output
python youtube_to_mp3_yt_dlp.py -c inputs/emilia.json -v --local
```

#### Configuration File Format
Create JSON files in the `inputs/` directory with this structure:

```json
{
    "tracks": [
        {
            "url": "https://youtu.be/VIDEO_ID_1",
            "destination": "Artist Name"
        },
        {
            "url": "https://youtu.be/VIDEO_ID_2", 
            "destination": "Artist Name"
        }
    ],
    "default_destination": "Artist Name"
}
```

#### Batch Processing All Input Files
```bash
# Process ALL JSON files in inputs/ and inputs/additions/ directories
python youtube_to_mp3_yt_dlp.py --all

# Process all files with verbose output
python youtube_to_mp3_yt_dlp.py --all -v

# Process all files without metadata (faster)
python youtube_to_mp3_yt_dlp.py --all --no-metadata
```

#### Command Line Options

- `-c, --config`: Specify configuration file (default: tracks_config.json)
- `-v, --verbose`: Enable verbose output and metadata details
- `-l, --local`: Save files locally in outputs/ directory instead of transferring to server
- `--no-metadata`: Skip metadata extraction and embedding (faster processing)
- `--all`: Process all JSON files in inputs/ and inputs/additions/, save directly to outputs/

### Alternative Script (pytube)

An alternative script using `pytube` is also provided, but it may be less reliable as YouTube frequently updates their platform:

```bash
python youtube_to_mp3.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

#### Options

- `-o, --output`: Specify output directory (default: current directory)
- `-v, --verbose`: Enable verbose output

## Features

### Core Download Features
- Downloads the highest quality audio stream available
- Shows download progress
- Automatically sanitizes filenames
- Creates output directory if it doesn't exist
- Proper error handling for common issues
- Automatically installs required Python dependencies

### 🎵 Enhanced Metadata Support (NEW!)
- **Comprehensive ID3 Tag Embedding**: Automatically extracts and embeds rich metadata
  - **Title**: Video title as song title
  - **Artist**: Channel/uploader name as artist
  - **Album**: Playlist title or auto-generated album name
  - **Genre**: Extracted from video categories and tags
  - **Date**: Upload date in proper format
  - **Track Numbers**: For playlist downloads
  - **Duration**: Exact track length
  - **Comments**: Video description and statistics

- **Album Art Integration**: Downloads and embeds high-quality thumbnails as album art
  - Supports JPEG, PNG, and WebP formats
  - Automatically selects highest quality available
  - Perfect integration with music servers

- **Music Server Optimization**: Optimized for popular self-hosted music servers
  - **Navidrome**: Full metadata compatibility
  - **Jellyfin**: Complete library integration
  - **Plex**: Rich metadata display
  - **Subsonic-compatible**: Works with all Subsonic API servers

### Configuration & Batch Processing
- **JSON Configuration Files**: Process multiple tracks with organized destinations
- **Batch Download Support**: Download entire artist catalogs or playlists
- **Flexible Output Options**: Local storage or remote server transfer
- **Metadata Control**: Option to disable metadata processing for faster downloads
- **Bulk Processing**: `--all` flag processes all input files at once
- **Comprehensive Error Handling**: Failed downloads are logged and skipped automatically

### 🛡️ Robust Error Handling & Reporting
- **Automatic Error Recovery**: Failed downloads don't stop the entire process
- **Detailed Error Logging**: Each failure is logged with timestamp and reason
- **Failed Downloads Report**: Automatically generates `outputs/failed_downloads.txt`
- **Processing Summary**: Shows success rates and completion statistics
- **Graceful Skipping**: Invalid URLs or corrupted files are automatically skipped

## 📁 All Mode Operation

The `--all` flag automatically:
1. Scans all `.json` files in `inputs/` directory
2. Scans all `.json` files in `inputs/additions/` subdirectory  
3. Skips template files (files with "template" in the name)
4. Combines all tracks into a single processing batch
5. Saves all files directly to `outputs/` (no artist subfolders)
6. Automatically enables local mode

Example directory structure after `--all` processing:
```
outputs/
├── failed_downloads.txt          # Error report (if any failures)
├── Song Title 1.mp3              # Direct file storage
├── Song Title 2.mp3
├── Another Song.mp3
└── ...
```

## 📋 Error Reporting

When downloads fail, a detailed report is generated at `outputs/failed_downloads.txt`:

```
FAILED DOWNLOADS REPORT
==================================================
Generated: 2024-01-15 14:30:45
Total failed: 3

1. URL: https://youtube.com/watch?v=INVALID_ID
   Destination: Artist Name
   Error: Video unavailable
   Timestamp: 2024-01-15 14:28:12
--------------------------------------------------
2. URL: https://youtube.com/watch?v=PRIVATE_VIDEO
   Destination: Another Artist
   Error: Private video
   Timestamp: 2024-01-15 14:29:33
--------------------------------------------------
```

The script continues processing even when individual downloads fail, ensuring maximum success rate for large batches.

## Testing the Metadata Functionality

To verify that the enhanced metadata features are working correctly:

```bash
# Run the test suite
python test_metadata.py
```

This will:
1. Download a sample Creative Commons video
2. Extract comprehensive metadata 
3. Download and embed album art
4. Create a test MP3 file in `test_output/`
5. Verify all metadata was properly embedded

After running the test, import the generated MP3 file into your music server (Navidrome, Jellyfin, etc.) to verify that:
- Artist, album, and title information display correctly
- Album art appears properly
- Additional metadata (genre, date, comments) is accessible
- The file is properly organized in your library

## Metadata Details

The enhanced script extracts and embeds the following ID3 tags:

| ID3 Tag | Source | Description |
|---------|--------|-------------|
| **TIT2** (Title) | Video title | Song title |
| **TPE1** (Artist) | Channel/uploader name | Primary artist |
| **TALB** (Album) | Playlist title or auto-generated | Album name |
| **TPE2** (Album Artist) | Channel/uploader name | Album artist |
| **TDRC** (Date) | Upload date | Release date |
| **TCON** (Genre) | Video categories/tags | Music genre |
| **TRCK** (Track) | Playlist index | Track number |
| **COMM** (Comment) | Description + stats | Additional info |
| **APIC** (Album Art) | Video thumbnail | Cover image |

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