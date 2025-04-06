from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path
from video_generator import create_video 

def test_video_generation():
    """Test the video generation functionality"""
    load_dotenv()
    
    # Initialize OpenAI client
    client = OpenAI()
    
    # Test topic
    topic = "Women in Science during the 20th Century"
    
    # Output directory
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Generating video about: {topic}")
    
    try:
        # Generate video
        result = create_video(client, topic, output_dir)
        
        print(f"Video generated successfully!")
        print(f"Video saved to: {result['video_path']}")
        print(f"Story ID: {result['story_id']}")
        print(f"Story directory: {result['story_dir']}")
        
        # Verify files exist
        video_path = Path(result['video_path'])
        if video_path.exists():
            print(f"Video file exists: {video_path}")
            print(f"Video file size: {video_path.stat().st_size / (1024 * 1024):.2f} MB")
        else:
            print(f"Error: Video file not found at {video_path}")
        
        # Check for story.json
        story_json_path = Path(result['story_dir']) / "story.json"
        if story_json_path.exists():
            print(f"Story JSON exists: {story_json_path}")
        else:
            print(f"Error: Story JSON not found at {story_json_path}")
        
        return True
    except Exception as e:
        print(f"Error generating video: {e}")
        return False

if __name__ == "__main__":
    test_video_generation() 