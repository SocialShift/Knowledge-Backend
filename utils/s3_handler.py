import os
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import uuid
from pathlib import Path
from dotenv import load_dotenv

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

async def upload_file_to_s3(upload_file: UploadFile, directory: str) -> str:
    """
    Upload a file to S3 bucket and return the URL.
    
    Args:
        upload_file: The uploaded file
        directory: The directory prefix within the S3 bucket
        
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
        # Upload the file
        file_content = await upload_file.read()
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=file_content,
            ContentType=upload_file.content_type
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

async def upload_image_to_s3(image: UploadFile) -> str:
    """Upload an image to S3 and return its URL"""
    if not image:
        return None
    return await upload_file_to_s3(image, "images")

async def upload_video_to_s3(video: UploadFile) -> str:
    """Upload a video to S3 and return its URL"""
    if not video:
        return None
    return await upload_file_to_s3(video, "videos")

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