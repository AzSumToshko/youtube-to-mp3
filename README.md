# YouTube to MP3 Converter

A Python-based tool to download YouTube videos and convert them to MP3 format, with optional remote server transfer capabilities.

## Features

- Download YouTube videos and convert to MP3
- Support for batch processing via configuration file
- Remote server transfer capability
- Sanitized filenames for compatibility
- Detailed logging and error handling
- Progress tracking during downloads

## Prerequisites

- Python 3.6+
- ffmpeg (for audio conversion)
- SSH access (for remote transfer feature)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AzSumToshko/youtube-to-mp3.git
cd youtube-to-mp3
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

### Single Video Download
```bash
python youtube_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID" -v
```

### Batch Processing with Remote Transfer
1. Edit `tracks_config.json` with your YouTube URLs and destination folders
2. Run:
```bash
python youtube_to_mp3_yt_dlp.py -v
```

## Configuration

### Environment Variables
Create a `.env` file with the following variables:
```
SSH_KEY_PATH=/path/to/your/ssh/key
SSH_PORT=your_ssh_port
SSH_USER=your_ssh_username
SSH_HOST=your_ssh_host
REMOTE_BASE_PATH=/path/to/remote/music/folder
```

### Batch Configuration
Edit `tracks_config.json`:
```json
{
    "tracks": [
        {
            "url": "youtube_url",
            "destination": "folder_name"
        }
    ],
    "default_destination": "Music"
}
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 