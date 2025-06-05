from pathlib import Path
import os
import json
import time
import uuid
import requests
import traceback
from io import BytesIO
from PIL import Image
from pydantic import BaseModel
from openai import OpenAI
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

# Define data models
class Dialog(BaseModel):
    text: str
    tone: str
    number_id: str
    image_id: str

class Image_Data(BaseModel):
    description: str
    prompt: str
    number_id: str

class StoryResponse(BaseModel):
    steps: list[Dialog]
    full_story: str
    story_annotated: str
    images: list[Image_Data]

# Constants for system prompt
STORY_PROMPT = """
Your task is to generate script for a educational video,
You will receive a topic and you will generate a script for a video.
You will first generate the story and next the dialogs.
Next you have to generate dialogs for the video.
We are using a text to speech engine to generate audio, you can define instructions for the text to speech engine in the script.

The script should not be more than 5 minutes long.
You have to split the script into parts (i.e 5-10 sec each) as we will be putting images in between the script.
The script should be in the format of a video script.
ID is the sequence of the script.
Also in story_annotated mention the images with complete story and during which dialog (mention id) that you want to show in the video.

For images you have to generate prompt to generate the images.
First is just the name of the image.
Second is the prompt for the image.
ID is the sequence of the script must match with the dialog id.

Image ID must match with the dialog id.
"""

def generate_audio(client, file_path, prompt, tone="speak in a positive tone"):
    """Generate audio from a text prompt using OpenAI's API."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Ensure prompt is not too long
        if len(prompt) > 2000:
            prompt = prompt[:2000]

        # Generate the audio
        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="alloy",
            input=prompt,
            instructions=tone
        ) as response:
            response.stream_to_file(file_path)
        
        # Get audio duration in milliseconds
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        return len(audio)
    except Exception as e:
        print(f"Error generating audio: {e}")
        # Create an empty audio file
        empty_audio = AudioSegment.silent(duration=3000)  # 3 seconds of silence
        empty_audio.export(file_path, format="aac")
        return 3000  # Return 3000ms

def save_image(image_url, output_path):
    """Save image from URL to file."""
    try:
        # Download the image from the URL
        image_response = requests.get(image_url)
        image = Image.open(BytesIO(image_response.content))

        # Save the image to the specified output path
        image.save(output_path)
        return True
    except Exception as e:
        print(f"Error saving image: {e}")
        # Create a simple blank image
        img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
        img.save(output_path)
        return False

def generate_image(client, prompt, output_path):
    """Generate an image using DALL-E and save it to the specified path."""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        return save_image(image_url, output_path)
    except Exception as e:
        print(f"Error generating image: {e}")
        # Create a simple blank image
        img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
        img.save(output_path)
        return False

def generate_story(client, topic):
    """Generate a story about the given topic."""
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": STORY_PROMPT},
                {"role": "user", "content": topic}
            ],
            response_format=StoryResponse,
            max_tokens=2000,
        )
        
        story_dialogs = completion.choices[0].message
        
        # Check for model refusal
        if getattr(story_dialogs, 'refusal', None):
            raise Exception(f"Model refused to generate content: {story_dialogs.refusal}")
        
        return story_dialogs.parsed
    except Exception as e:
        print(f"Error generating story: {e}")
        traceback.print_exc()
        # Create a minimal fallback story
        return StoryResponse(
            steps=[
                Dialog(
                    text=f"This is a story about {topic}.",
                    tone="Informative",
                    number_id="1",
                    image_id="1"
                )
            ],
            full_story=f"This is a story about {topic}.",
            story_annotated=f"Image: 'Topic'. Prompt: 'Illustration of {topic}'",
            images=[
                Image_Data(
                    description=topic,
                    prompt=f"Educational illustration about {topic}",
                    number_id="1"
                )
            ]
        )

def create_video(client, topic, output_dir):
    """Create a video about the given topic."""
    # Create a unique ID for this story
    story_id = str(uuid.uuid4())
    story_dir = Path(output_dir) / story_id
    os.makedirs(story_dir, exist_ok=True)
    
    try:
        # Generate the story
        story = generate_story(client, topic)
        
        # Save the story to JSON
        story_json_path = story_dir / "story.json"
        with open(story_json_path, "w") as f:
            f.write(story.model_dump_json())
        
        # Save the story text
        story_text_path = story_dir / "story.txt"
        with open(story_text_path, "w") as f:
            f.write(story.full_story)
        
        # Generate images
        image_paths = []
        for image in story.images:
            image_path = story_dir / f"image-{image.number_id}.png"
            generate_image(client, image.prompt, image_path)
            image_paths.append(str(image_path))
        
        # Generate audio for each step
        audio_paths = []
        durations = []
        for step in story.steps:
            audio_path = story_dir / f"step-{step.number_id}.aac"
            duration = generate_audio(client, audio_path, step.text, step.tone)
            audio_paths.append(str(audio_path))
            durations.append(duration)
        
        # Create video clips
        video_clips = []
        for i in range(len(story.steps)):
            try:
                # Duration in seconds
                duration_sec = durations[i] / 1000
                
                # Make sure the image and audio files exist
                if not os.path.exists(image_paths[i]):
                    # Create a blank image if it doesn't exist
                    img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
                    img.save(image_paths[i])
                
                if not os.path.exists(audio_paths[i]):
                    # Create a silent audio clip if it doesn't exist
                    from pydub import AudioSegment
                    silent = AudioSegment.silent(duration=3000)
                    silent.export(audio_paths[i], format="aac")
                    duration_sec = 3
                
                # Create image clip with audio
                img_clip = ImageClip(image_paths[i]).with_duration(duration_sec)
                audio_clip = AudioFileClip(audio_paths[i])
                img_clip = img_clip.with_audio(audio_clip)
                
                video_clips.append(img_clip)
            except Exception as e:
                print(f"Error creating video clip {i}: {e}")
                # Skip this clip if there's an error
                continue
        
        # Default to at least one clip if all fail
        if not video_clips:
            # Create a default clip
            img_path = story_dir / "default.png"
            img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
            img.save(img_path)
            
            img_clip = ImageClip(str(img_path)).with_duration(3)
            video_clips = [img_clip]
        
        # Concatenate clips and create final video
        final_video = concatenate_videoclips(video_clips)
        video_output_path = story_dir / f"{story_id}.mp4"
        final_video.write_videofile(str(video_output_path), fps=24, codec="libx264", audio_codec="aac")
        
        return {
            "story_id": story_id,
            "video_path": str(video_output_path),
            "story_dir": str(story_dir),
            "story": story
        }
    except Exception as e:
        print(f"Error creating video: {e}")
        traceback.print_exc()
        from PIL import ImageDraw
        # Create a fallback video with a simple message
        fallback_path = story_dir / "fallback.png"
        img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
        draw = ImageDraw.Draw(img)
        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
            draw.text((512, 512), f"Story about {topic}", fill=(255, 255, 255), font=font, anchor="mm")
        except:
            # If font drawing fails, just save the blank image
            pass
        img.save(fallback_path)
        
        img_clip = ImageClip(str(fallback_path)).with_duration(5)
        video_output_path = story_dir / f"{story_id}.mp4"
        img_clip.write_videofile(str(video_output_path), fps=24, codec="libx264", audio_codec="aac")
        
        return {
            "story_id": story_id,
            "video_path": str(video_output_path),
            "story_dir": str(story_dir),
            "story": None
        } 