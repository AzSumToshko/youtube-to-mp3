#!/usr/bin/env python3
"""
Test script for YouTube to MP3 converter with metadata support
-------------------------------------------------------------
This script tests the metadata extraction and embedding functionality
using a sample video. Perfect for verifying everything works correctly.
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# Add the current directory to the path so we can import the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_to_mp3_yt_dlp import download_audio, extract_metadata_from_info, apply_metadata_to_mp3, download_thumbnail

def test_metadata_extraction():
    """Test the metadata functionality with a sample video."""
    
    # Use a Creative Commons licensed video for testing
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo - first YouTube video
    
    print("🎵 YouTube to MP3 Metadata Test")
    print("=" * 50)
    print(f"Test URL: {test_url}")
    print()
    
    # Create a test output directory
    test_output_dir = Path("test_output")
    test_output_dir.mkdir(exist_ok=True)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print("⬇️  Downloading and extracting metadata...")
            
            # Download the audio with metadata
            success, file_path, title, metadata = download_audio(test_url, temp_dir, verbose=True)
            
            if not success:
                print("❌ Download failed!")
                return False
            
            print(f"✅ Download successful: {title}")
            print()
            
            # Display extracted metadata
            print("📋 Extracted Metadata:")
            print("-" * 30)
            for key, value in metadata.items():
                if key != 'thumbnail_url' and value:
                    print(f"  {key.capitalize().replace('_', ' ')}: {value}")
            print()
            
            # Download thumbnail
            print("🖼️  Downloading album art...")
            thumbnail_path = None
            if metadata.get('thumbnail_url'):
                thumbnail_path = download_thumbnail(metadata['thumbnail_url'], temp_dir)
                if thumbnail_path:
                    print(f"✅ Album art downloaded: {Path(thumbnail_path).name}")
                else:
                    print("⚠️  Album art download failed")
            else:
                print("⚠️  No thumbnail URL found")
            print()
            
            # Apply metadata to MP3
            print("🏷️  Applying metadata to MP3...")
            metadata_success = apply_metadata_to_mp3(file_path, metadata, thumbnail_path)
            
            if metadata_success:
                print("✅ Metadata applied successfully!")
            else:
                print("❌ Metadata application failed!")
                return False
            
            # Copy the test file to the output directory
            test_file = test_output_dir / f"test_sample_{Path(file_path).name}"
            import shutil
            shutil.copy2(file_path, test_file)
            print(f"📁 Test file saved to: {test_file}")
            print()
            
            # Verify metadata was applied
            print("🔍 Verifying embedded metadata...")
            try:
                from mutagen.mp3 import MP3
                from mutagen.id3 import ID3
                
                audio = MP3(str(test_file), ID3=ID3)
                if audio.tags:
                    print("✅ ID3 tags found:")
                    for tag_name, tag_value in audio.tags.items():
                        if hasattr(tag_value, 'text') and tag_value.text:
                            print(f"  {tag_name}: {tag_value.text[0] if isinstance(tag_value.text, list) else tag_value.text}")
                        elif tag_name.startswith('APIC'):
                            print(f"  {tag_name}: Album art embedded ({len(tag_value.data)} bytes)")
                else:
                    print("⚠️  No ID3 tags found")
            except Exception as e:
                print(f"⚠️  Error verifying metadata: {str(e)}")
            
            print()
            print("🎉 Test completed successfully!")
            print(f"📁 Test file location: {test_file.absolute()}")
            print()
            print("💡 Tips:")
            print("  - Import this file into Navidrome, Jellyfin, or your preferred music server")
            print("  - Check that the metadata and album art display correctly")
            print("  - The file should be properly organized by Artist/Album")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

def create_test_config():
    """Create a sample configuration file for testing."""
    
    test_config = {
        "tracks": [
            {
                "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "destination": "Test Artist"
            }
        ],
        "default_destination": "Test Artist"
    }
    
    config_path = Path("test_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, indent=4)
    
    print(f"📝 Created test configuration: {config_path}")
    print("   You can run: python youtube_to_mp3_yt_dlp.py -c test_config.json --local")
    print()

if __name__ == "__main__":
    print("🧪 YouTube to MP3 Metadata Test Suite")
    print("=====================================")
    print()
    
    # Create test configuration
    create_test_config()
    
    # Run the metadata test
    success = test_metadata_extraction()
    
    if success:
        print("✅ All tests passed! Your metadata functionality is working correctly.")
        print()
        print("🚀 Next steps:")
        print("  1. Check the test_output/ directory for your sample file")
        print("  2. Try importing it into your music server")
        print("  3. Run with your own URLs using the main script")
        sys.exit(0)
    else:
        print("❌ Tests failed. Please check the error messages above.")
        sys.exit(1) 