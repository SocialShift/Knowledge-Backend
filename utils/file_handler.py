import os
import shutil
import uuid
from fastapi import UploadFile
from pathlib import Path
import os
from dotenv import load_dotenv
from .s3_handler import (
    upload_image_to_s3, 
    upload_video_to_s3, 
    delete_file_from_s3,
    S3_ENABLED
)

# Load environment variables
load_dotenv()

# Create media directories if they don't exist
MEDIA_ROOT = Path("media")
IMAGES_DIR = MEDIA_ROOT / "images"
VIDEOS_DIR = MEDIA_ROOT / "videos"

# Create directories if they don't exist
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

async def save_upload_file(upload_file: UploadFile, directory: Path) -> str:
    """
    Save an uploaded file to the specified directory and return the file path.
    
    Args:
        upload_file: The uploaded file
        directory: The directory to save the file in
        
    Returns:
        The relative path to the saved file
    """
    if not upload_file:
        return None
        
    # Generate a unique filename to prevent collisions
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create the full file path
    file_path = directory / unique_filename
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    # Return the relative path from the media root
    return str(file_path.relative_to(MEDIA_ROOT.parent))

async def save_image(image: UploadFile) -> str:
    """Save an uploaded image and return its path or S3 URL"""
    if not image:
        return None
    
    # Try S3 upload first if enabled
    if S3_ENABLED:
        s3_url = await upload_image_to_s3(image)
        if s3_url:
            return s3_url
    
    # Fall back to local storage
    return await save_upload_file(image, IMAGES_DIR)

async def save_video(video: UploadFile) -> str:
    """Save an uploaded video and return its path or S3 URL"""
    if not video:
        return None
    
    if S3_ENABLED:
        s3_url = await upload_video_to_s3(video)
        if s3_url:
            return s3_url
    
    return await save_upload_file(video, VIDEOS_DIR)

def delete_file(file_path: str) -> bool:
    """Delete a file given its path or S3 URL"""
    if not file_path:
        return False
    
    # Check if this is an S3 URL
    if S3_ENABLED and "amazonaws.com" in file_path:
        return delete_file_from_s3(file_path)
        
    # Convert to absolute path
    full_path = Path(file_path)
    if full_path.exists():
        os.remove(full_path)
        return True
    return False 