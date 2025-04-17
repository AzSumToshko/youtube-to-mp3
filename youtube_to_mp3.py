#!/usr/bin/env python3
"""
YouTube to MP3 Converter
------------------------
Convert YouTube videos to MP3 audio files.
"""
import os
import sys
import re
from typing import Optional, Tuple
import argparse
from pathlib import Path
import logging
import traceback

try:
    from pytube import YouTube
    from pytube.exceptions import PytubeError, RegexMatchError
except ImportError:
    print("Required package 'pytube' not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytube"])
    from pytube import YouTube
    from pytube.exceptions import PytubeError, RegexMatchError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def download_audio(url: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
    if output_path:
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path.cwd()
    
    try:
        # Clean up URL
        logger.info(f"Processing URL: {url}")
        # Remove any additional parameters
        if "?" in url:
            base_url, params = url.split("?", 1)
            if "v=" in params:
                # Extract video ID from parameters if it exists
                video_id = ""
                for param in params.split("&"):
                    if param.startswith("v="):
                        video_id = param[2:]
                        break
                if video_id:
                    logger.info(f"Extracted video ID: {video_id}")
                    url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                # Just use the base URL for youtu.be links
                url = base_url
                
        logger.info(f"Using URL: {url}")
        
        # Create YouTube object
        logger.info(f"Fetching video information from: {url}")
        yt = YouTube(url)
        
        # Get video title and create filename
        video_title = yt.title
        logger.info(f"Video title: {video_title}")
        sanitized_title = sanitize_filename(video_title)
        output_file = output_dir / f"{sanitized_title}.mp3"
        
        # Progress callback
        def progress_callback(stream, chunk, bytes_remaining):
            total_size = stream.filesize
            bytes_downloaded = total_size - bytes_remaining
            percent = (bytes_downloaded / total_size) * 100
            sys.stdout.write(f"\rDownloading: {percent:.1f}% complete")
            sys.stdout.flush()

        # Register progress callback
        yt.register_on_progress_callback(progress_callback)
        
        # Get audio stream
        logger.info(f"Available streams:")
        for stream in yt.streams.filter(only_audio=True):
            logger.info(f"  - {stream}")
            
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            logger.error("No audio streams found")
            return False, "No audio streams found for this video"
            
        logger.info(f"Selected stream: {audio_stream}")
        logger.info(f"Downloading audio for: {video_title}")
        
        # Download audio to temporary file
        temp_file = audio_stream.download(output_path=output_dir)
        
        # Convert to MP3
        logger.info("Converting to MP3 format...")
        base, _ = os.path.splitext(temp_file)
        mp3_file = f"{base}.mp3"
        
        os.rename(temp_file, mp3_file)
        
        # Finish
        logger.info(f"Successfully downloaded and converted to MP3: {mp3_file}")
        return True, mp3_file
        
    except RegexMatchError as e:
        error_msg = f"RegexMatchError (invalid URL format): {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except PytubeError as e:
        error_msg = f"PyTube error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg


def main():
    """Main function to parse arguments and initiate download."""
    parser = argparse.ArgumentParser(description="Download YouTube video and convert to MP3")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output", help="Output directory (default: current directory)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    success, result = download_audio(args.url, args.output)
    
    if not success:
        logger.error(f"Failed to download: {result}")
        sys.exit(1)
    else:
        logger.info(f"Download complete: {result}")


if __name__ == "__main__":
    main() 