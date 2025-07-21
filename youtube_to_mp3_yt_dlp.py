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
import requests
import glob
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TPE2, TDRC, TCON, TRCK, COMM, TPOS
from mutagen.mp3 import MP3
from datetime import datetime

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

def load_all_configs() -> Tuple[Dict, List[str]]:
    """
    Load all configuration files from inputs/ and inputs/additions/ directories.
    Skips template files and combines all tracks into a single configuration.
    
    Returns:
        Tuple containing:
        - Combined configuration dictionary
        - List of processed file paths for logging
    """
    try:
        inputs_dir = Path("inputs")
        if not inputs_dir.exists():
            logger.error("inputs/ directory not found")
            sys.exit(1)
        
        all_tracks = []
        processed_files = []
        
        # Find all JSON files in inputs/ directory
        json_files = list(inputs_dir.glob("*.json"))
        
        # Also find JSON files in inputs/additions/ subdirectory
        additions_dir = inputs_dir / "additions"
        if additions_dir.exists():
            json_files.extend(additions_dir.glob("*.json"))
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        for json_file in json_files:
            # Skip template files
            if "template" in json_file.name.lower():
                logger.info(f"Skipping template file: {json_file}")
                continue
                
            try:
                logger.info(f"Loading configuration from: {json_file}")
                with open(json_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if 'tracks' in config and isinstance(config['tracks'], list):
                    # Add tracks with original destination info
                    for track in config['tracks']:
                        if track.get('url'):  # Only add tracks with URLs
                            all_tracks.append(track)
                    
                    processed_files.append(str(json_file))
                    logger.info(f"Loaded {len(config['tracks'])} tracks from {json_file.name}")
                else:
                    logger.warning(f"Invalid config structure in {json_file.name} - skipping")
                    
            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {str(e)}")
                continue
        
        if not all_tracks:
            logger.error("No valid tracks found in any configuration files")
            sys.exit(1)
        
        # Create combined configuration
        combined_config = {
            "tracks": all_tracks,
            "default_destination": "Music"
        }
        
        logger.info(f"Successfully combined {len(all_tracks)} tracks from {len(processed_files)} files")
        return combined_config, processed_files
        
    except Exception as e:
        logger.error(f"Error loading configurations: {str(e)}")
        sys.exit(1)


def save_failed_downloads(failed_downloads: List[Dict], output_dir: str = "outputs") -> None:
    """
    Save failed download information to a text file.
    
    Args:
        failed_downloads: List of dictionaries containing failed download info
        output_dir: Directory to save the failed downloads file
    """
    if not failed_downloads:
        logger.info("No failed downloads to save")
        return
    
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        failed_file = output_path / "failed_downloads.txt"
        
        with open(failed_file, 'w', encoding='utf-8') as f:
            f.write("FAILED DOWNLOADS REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total failed: {len(failed_downloads)}\n\n")
            
            for i, failed in enumerate(failed_downloads, 1):
                f.write(f"{i}. URL: {failed['url']}\n")
                f.write(f"   Destination: {failed['destination']}\n")
                f.write(f"   Error: {failed['error']}\n")
                f.write(f"   Timestamp: {failed['timestamp']}\n")
                f.write("-" * 50 + "\n")
        
        logger.info(f"Failed downloads report saved to: {failed_file}")
        
    except Exception as e:
        logger.error(f"Error saving failed downloads report: {str(e)}")


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

def save_to_local_outputs(file_path: str, destination_folder: str) -> bool:
    """
    Save a file to the local outputs directory structure.
    
    Args:
        file_path (str): Path to the local file to save
        destination_folder (str): Destination folder name within outputs/
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        local_file = Path(file_path)
        if not local_file.exists():
            logger.error(f"Local file not found: {local_file}")
            return False
        
        # Create outputs directory structure
        outputs_dir = Path("outputs")
        destination_dir = outputs_dir / destination_folder
        
        # Create directories if they don't exist
        if not destination_dir.exists():
            logger.info(f"Creating directory structure: {destination_dir}")
            destination_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Successfully created directory: {destination_dir}")
        else:
            logger.debug(f"Directory already exists: {destination_dir}")
        
        # Sanitize filename for the destination
        sanitized_filename = sanitize_filename(local_file.name)
        destination_file = destination_dir / sanitized_filename
        
        # Copy the file to the destination
        shutil.copy2(local_file, destination_file)
        logger.info(f"Successfully saved {local_file.name} to {destination_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving file locally: {str(e)}")
        return False

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


def extract_metadata_from_info(info: Dict) -> Dict:
    """
    Extract comprehensive metadata from yt-dlp video info.
    
    Args:
        info: Video information dictionary from yt-dlp
        
    Returns:
        Dict containing extracted metadata for ID3 tags
    """
    metadata = {}
    
    # Essential metadata for music servers
    metadata['title'] = info.get('title', 'Unknown Title')
    metadata['artist'] = info.get('uploader', 'Unknown Artist')
    metadata['album'] = info.get('playlist_title') or f"{metadata['artist']} - YouTube"
    metadata['albumartist'] = metadata['artist']
    
    # Date handling
    upload_date = info.get('upload_date')
    if upload_date:
        try:
            # Convert YYYYMMDD format to YYYY-MM-DD
            date_obj = datetime.strptime(upload_date, '%Y%m%d')
            metadata['date'] = date_obj.strftime('%Y-%m-%d')
            metadata['year'] = str(date_obj.year)
        except (ValueError, TypeError):
            metadata['date'] = upload_date
            metadata['year'] = upload_date[:4] if len(upload_date) >= 4 else None
    
    # Genre from categories or tags
    categories = info.get('categories', [])
    tags = info.get('tags', [])
    
    if categories:
        metadata['genre'] = categories[0]  # Use first category as primary genre
    elif tags:
        # Look for music-related tags
        music_tags = [tag for tag in tags if any(keyword in tag.lower() 
                     for keyword in ['music', 'song', 'pop', 'rock', 'hip hop', 'electronic', 'jazz', 'classical'])]
        metadata['genre'] = music_tags[0] if music_tags else 'Music'
    else:
        metadata['genre'] = 'Music'
    
    # Track number (if part of playlist)
    playlist_index = info.get('playlist_index')
    if playlist_index:
        metadata['tracknumber'] = str(playlist_index)
    
    # Duration
    duration = info.get('duration')
    if duration:
        metadata['length'] = str(int(duration * 1000))  # Convert to milliseconds
    
    # Additional metadata for description/comments
    description = info.get('description', '')
    if description:
        # Truncate description for comment field (max 3000 chars for compatibility)
        metadata['comment'] = description[:3000] if len(description) > 3000 else description
    
    # Channel/Uploader info
    metadata['composer'] = info.get('uploader', '')
    
    # View count and like count (if available) - store in comment
    view_count = info.get('view_count')
    like_count = info.get('like_count')
    additional_info = []
    
    if view_count:
        additional_info.append(f"Views: {view_count:,}")
    if like_count:
        additional_info.append(f"Likes: {like_count:,}")
    
    if additional_info:
        stats_info = " | ".join(additional_info)
        if metadata.get('comment'):
            metadata['comment'] += f"\n\n[Stats: {stats_info}]"
        else:
            metadata['comment'] = f"[Stats: {stats_info}]"
    
    # Thumbnail URL for album art
    thumbnail = info.get('thumbnail')
    if not thumbnail:
        # Try to get the best thumbnail
        thumbnails = info.get('thumbnails', [])
        if thumbnails:
            # Get highest quality thumbnail
            thumbnail = max(thumbnails, key=lambda x: x.get('height', 0) * x.get('width', 0))
            thumbnail = thumbnail.get('url')
    
    metadata['thumbnail_url'] = thumbnail
    
    # Original URL for reference
    metadata['webpage_url'] = info.get('webpage_url', '')
    
    return metadata


def download_thumbnail(thumbnail_url: str, temp_dir: str) -> Optional[str]:
    """
    Download thumbnail image from URL.
    
    Args:
        thumbnail_url: URL of the thumbnail image
        temp_dir: Temporary directory to save the image
        
    Returns:
        Path to downloaded thumbnail file or None if failed
    """
    if not thumbnail_url:
        logger.warning("No thumbnail URL provided")
        return None
        
    try:
        logger.info(f"Downloading thumbnail: {thumbnail_url}")
        response = requests.get(thumbnail_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Determine file extension from content type or URL
        content_type = response.headers.get('content-type', '')
        if 'image/jpeg' in content_type or thumbnail_url.endswith(('.jpg', '.jpeg')):
            ext = '.jpg'
        elif 'image/png' in content_type or thumbnail_url.endswith('.png'):
            ext = '.png'
        elif 'image/webp' in content_type or thumbnail_url.endswith('.webp'):
            ext = '.webp'
        else:
            ext = '.jpg'  # Default to JPEG
        
        thumbnail_path = Path(temp_dir) / f"thumbnail{ext}"
        
        with open(thumbnail_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Thumbnail downloaded successfully: {thumbnail_path}")
        return str(thumbnail_path)
        
    except Exception as e:
        logger.warning(f"Failed to download thumbnail: {str(e)}")
        return None


def apply_metadata_to_mp3(mp3_path: str, metadata: Dict, thumbnail_path: Optional[str] = None) -> bool:
    """
    Apply comprehensive metadata to MP3 file using ID3 tags.
    
    Args:
        mp3_path: Path to the MP3 file
        metadata: Dictionary containing metadata to apply
        thumbnail_path: Optional path to thumbnail image for album art
        
    Returns:
        bool: True if metadata was applied successfully, False otherwise
    """
    try:
        logger.info(f"Applying metadata to: {mp3_path}")
        
        # Load the MP3 file
        audio = MP3(mp3_path, ID3=ID3)
        
        # Add ID3 tag if it doesn't exist
        if audio.tags is None:
            audio.tags = ID3()
        
        # Clear existing tags to avoid conflicts
        audio.tags.clear()
        
        # Apply basic metadata using ID3 frames
        if metadata.get('title'):
            audio.tags.add(TIT2(encoding=3, text=metadata['title']))
            
        if metadata.get('artist'):
            audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
            
        if metadata.get('album'):
            audio.tags.add(TALB(encoding=3, text=metadata['album']))
            
        if metadata.get('albumartist'):
            audio.tags.add(TPE2(encoding=3, text=metadata['albumartist']))
            
        if metadata.get('date'):
            audio.tags.add(TDRC(encoding=3, text=metadata['date']))
            
        if metadata.get('genre'):
            audio.tags.add(TCON(encoding=3, text=metadata['genre']))
            
        if metadata.get('tracknumber'):
            audio.tags.add(TRCK(encoding=3, text=metadata['tracknumber']))
        
        # Add comment with additional info
        if metadata.get('comment'):
            audio.tags.add(COMM(encoding=3, lang='eng', desc='', text=metadata['comment']))
        
        # Add album art if thumbnail is available
        if thumbnail_path and Path(thumbnail_path).exists():
            logger.info(f"Adding album art from: {thumbnail_path}")
            try:
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_data = f.read()
                
                # Determine MIME type
                mime_type = 'image/jpeg'
                if thumbnail_path.lower().endswith('.png'):
                    mime_type = 'image/png'
                elif thumbnail_path.lower().endswith('.webp'):
                    mime_type = 'image/webp'
                
                # Add album art
                audio.tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,  # Cover (front) image
                    desc='Cover',
                    data=thumbnail_data
                ))
                logger.info("Album art added successfully")
                
            except Exception as e:
                logger.warning(f"Failed to add album art: {str(e)}")
        
        # Save the changes
        audio.save()
        logger.info("Metadata applied successfully")
        
        # Log applied metadata for verification
        logger.debug("Applied metadata:")
        for key, value in metadata.items():
            if key != 'thumbnail_url' and value:
                logger.debug(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error applying metadata to MP3: {str(e)}")
        return False


def download_audio(url: str, temp_dir: str, verbose: bool = False) -> tuple[bool, str, str, Dict]:
    """
    Download YouTube video and convert to MP3 with metadata extraction.
    
    Args:
        url: YouTube video URL
        temp_dir: Temporary directory to store downloaded files
        verbose: Whether to print verbose output
        
    Returns:
        tuple: (success: bool, file_path: str, title: str, metadata: Dict)
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
                
                # Extract comprehensive metadata
                metadata = extract_metadata_from_info(info)
                logger.info(f"Extracted metadata for: {metadata.get('title', 'Unknown')}")
                
                # Get the output filename
                if 'title' in info:
                    title = info['title']
                    # Find the actual file in the temp directory
                    mp3_files = list(Path(temp_dir).glob('*.mp3'))
                    
                    if mp3_files:
                        output_file = mp3_files[0]  # There should only be one file
                        logger.info(f"Download complete: {output_file}")
                        return True, str(output_file), title, metadata
                    else:
                        logger.error(f"No MP3 files found in {temp_dir}")
                        # List directory contents for debugging
                        logger.info(f"Directory contents: {list(Path(temp_dir).glob('*'))}")
                        return False, "", title, {}
                else:
                    logger.error("Could not determine the output filename")
                    return False, "", "", {}
            except Exception as e:
                logger.error(f"Error during download: {str(e)}")
                return False, "", "", {}
                
    except Exception as e:
        logger.error(f"Error occurred during download: {str(e)}")
        return False, "", "", {}

def process_tracks(config: Dict, verbose: bool = False, save_local: bool = False, apply_metadata: bool = True, all_mode: bool = False):
    """
    Process all tracks from the configuration with comprehensive exception handling.
    
    Args:
        config: Dictionary containing track configurations
        verbose: Whether to print verbose output
        save_local: Whether to save files locally instead of transferring to server
        apply_metadata: Whether to extract and apply metadata to MP3 files
        all_mode: Whether running in --all mode (saves directly to outputs/)
    """
    default_destination = config.get('default_destination', 'Music')
    tracks = config['tracks']
    failed_downloads = []
    successful_downloads = 0
    
    logger.info(f"Found {len(tracks)} tracks to process")
    
    if save_local:
        logger.info("Local save mode enabled - files will be saved to outputs/ directory")
    else:
        logger.info("Remote transfer mode enabled - files will be transferred to server")
    
    if all_mode:
        logger.info("All mode enabled - files will be saved directly to outputs/ without subfolders")
    
    for i, track in enumerate(tracks, 1):
        url = track.get('url')
        destination = track.get('destination', default_destination)
        
        # In all mode, save directly to outputs
        if all_mode:
            destination = "."  # Save directly to outputs/ root
        
        if not url:
            logger.warning(f"Skipping track {i} - missing URL")
            failed_downloads.append({
                'url': url or 'N/A',
                'destination': destination,
                'error': 'Missing URL',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            continue
            
        logger.info(f"Processing track {i}/{len(tracks)}: {url}")
        logger.info(f"Destination: {'outputs/' if all_mode else destination}")
        
        try:
            # Create a temporary directory for this track
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Created temporary directory: {temp_dir}")
                
                try:
                    # Download the audio with metadata extraction
                    success, file_path, title, metadata = download_audio(url, temp_dir, verbose)
                    
                    if not success or not file_path:
                        error_msg = f"Download failed for track {i}"
                        logger.error(error_msg)
                        failed_downloads.append({
                            'url': url,
                            'destination': destination,
                            'error': error_msg,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        continue
                    
                    metadata_success = False
                    
                    # Apply metadata if enabled
                    if apply_metadata:
                        try:
                            logger.info(f"Processing metadata and album art for: {title}")
                            
                            # Download thumbnail for album art
                            thumbnail_path = None
                            if metadata.get('thumbnail_url'):
                                thumbnail_path = download_thumbnail(metadata['thumbnail_url'], temp_dir)
                            
                            # Apply comprehensive metadata to the MP3 file
                            metadata_success = apply_metadata_to_mp3(file_path, metadata, thumbnail_path)
                            if metadata_success:
                                logger.info(f"Metadata successfully applied to: {title}")
                            else:
                                logger.warning(f"Failed to apply metadata to: {title}")
                        except Exception as metadata_error:
                            logger.warning(f"Metadata processing failed for {title}: {str(metadata_error)}")
                            metadata_success = False
                    else:
                        logger.info(f"Skipping metadata processing (disabled by --no-metadata flag)")
                    
                    # Save locally or transfer to server
                    try:
                        if save_local:
                            # Save the file to local outputs directory
                            if save_to_local_outputs(file_path, destination):
                                logger.info(f"Successfully processed track {i}: {title}")
                                if apply_metadata and metadata_success:
                                    logger.info(f"  ✓ Applied metadata: Artist: {metadata.get('artist', 'N/A')}, Album: {metadata.get('album', 'N/A')}, Genre: {metadata.get('genre', 'N/A')}")
                                successful_downloads += 1
                            else:
                                error_msg = f"Failed to save track {i} to local outputs: {title}"
                                logger.error(error_msg)
                                failed_downloads.append({
                                    'url': url,
                                    'destination': destination,
                                    'error': error_msg,
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                        else:
                            # Transfer the file to the remote server
                            if transfer_to_server(file_path, destination):
                                logger.info(f"Successfully processed track {i}: {title}")
                                if apply_metadata and metadata_success:
                                    logger.info(f"  ✓ Applied metadata: Artist: {metadata.get('artist', 'N/A')}, Album: {metadata.get('album', 'N/A')}, Genre: {metadata.get('genre', 'N/A')}")
                                successful_downloads += 1
                            else:
                                error_msg = f"Failed to transfer track {i}: {title}"
                                logger.error(error_msg)
                                failed_downloads.append({
                                    'url': url,
                                    'destination': destination,
                                    'error': error_msg,
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except Exception as save_error:
                        error_msg = f"Save/transfer error for track {i} ({title}): {str(save_error)}"
                        logger.error(error_msg)
                        failed_downloads.append({
                            'url': url,
                            'destination': destination,
                            'error': error_msg,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        
                except Exception as download_error:
                    error_msg = f"Download error for track {i}: {str(download_error)}"
                    logger.error(error_msg)
                    failed_downloads.append({
                        'url': url,
                        'destination': destination,
                        'error': error_msg,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
        except Exception as track_error:
            error_msg = f"Unexpected error processing track {i}: {str(track_error)}"
            logger.error(error_msg)
            failed_downloads.append({
                'url': url,
                'destination': destination,
                'error': error_msg,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # Processing summary
    logger.info(f"\n{'='*60}")
    logger.info(f"PROCESSING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total tracks: {len(tracks)}")
    logger.info(f"Successful downloads: {successful_downloads}")
    logger.info(f"Failed downloads: {len(failed_downloads)}")
    logger.info(f"Success rate: {(successful_downloads/len(tracks)*100):.1f}%")
    
    # Save failed downloads to file
    if failed_downloads:
        save_failed_downloads(failed_downloads, "outputs")
        logger.warning(f"⚠️  {len(failed_downloads)} downloads failed - see outputs/failed_downloads.txt for details")
    else:
        logger.info("🎉 All downloads completed successfully!")

def main():
    """
    Main function to process tracks from config file or all input files.
    """
    parser = argparse.ArgumentParser(description="Download YouTube videos and convert to MP3 using yt-dlp")
    parser.add_argument("-c", "--config", default=DEFAULT_CONFIG_PATH,
                      help=f"Path to configuration file (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Enable verbose output")
    parser.add_argument("-l", "--local", action="store_true",
                      help="Save files locally in outputs/ directory instead of transferring to server")
    parser.add_argument("--no-metadata", action="store_true",
                      help="Skip metadata extraction and embedding (faster processing)")
    parser.add_argument("--all", action="store_true",
                      help="Process all JSON files in inputs/ and inputs/additions/ directories, save directly to outputs/")
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    # Check dependencies
    check_dependencies()
    
    # Load configuration
    if args.all:
        logger.info("🚀 ALL MODE: Processing all input files")
        logger.info("Files will be saved directly to outputs/ directory")
        config, processed_files = load_all_configs()
        
        logger.info("📁 Processed files:")
        for file_path in processed_files:
            logger.info(f"  - {file_path}")
        logger.info("")
        
        # Force local mode when using --all
        if not args.local:
            logger.info("Automatically enabling local mode for --all flag")
            args.local = True
        
        # Process all tracks in all mode
        process_tracks(config, args.verbose, args.local, not args.no_metadata, all_mode=True)
    else:
        # Regular single config processing
        config = load_config(args.config)
        process_tracks(config, args.verbose, args.local, not args.no_metadata, all_mode=False)

if __name__ == "__main__":
    main() 