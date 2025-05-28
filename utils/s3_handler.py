import os
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import uuid
from pathlib import Path
from dotenv import load_dotenv
import io
from PIL import Image
import tempfile
import subprocess

# Load environment variables
load_dotenv()

# S3 configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ENABLED = os.getenv("S3_ENABLED", "false").lower() == "true"

# Initialize S3 client if S3 is enabled
s3_client = None
if S3_ENABLED and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

async def compress_image(image_data: bytes, quality: int = 85, max_size: tuple = (1920, 1080)) -> bytes:
    """
    Compress an image using PIL
    
    Args:
        image_data: The original image data
        quality: JPEG compression quality (1-100)
        max_size: Maximum dimensions (width, height)
        
    Returns:
        Compressed image data
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed (JPEG doesn't support alpha channel)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        # Resize if larger than max_size while maintaining aspect ratio
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.LANCZOS)
            
        # Save compressed image to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        
        return output.getvalue()
    except Exception as e:
        print(f"Error compressing image: {e}")
        return image_data  # Return original if compression fails

async def compress_video(video_data: bytes, crf: int = 28) -> bytes:
    """
    Compress a video using FFmpeg
    
    Args:
        video_data: The original video data
        crf: Constant Rate Factor (0-51, higher means more compression)
        
    Returns:
        Compressed video data or original if compression fails
    """
    try:
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as input_file:
            input_file.write(video_data)
            input_path = input_file.name
            
        output_path = input_path + '_compressed.mp4'
        
        # Run FFmpeg compression
        cmd = [
            'ffmpeg', '-i', input_path, 
            '-c:v', 'libx264', '-crf', str(crf), 
            '-preset', 'medium', 
            '-c:a', 'aac', '-b:a', '128k', 
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr.decode()}")
            os.unlink(input_path)
            return video_data
            
        # Read compressed video
        with open(output_path, 'rb') as f:
            compressed_data = f.read()
            
        # Clean up temporary files
        os.unlink(input_path)
        os.unlink(output_path)
        
        return compressed_data
    except Exception as e:
        print(f"Error compressing video: {e}")
        try:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
        return video_data  # Return original if compression fails

async def upload_file_to_s3(upload_file: UploadFile, directory: str, compress: bool = True) -> str:
    """
    Upload a file to S3 bucket and return the URL.
    
    Args:
        upload_file: The uploaded file
        directory: The directory prefix within the S3 bucket
        compress: Whether to compress the file before uploading
        
    Returns:
        The URL of the uploaded file
    """
    if not S3_ENABLED or not s3_client:
        return None
        
    if not upload_file:
        return None
    
    # Generate a unique filename to prevent collisions
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create the full object key with directory prefix
    object_key = f"{directory}/{unique_filename}"
    
    try:
        # Read file content
        file_content = await upload_file.read()
        
        # Compress if needed
        if compress:
            if directory == "images" and file_extension.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                file_content = await compress_image(file_content)
                content_type = 'image/jpeg'
            elif directory == "videos" and file_extension.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
                file_content = await compress_video(file_content)
                content_type = upload_file.content_type
            else:
                content_type = upload_file.content_type
        else:
            content_type = upload_file.content_type
        
        # Upload the file
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=file_content,
            ContentType=content_type
        )
        
        # Reset file cursor for potential further use
        await upload_file.seek(0)
        
        # Construct and return the S3 URL
        if AWS_REGION == "us-east-1":
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{object_key}"
        else:
            s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{object_key}"
        
        return s3_url
    
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return None

async def upload_image_to_s3(image: UploadFile, compress: bool = True) -> str:
    """Upload an image to S3 and return its URL"""
    if not image:
        return None
    return await upload_file_to_s3(image, "images", compress)

async def upload_video_to_s3(video: UploadFile, compress: bool = True) -> str:
    """Upload a video to S3 and return its URL"""
    if not video:
        return None
    return await upload_file_to_s3(video, "videos", compress)

def delete_file_from_s3(s3_url: str) -> bool:
    """Delete a file from S3 given its URL"""
    if not S3_ENABLED or not s3_client:
        return False
        
    if not s3_url:
        return False
    
    try:
        # Extract the object key from the URL
        if "amazonaws.com/" in s3_url:
            object_key = s3_url.split("amazonaws.com/")[1]
            
            # Delete the object
            s3_client.delete_object(
                Bucket=S3_BUCKET_NAME,
                Key=object_key
            )
            return True
    except ClientError as e:
        print(f"Error deleting from S3: {e}")
    
    return False

def upload_local_file_to_s3(file_path, directory="images", compress: bool = True) -> str:
    """
    Upload a local file to S3 and return the S3 URL
    
    Args:
        file_path: Path to the local file
        directory: Directory prefix within the S3 bucket (default: "images")
        compress: Whether to compress the file before uploading
        
    Returns:
        S3 URL if successful, file_path as fallback
    """
    if not S3_ENABLED or not s3_client:
        return file_path  # Return the local path if S3 is not enabled
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return file_path
    
    try:
        # Generate a unique filename
        filename = os.path.basename(file_path)
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create the full object key with directory prefix
        object_key = f"{directory}/{unique_filename}"
        
        # Read and potentially compress the file
        with open(file_path, 'rb') as file_obj:
            file_data = file_obj.read()
        
        if compress:
            if directory == "images" and file_extension.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                # Convert synchronous use
                img = Image.open(io.BytesIO(file_data))
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                if img.width > 1920 or img.height > 1080:
                    img.thumbnail((1920, 1080), Image.LANCZOS)
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                file_data = output.getvalue()
                content_type = 'image/jpeg'
            elif directory == "videos" and file_extension.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
                # Create temporary files for video compression
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as input_file:
                    input_file.write(file_data)
                    input_path = input_file.name
                    
                output_path = input_path + '_compressed.mp4'
                
                # Run FFmpeg compression
                cmd = [
                    'ffmpeg', '-i', input_path, 
                    '-c:v', 'libx264', '-crf', '28', 
                    '-preset', 'medium', 
                    '-c:a', 'aac', '-b:a', '128k', 
                    output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True)
                
                if result.returncode == 0:
                    with open(output_path, 'rb') as f:
                        file_data = f.read()
                    content_type = 'video/mp4'
                else:
                    print(f"FFmpeg error: {result.stderr.decode()}")
                    content_type = 'application/octet-stream'
                
                # Clean up temporary files
                try:
                    os.unlink(input_path)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except Exception as e:
                    print(f"Error cleaning up temp files: {e}")
            else:
                content_type = 'image/png' if directory == "images" else 'application/octet-stream'
        else:
            content_type = 'image/png' if directory == "images" else 'application/octet-stream'
        
        # Upload the file
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=file_data,
            ContentType=content_type
        )
        
        # Construct and return the S3 URL
        if AWS_REGION == "us-east-1":
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{object_key}"
        else:
            s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{object_key}"
        
        print(f"Successfully uploaded to S3: {s3_url}")
        return s3_url
    
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return file_path  # Return the local path as fallback 