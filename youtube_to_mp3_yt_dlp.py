#!/usr/bin/env python3
"""
YouTube to MP3 Converter using yt-dlp
------------------------------------
Convert YouTube videos to MP3 audio files using yt-dlp and optionally transfer to remote server.
"""
import os
import sys
import re
import argparse
import json
from pathlib import Path
import logging
import subprocess
import shutil
import platform
import tempfile
from typing import List, Dict
from dotenv import load_dotenv
import yt_dlp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# SSH Configuration from environment variables
SSH_KEY_PATH = os.getenv('SSH_KEY_PATH')
SSH_PORT = os.getenv('SSH_PORT')
SSH_USER = os.getenv('SSH_USER')
SSH_HOST = os.getenv('SSH_HOST')
REMOTE_BASE_PATH = os.getenv('REMOTE_BASE_PATH')
SUDO_PASSWORD = os.getenv('SUDO_PASSWORD')

# Default config file path
DEFAULT_CONFIG_PATH = 'tracks_config.json'

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict:
    """
    Load track configuration from JSON file.
    
    Args:
        config_path: Path to the configuration JSON file
        
    Returns:
        Dict containing track configurations
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Validate config structure
        if not isinstance(config.get('tracks'), list):
            raise ValueError("Config must contain a 'tracks' list")
            
        return config
    except Exception as e:
        logger.error(f"Error loading config file: {str(e)}")
        sys.exit(1)

def transfer_to_server(file_path: str, remote_folder: str) -> bool:
    """
    Transfer a file to the remote server using SCP.
    
    Args:
        file_path (str): Path to the local file to transfer
        remote_folder (str): Remote folder name to transfer the file to
        
    Returns:
        bool: True if transfer was successful, False otherwise
    """
    local_file = Path(file_path)
    if not local_file.exists():
        logger.error(f"Local file not found: {local_file}")
        return False
        
    # Create a temporary copy with a simple name to avoid special character issues
    temp_file = local_file.parent / "song.mp3"
    try:
        # Copy the file with a simple name
        shutil.copy2(local_file, temp_file)
        logger.info(f"Created temporary file: {temp_file}")
        
        # Sanitize the original filename for the remote destination
        sanitized_filename = sanitize_filename(local_file.name)
        
        # Construct the SCP command with the sanitized original filename
        remote_path = f"{SSH_USER}@{SSH_HOST}:{REMOTE_BASE_PATH}/{remote_folder}/{sanitized_filename}"
        scp_cmd = [
            "scp",
            "-P", SSH_PORT,
            "-i", SSH_KEY_PATH,
            str(temp_file),
            remote_path
        ]
        
        # Execute the SCP command
        logger.info(f"Executing SCP command: {' '.join(scp_cmd)}")
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully transferred {local_file.name} to {remote_path}")
            return True
        else:
            logger.error(f"SCP transfer failed with error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error during file transfer: {str(e)}")
        return False
        
    finally:
        # Clean up the temporary file
        if temp_file.exists():
            try:
                temp_file.unlink()
                logger.info(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file}: {str(e)}")

def check_dependencies():
    """Check and install required dependencies."""
    # Check for yt-dlp
    try:
        import yt_dlp
        logger.info("yt-dlp is already installed.")
    except ImportError:
        logger.info("Installing yt-dlp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        logger.info("yt-dlp has been installed.")
    
    # Check for ffmpeg
    ffmpeg_found = False
    if shutil.which('ffmpeg'):
        logger.info("ffmpeg found in system PATH.")
        ffmpeg_found = True
    
    if not ffmpeg_found:
        logger.error("ffmpeg not found! MP3 conversion will not work.")
        system = platform.system()
        
        if system == "Windows":
            logger.error("Please install ffmpeg from https://ffmpeg.org/download.html")
            logger.error("After installation, add ffmpeg to your system PATH.")
            logger.error("\nWindows Installation Steps:")
            logger.error("1. Download FFmpeg from https://ffmpeg.org/download.html")
            logger.error("2. Extract the downloaded zip file")
            logger.error("3. Add the bin folder to your system PATH:")
            logger.error("   a. Open System Properties (Win + Pause/Break)")
            logger.error("   b. Click 'Advanced system settings'")
            logger.error("   c. Click 'Environment Variables'")
            logger.error("   d. Under System Variables, find 'Path'")
            logger.error("   e. Click 'Edit' and 'New'")
            logger.error("   f. Add the path to ffmpeg's bin folder")
            logger.error("   g. Click OK on all windows")
            logger.error("4. Restart your terminal/PowerShell")
        elif system == "Darwin":  # macOS
            logger.error("Install ffmpeg using Homebrew: brew install ffmpeg")
        else:  # Linux
            logger.error("Install ffmpeg using your package manager:")
            logger.error("Ubuntu/Debian: sudo apt-get install ffmpeg")
            logger.error("Fedora: sudo dnf install ffmpeg")
            logger.error("Arch Linux: sudo pacman -S ffmpeg")
        
        sys.exit(1)
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters from filename.
    
    Args:
        filename: Original filename with potentially invalid characters
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscore
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def copy_to_music_folder(source_file: str, music_folder: str, subfolder: str = None) -> str:
    """
    Copy the MP3 file to the specified music folder.
    
    Args:
        source_file: Path to the source MP3 file
        music_folder: Path to the destination music folder
        subfolder: Optional subfolder within the music folder
        
    Returns:
        Path to the copied file
    """
    try:
        # Create full destination path
        dest_folder = Path(music_folder)
        if subfolder:
            dest_folder = dest_folder / subfolder
            
        # Create destination folder if it doesn't exist
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Get the filename from the source path and sanitize it further for Windows
        source_path = Path(source_file)
        filename = source_path.name
        # Replace additional problematic characters
        filename = re.sub(r'[｜]', "-", filename)
        
        # Create destination file path
        dest_file = dest_folder / filename
        
        # Copy the file using shutil
        if source_path.exists():
            shutil.copy2(str(source_path), str(dest_file))
            logger.info(f"Copied MP3 to music folder: {dest_file}")
            return str(dest_file)
        else:
            logger.error(f"Source file not found: {source_path}")
            return None
        
    except Exception as e:
        logger.error(f"Error copying to music folder: {str(e)}")
        logger.error(f"Source: {source_file}")
        logger.error(f"Destination: {dest_folder}")
        return None


def download_audio(url: str, temp_dir: str, verbose: bool = False) -> tuple[bool, str, str]:
    """
    Download YouTube video and convert to MP3.
    
    Args:
        url: YouTube video URL
        temp_dir: Temporary directory to store downloaded files
        verbose: Whether to print verbose output
        
    Returns:
        tuple: (success: bool, file_path: str, title: str)
    """
    try:
        # Import yt-dlp
        import yt_dlp
            
        logger.info(f"Downloading audio from: {url}")
        
        # Configure yt-dlp options with MP3 conversion
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'paths': {'home': temp_dir},
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': not verbose,
            'progress': True,
        }
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                
                # Get the output filename
                if 'title' in info:
                    title = info['title']
                    # Find the actual file in the temp directory
                    mp3_files = list(Path(temp_dir).glob('*.mp3'))
                    
                    if mp3_files:
                        output_file = mp3_files[0]  # There should only be one file
                        logger.info(f"Download complete: {output_file}")
                        return True, str(output_file), title
                    else:
                        logger.error(f"No MP3 files found in {temp_dir}")
                        # List directory contents for debugging
                        logger.info(f"Directory contents: {list(Path(temp_dir).glob('*'))}")
                        return False, "", title
                else:
                    logger.error("Could not determine the output filename")
                    return False, "", ""
            except Exception as e:
                logger.error(f"Error during download: {str(e)}")
                return False, "", ""
                
    except Exception as e:
        logger.error(f"Error occurred during download: {str(e)}")
        return False, "", ""

def process_tracks(config: Dict, verbose: bool = False):
    """
    Process all tracks from the configuration.
    
    Args:
        config: Dictionary containing track configurations
        verbose: Whether to print verbose output
    """
    default_destination = config.get('default_destination', 'Music')
    tracks = config['tracks']
    
    logger.info(f"Found {len(tracks)} tracks to process")
    
    for i, track in enumerate(tracks, 1):
        url = track.get('url')
        destination = track.get('destination', default_destination)
        
        if not url:
            logger.warning(f"Skipping track {i} - missing URL")
            continue
            
        logger.info(f"Processing track {i}/{len(tracks)}: {url}")
        
        # Create a temporary directory for this track
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Download the audio
            success, file_path, title = download_audio(url, temp_dir, verbose)
            
            if success and file_path:
                # Transfer the file to the remote server
                if transfer_to_server(file_path, destination):
                    logger.info(f"Successfully processed track {i}: {title}")
                else:
                    logger.error(f"Failed to transfer track {i}: {title}")
            else:
                logger.error(f"Failed to download track {i}")

def main():
    """
    Main function to process tracks from config file.
    """
    parser = argparse.ArgumentParser(description="Download YouTube videos and convert to MP3 using yt-dlp")
    parser.add_argument("-c", "--config", default=DEFAULT_CONFIG_PATH,
                      help=f"Path to configuration file (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    # Check dependencies
    check_dependencies()
    
    # Load and validate config
    config = load_config(args.config)
    
    # Process all tracks
    process_tracks(config, args.verbose)

if __name__ == "__main__":
    main() 