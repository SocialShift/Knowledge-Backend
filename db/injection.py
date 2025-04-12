# /api/character/create
# /api/timeline/create
# /api/{timeline}/story/create
# /api/story/{story_id}/quiz/create


from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
import json
import time
from datetime import datetime, date
import uuid
import base64
from io import BytesIO
from pathlib import Path
from video_generator import create_video

load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Authentication cookie (replace with your actual cookie)
AUTH_COOKIE = "eyJ1c2VyX2lkIjogOCwgImVtYWlsIjogIm5qbmF5YW4yMjJAZ21haWwuY29tIn0=.Z_qPEA.6TzWm-nPCJR4Ug3HD-xskn9KnK8"
BASE_URL = "https://knowledge-backend-rqya.onrender.com/api"

# Thread management
def get_or_create_thread():
    thread_id_file = "thread_id.txt"
    
    if os.path.exists(thread_id_file):
        with open(thread_id_file, "r") as file:
            thread_id = file.read().strip()
        # Retrieve the existing thread
        try:
            thread = client.beta.threads.retrieve(thread_id=thread_id)
            return thread
        except:
            # If thread retrieval fails, create a new one
            pass
    
    # Create a new thread and save its ID
    thread = client.beta.threads.create()
    with open(thread_id_file, "w") as file:
        file.write(thread.id)
    
    return thread

def create_assistant():
    """Create an assistant specialized in historical content about underrepresented groups"""
    assistant = client.beta.assistants.create(
        name="History Education Content Creator",
        instructions="""You are a specialized assistant for an educational history application focused on the stories and contributions of underrepresented groups throughout history, including women, Black individuals, LGBTQ+ people, indigenous populations, and other marginalized communities.

Your primary role is to create historically accurate, engaging, and HIGHLY DETAILED educational content that highlights the struggles, achievements, and impacts of these individuals and groups.

When generating content:
1. Focus on historically accurate information with proper context and deep detail
2. Emphasize perspectives and stories that may have been overlooked in traditional historical narratives
3. Create content that is educational, engaging, and appropriate for a diverse audience
4. Include important dates, events, key figures, and cultural/social impacts with rich context
5. Ensure representation across different time periods and geographical regions
6. Provide EXTENSIVE descriptions and narratives - each story should be comprehensive, at least 5-7 paragraphs, with rich supporting details

You should structure content in the form of:
- Character profiles representing historical figures with detailed biographies and contributions
- Timelines of important movements or periods with precise date ranges
- Individual stories within those timelines that highlight specific events or achievements with rich narrative
- Educational quizzes with meaningful questions that test understanding of the content

Each story must be SUBSTANTIVE and COMPREHENSIVE. Think of creating college-level educational material that provides a thorough understanding of the subject matter.

Always maintain sensitivity and respect when discussing historical injustices and struggles while celebrating the resilience, achievements, and contributions of these groups.

For quizzes, always create exactly 4 options for each question, with only one correct answer.""",
        model="gpt-4o",
    )
    
    return assistant

def generate_image(prompt, size="1024x1024"):
    """Generate an image using DALL-E 3 based on the description"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Create a historically accurate, detailed educational image related to: {prompt}. The image should be high quality, realistic, and appropriate for an educational platform about history.",
            size=size,
            quality="standard",
            n=1,
        )
        
        # Save the image to a file
        image_url = response.data[0].url
        
        # Download the image
        image_response = requests.get(image_url)
        
        # Create directory if it doesn't exist
        image_dir = "generated_media"
        os.makedirs(image_dir, exist_ok=True)
        
        # Save to file
        image_filename = f"{image_dir}/{uuid.uuid4()}.png"
        with open(image_filename, "wb") as f:
            f.write(image_response.content)
        
        return image_filename
    except Exception as e:
        print(f"Error generating image: {e}")
        # Fall back to placeholder if image generation fails
        return create_placeholder_image()

def create_placeholder_image():
    """Create a placeholder image if DALL-E fails"""
    image_dir = "generated_media"
    os.makedirs(image_dir, exist_ok=True)
    
    # Create a small dummy file
    image_filename = f"{image_dir}/placeholder_{uuid.uuid4()}.jpg"
    with open(image_filename, 'wb') as f:
        f.write(b'\x00' * 100)
    
    return image_filename

# API Helpers
def upload_media(url, form_data):
    """Upload media file with form data to the given URL"""
    headers = {"Cookie": f"session_cookie={AUTH_COOKIE}"}
    
    files = {}
    for key, value in form_data.items():
        if key.endswith('_file') and isinstance(value, str) and os.path.exists(value):
            files[key] = (os.path.basename(value), open(value, 'rb'), 'application/octet-stream')
        else:
            if key not in files:  # Avoid duplicate keys
                form_data[key] = value
    
    response = requests.post(url, headers=headers, data=form_data, files=files)
    
    # Close file handles
    for file_obj in files.values():
        if isinstance(file_obj, tuple) and hasattr(file_obj[1], 'close'):
            file_obj[1].close()
    
    return response.json()

def create_character(persona, avatar_description):
    """Create a character with the given persona and generated avatar"""
    url = f"{BASE_URL}/character/create"
    
    # Enforce brevity in persona
    words = persona.split()
    if len(words) > 7:
        persona = " ".join(words[:7])
        print("Character persona trimmed to ensure brevity.")
    
    # Generate character image using DALL-E
    print(f"Generating image for character: {persona}")
    avatar_file_path = generate_image(f"Historical portrait of {avatar_description}")
    
    form_data = {
        "persona": persona,
        "avatar_file": avatar_file_path
    }
    
    response = upload_media(url, form_data)
    print(f"Character created: {response}")
    return response, avatar_file_path

def create_timeline(title, year_range, overview, main_character_id, timeline_description):
    """Create a timeline with the given details and generated thumbnail"""
    url = f"{BASE_URL}/timeline/create"
    
    # Enforce brevity in title
    words = title.split()
    if len(words) > 5:
        title = " ".join(words[:5])
        print("Timeline title trimmed to ensure brevity.")
    
    # Generate timeline image
    print(f"Generating image for timeline: {title}")
    thumbnail_file_path = generate_image(f"Historical representation of {timeline_description} during {year_range}")
    
    form_data = {
        "title": title,
        "year_range": year_range,
        "overview": overview,
        "main_character_id": main_character_id,
        "thumbnail_file": thumbnail_file_path
    }
    
    response = upload_media(url, form_data)
    print(f"Timeline created: {response}")
    return response, thumbnail_file_path

def create_story(timeline_id, title, desc, story_date, story_type, story_description, timestamps=None, generate_video=True):
    """Create a story within a timeline with generated media"""
    url = f"{BASE_URL}/{timeline_id}/story/create"
    
    # Enforce brevity in title
    words = title.split()
    if len(words) > 5:
        title = " ".join(words[:5])
        print("Story title trimmed to ensure brevity.")
    
    if timestamps is None:
        timestamps = []
    
    # Handle BCE/BC dates by converting to a standard format
    if isinstance(story_date, str) and ('BCE' in story_date.upper() or 'BC' in story_date.upper()):
        print(f"Converting BCE/BC date: {story_date}")
        # Extract year and convert BCE/BC to CE/AD format (use a placeholder date)
        try:
            # Check if it's a range
            if '-' in story_date:
                # Just use the later date in the range
                parts = story_date.split('-')
                year_part = parts[-1].strip()
            else:
                year_part = story_date
                
            # Remove BCE/BC and extract the year
            year_part = year_part.upper().replace('BCE', '').replace('BC', '').strip()
            
            # Use January 1st of the year as a standard date
            story_date = f"0001-01-01"  # Default to year 1 CE/AD
            print(f"Converted date to standard format: {story_date}")
        except Exception as e:
            print(f"Error converting BCE/BC date: {e}")
            story_date = "0001-01-01"  # Default to year 1 CE/AD
    
    # Generate media for the story
    thumbnail_file_path = None
    video_file_path = None
    
    if generate_video:
        # Create video content instead of just an image
        print(f"Generating video for story: {title}")
        # Use our new video generator to create a complete video
        video_dir = "generated_media/videos"
        os.makedirs(video_dir, exist_ok=True)
        
        try:
            # Generate video and associated content
            video_result = create_video(client, story_description, video_dir)
            video_file_path = video_result["video_path"]
            
            # Get the first image to use as thumbnail
            story_dir = Path(video_result["story_dir"])
            thumbnail_file_path = list(story_dir.glob("image-1.png"))[0]
            
            if not os.path.exists(thumbnail_file_path):
                # Fallback to generating an image if needed
                thumbnail_file_path = generate_image(f"Historical scene depicting {story_description}")
            
            # Generate dynamic timestamps based on video content
            if not timestamps:  # Only generate if timestamps are not already provided
                timestamps = generate_timestamps_from_video(video_result)
        except Exception as e:
            print(f"Error creating video: {e}")
            # Fallback to just generating image
            thumbnail_file_path = generate_image(f"Historical scene depicting {story_description}")
            video_file_path = thumbnail_file_path
    else:
        # Just generate an image
        print(f"Generating image for story: {title}")
        thumbnail_file_path = generate_image(f"Historical scene depicting {story_description}")
        video_file_path = thumbnail_file_path  # Use the same image for video placeholder
        # No timestamps for image-only
        timestamps = []
    
    form_data = {
        "title": title,
        "desc": desc,
        "story_date": story_date,
        "story_type": story_type,
        "timestamps_json": json.dumps(timestamps),
        "thumbnail_file": str(thumbnail_file_path),
        "video_file": str(video_file_path)
    }
    
    response = upload_media(url, form_data)
    print(f"Story created: {response}")
    return response, video_file_path

def generate_timestamps_from_video(video_result):
    """Generate meaningful timestamps based on the video content"""
    timestamps = []
    
    try:
        # Get story data from the video result
        story = video_result.get("story")
        if not story:
            return default_timestamps()
        
        # Get steps from the story
        steps = []
        try:
            steps = story.steps  # Try accessing steps directly (if story is StoryResponse object)
        except AttributeError:
            # If story is a dict, not an object
            if isinstance(story, dict) and "steps" in story:
                steps = story["steps"]
        
        if not steps:
            return default_timestamps()
        
        # Calculate audio durations and timestamps
        durations_ms = []
        cumulative_time = 0
        
        # Calculate audio durations
        for i, step in enumerate(steps):
            try:
                # Get step ID (handle both object and dict formats)
                if isinstance(step, dict):
                    step_id = step.get("number_id", str(i+1))
                else:
                    step_id = getattr(step, "number_id", str(i+1))
                
                # Try to get actual audio file duration
                from pydub import AudioSegment
                audio_path = Path(video_result["story_dir"]) / f"step-{step_id}.mp3"
                if audio_path.exists():
                    audio = AudioSegment.from_file(str(audio_path))
                    duration_ms = len(audio)
                else:
                    # Default duration if audio file doesn't exist
                    duration_ms = 3000  # 3 seconds
                
                durations_ms.append(duration_ms)
                
                # Create a timestamp at the start of each segment
                # Ensure time_sec is at least 1 (not 0)
                time_sec = max(1, int(cumulative_time / 1000))
                
                # Get step text (handle both object and dict formats)
                if isinstance(step, dict):
                    step_text = step.get("text", f"Part {i+1}")
                else:
                    step_text = getattr(step, "text", f"Part {i+1}")
                
                # Get a descriptive label from the step content
                if i == 0:
                    label = "Introduction"
                elif i == len(steps) - 1:
                    label = "Conclusion"
                else:
                    # Extract a short phrase from the beginning of the step text
                    words = step_text.split()
                    label_words = words[:3] if len(words) > 3 else words
                    label = " ".join(label_words) + "..."
                
                timestamps.append({
                    "time_sec": time_sec,
                    "label": label
                })
                
                cumulative_time += duration_ms
                
            except Exception as e:
                print(f"Error calculating timestamp for step {i}: {e}")
                continue
        
        # Add a final timestamp if not already at the end
        if cumulative_time > 0:
            total_seconds = max(1, int(cumulative_time / 1000))
            if not any(ts["time_sec"] == total_seconds for ts in timestamps):
                timestamps.append({
                    "time_sec": total_seconds,
                    "label": "End"
                })
        
        return timestamps if timestamps else default_timestamps()
    
    except Exception as e:
        print(f"Error generating timestamps: {e}")
        return default_timestamps()

def default_timestamps():
    """Return default timestamps if dynamic generation fails"""
    return [
        {"time_sec": 1, "label": "Introduction"},
        {"time_sec": 30, "label": "Main Content"},
        {"time_sec": 60, "label": "Conclusion"}
    ]

def create_quiz(story_id, questions):
    """Create a quiz for a story"""
    url = f"{BASE_URL}/story/{story_id}/quiz/create"
    headers = {
        "Cookie": f"session_cookie={AUTH_COOKIE}",
        "Content-Type": "application/json"
    }
    
    # Ensure each question has exactly 4 options
    validated_questions = []
    for question in questions:
        # If there are fewer than 4 options, add dummy options
        options = question.get('options', [])
        while len(options) < 4:
            options.append({
                "text": f"Option {len(options) + 1}",
                "is_correct": False
            })
        
        # If there are more than 4 options, trim to 4, keeping the correct one
        if len(options) > 4:
            # Find the correct option
            correct_option = next((opt for opt in options if opt.get('is_correct', False)), None)
            
            # Select 3 incorrect options
            incorrect_options = [opt for opt in options if not opt.get('is_correct', False)][:3]
            
            # Combine correct and incorrect options
            options = incorrect_options + [correct_option] if correct_option else incorrect_options[:4]
        
        validated_questions.append({
            "text": question.get('text', ""),
            "options": options
        })
    
    quiz_data = {
        "story_id": story_id,  # Add the story_id to the request body
        "questions": validated_questions
    }
    
    try:
        response = requests.post(url, headers=headers, json=quiz_data)
        response_json = response.json()
        print(f"Quiz created: {response_json}")
        return response_json
    except Exception as e:
        print(f"Error creating quiz: {e}")
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        return {"error": str(e)}

def generate_content(user_query, thread):
    """Generate historical content based on user query"""
    # Create our specialized assistant
    assistant = create_assistant()
    
    # Add the user's query to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"""I want to create detailed, comprehensive educational content about '{user_query}' for our history education platform. 

Please provide extensive, richly detailed ideas for:
1. A character profile (historical figure or composite representative) with a VERY BRIEF persona description (3-5 words)
2. A timeline with a VERY BRIEF title (3-5 words) and precise year range
3. At least 3 detailed stories within that timeline (each should be substantial, 5-7 paragraphs) with VERY BRIEF titles (3-5 words)
4. Quiz questions for each story (with 4 options per question)

Each story should include a detailed visual description that can be used to generate either an image or a short video.

Focus on historically accurate information about underrepresented groups. The content should be college-level depth and detail while remaining engaging.

IMPORTANT: All titles and persona descriptions MUST be extremely concise (max 5-7 words)."""
    )
    
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    
    # Wait for the run to complete
    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        print(f"Run status: {run.status}")
        if run.status in ["failed", "cancelled", "expired"]:
            raise Exception(f"Run failed with status {run.status}")
    
    # Get the assistant's response
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )
    
    # The latest message should be from the assistant
    for msg in messages.data:
        if msg.role == "assistant":
            content = ''.join([part.text.value for part in msg.content if hasattr(part, 'text')])
            return content
    
    return "No response from assistant"

def process_content(content):
    """Process the generated content into structured data"""
    # Ask the assistant to structure the data
    thread = get_or_create_thread()
    
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"""Please structure the following content into a JSON format with these keys:
        
        1. character: {{
            "persona": "BRIEF description of the historical figure (max 5-7 words)",
            "avatar_description": "Description for generating an image of this character"
        }}
        
        2. timeline: {{
            "title": "BRIEF title of the timeline (max 3-5 words)",
            "year_range": "YYYY-YYYY",
            "overview": "Comprehensive overview of the timeline",
            "description": "Visual description for generating an image representing this timeline"
        }}
        
        3. stories: [
            {{
                "title": "BRIEF story title (max 3-5 words)",
                "desc": "Detailed story description (keep all paragraphs)",
                "story_date": "YYYY-MM-DD",
                "story_type": 1-12 (use the number),
                "description": "Visual description for generating an image representing this story"
            }}
        ]
        
        4. quizzes: [
            {{
                "story_index": 0, (0-based index matching the stories array)
                "questions": [
                    {{
                        "text": "Question text?",
                        "options": [
                            {{"text": "Option 1", "is_correct": true}},
                            {{"text": "Option 2", "is_correct": false}},
                            {{"text": "Option 3", "is_correct": false}},
                            {{"text": "Option 4", "is_correct": false}}
                        ]
                    }}
                ]
            }}
        ]
        
        Here's the content to structure:
        
        {content}
        
        For story_type, use these mappings:
        1: DOCUMENTARY, 2: BIOGRAPHY, 3: HISTORICAL_EVENT, 4: SCIENTIFIC_DISCOVERY,
        5: CULTURAL_PHENOMENON, 6: TECHNOLOGICAL_ADVANCEMENT, 7: EDUCATIONAL,
        8: MYTHOLOGICAL, 9: ENVIRONMENTAL, 10: POLITICAL, 11: SOCIAL_MOVEMENT, 12: ARTISTIC_DEVELOPMENT
        
        IMPORTANT: 
        1. Each question MUST have EXACTLY 4 options
        2. Each story MUST have a corresponding quiz in the quizzes array
        3. Preserve all paragraph breaks and formatting in the descriptions
        4. Add an appropriate image description for each element
        5. KEEP ALL TITLES AND PERSONA DESCRIPTIONS EXTREMELY BRIEF (3-5 words)
        6. For story_date, use EXACTLY the format YYYY-MM-DD (example: 1963-08-28)
           - For ancient/BCE dates, use 0001-01-01 as a placeholder
           - For date ranges or uncertain dates, pick a specific representative date
        """
    )
    
    # Create our specialized assistant
    assistant = create_assistant()
    
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    
    # Wait for the run to complete
    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        print(f"Run status: {run.status}")
        if run.status in ["failed", "cancelled", "expired"]:
            raise Exception(f"Run failed with status {run.status}")
    
    # Get the assistant's response
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )
    
    # The latest message should be from the assistant
    for msg in messages.data:
        if msg.role == "assistant":
            content = ''.join([part.text.value for part in msg.content if hasattr(part, 'text')])
            
            # Extract JSON from the content
            try:
                # Find JSON content between triple backticks
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find any JSON-like content
                    json_match = re.search(r'(\{[\s\S]*\})', content)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        raise ValueError("Could not find JSON content in response")
                
                structured_data = json.loads(json_str)
                
                # Validate each quiz has exactly 4 options
                for quiz in structured_data.get("quizzes", []):
                    for question in quiz.get("questions", []):
                        options = question.get("options", [])
                        if len(options) != 4:
                            print(f"Warning: Question '{question.get('text')}' has {len(options)} options instead of 4")
                            # Add dummy options if needed
                            while len(options) < 4:
                                options.append({
                                    "text": f"Option {len(options) + 1}",
                                    "is_correct": False
                                })
                            # Trim if too many
                            if len(options) > 4:
                                has_correct = any(opt.get("is_correct", False) for opt in options[:4])
                                if not has_correct:
                                    # Make sure we have one correct option
                                    options[0]["is_correct"] = True
                                options = options[:4]
                            question["options"] = options
                
                # Apply validation for title/persona brevity
                structured_data = validate_structured_data(structured_data)
                
                return structured_data
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                print(f"Content received: {content}")
                return None
    
    return None

def validate_structured_data(structured_data):
    """Validates that titles and personas are appropriately brief"""
    modified = False
    
    # Check and trim character persona
    if "character" in structured_data and "persona" in structured_data["character"]:
        persona = structured_data["character"]["persona"]
        words = persona.split()
        if len(words) > 7:
            structured_data["character"]["persona"] = " ".join(words[:7])
            modified = True
    
    # Check and trim timeline title
    if "timeline" in structured_data and "title" in structured_data["timeline"]:
        title = structured_data["timeline"]["title"]
        words = title.split()
        if len(words) > 5:
            structured_data["timeline"]["title"] = " ".join(words[:5])
            modified = True
    
    # Check and trim story titles
    if "stories" in structured_data:
        for story in structured_data["stories"]:
            if "title" in story:
                title = story["title"]
                words = title.split()
                if len(words) > 5:
                    story["title"] = " ".join(words[:5])
                    modified = True
            
            # Ensure story_date is in a valid format
            if "story_date" in story:
                # Check for BCE/BC dates and provide a fallback
                if isinstance(story["story_date"], str) and ('BCE' in story["story_date"].upper() or 'BC' in story["story_date"].upper()):
                    print(f"Converting BCE/BC date in structured data: {story['story_date']}")
                    # Default to a standard date format
                    story["story_date"] = "0001-01-01"
                    modified = True
                
                # Ensure it follows YYYY-MM-DD format
                try:
                    # Try to parse the date
                    parsed_date = datetime.strptime(story["story_date"], "%Y-%m-%d")
                    # Reformat to ensure consistency
                    story["story_date"] = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    # If parsing fails, default to a safe date
                    print(f"Invalid date format in structured data: {story['story_date']}")
                    story["story_date"] = "0001-01-01"
                    modified = True
    
    if modified:
        print("Some content was modified to ensure compatibility with the API.")
    return structured_data

def main():
    """Main function to run the content generation workflow"""
    print("Welcome to the History Education Content Generator!")
    print("This tool helps you create educational content about underrepresented groups in history.")
    
    # Get or create a thread for the conversation
    thread = get_or_create_thread()
    
    while True:
        user_query = input("\nWhat historical topic would you like to generate content for? (e.g., 'Black Women in Science', 'LGBTQ+ Rights Movement'): ")
        
        if not user_query:
            print("Please enter a valid topic.")
            continue
        
        # Ask user if they want to generate videos
        generate_videos = input("Would you like to generate videos for the stories? (yes/no): ").lower() == "yes"
        if generate_videos:
            print("Videos will be generated for each story.")
        else:
            print("Only images will be generated for the stories (no videos).")
        
        print("\nGenerating content ideas based on your topic...")
        content = generate_content(user_query, thread)
        
        print("\n=== Generated Content Ideas ===")
        print(content)
        print("=============================\n")
        
        proceed = input("Would you like to refine this content or proceed with creating it? (refine/proceed): ").lower()
        
        while proceed == "refine":
            refinement = input("\nWhat specific changes would you like to make? ")
            
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Please refine the content based on this feedback: {refinement}. Remember to keep all titles and persona descriptions EXTREMELY BRIEF (max 5-7 words)."
            )
            
            assistant = create_assistant()
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            print("Processing refinement...")
            
            while run.status != "completed":
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Run failed with status {run.status}")
            
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant":
                    content = ''.join([part.text.value for part in msg.content if hasattr(part, 'text')])
                    break
            
            print("\n=== Refined Content ===")
            print(content)
            print("=======================\n")
            
            proceed = input("Would you like to refine this content further or proceed with creating it? (refine/proceed): ").lower()
        
        if proceed == "proceed":
            print("\nProcessing content into structured format...")
            structured_data = process_content(content)
            
            if not structured_data:
                print("Failed to structure the content. Please try again.")
                continue
            
            print("\n=== Structured Content ===")
            print(json.dumps(structured_data, indent=2))
            print("=========================\n")
            
            create_confirm = input("Confirm creation of this content? (yes/no): ").lower()
            
            if create_confirm != "yes":
                print("Content creation cancelled.")
                continue
            
            print("\nCreating content in the system...")
            
            created_files = []
            try:
                # 1. Create character
                print("\nCreating character...")
                character_response, character_image = create_character(
                    structured_data["character"]["persona"],
                    structured_data["character"]["avatar_description"]
                )
                created_files.append(character_image)
                
                character_id = character_response.get("id")
                if not character_id:
                    print("Failed to create character.")
                    continue
                
                # 2. Create timeline
                print("\nCreating timeline...")
                timeline_response, timeline_image = create_timeline(
                    structured_data["timeline"]["title"],
                    structured_data["timeline"]["year_range"],
                    structured_data["timeline"]["overview"],
                    character_id,
                    structured_data["timeline"]["description"]
                )
                created_files.append(timeline_image)
                
                timeline_id = timeline_response.get("id")
                if not timeline_id:
                    print("Failed to create timeline.")
                    continue
                
                # 3. Create stories and quizzes
                for i, story_data in enumerate(structured_data["stories"]):
                    # Create story
                    print(f"\nCreating story {i+1}: {story_data['title']}...")
                    story_response, story_image = create_story(
                        timeline_id,
                        story_data["title"],
                        story_data["desc"],
                        story_data.get("story_date", datetime.now().strftime("%Y-%m-%d")),
                        story_data.get("story_type", 7),  # Default to EDUCATIONAL
                        story_data["description"],
                        story_data.get("timestamps", []),
                        generate_video=generate_videos  # Pass the video generation flag
                    )
                    created_files.append(story_image)
                    
                    # Extract story ID directly from the response
                    story_id = None
                    if isinstance(story_response, dict) and "story" in story_response:
                        story_id = story_response["story"].get("id")
                    
                    if not story_id:
                        print(f"Failed to create story {i+1} or extract story ID.")
                        print(f"Story response: {story_response}")
                        continue
                    
                    # Find corresponding quiz for this story
                    matching_quizzes = [q for q in structured_data["quizzes"] if q.get("story_index") == i]
                    
                    if matching_quizzes:
                        # Create quiz for this story
                        print(f"\nCreating quiz for story {i+1} (ID: {story_id})...")
                        quiz_response = create_quiz(story_id, matching_quizzes[0]["questions"])
                    else:
                        print(f"No quiz found for story index {i}")
                
                print("\nContent creation completed successfully!")
                
                # Clean up media files
                cleanup = input("\nDo you want to clean up generated media files? (yes/no): ").lower()
                if cleanup == "yes":
                    for file in created_files:
                        if os.path.exists(file):
                            os.remove(file)
                    print("Generated media files cleaned up.")
                
            except Exception as e:
                print(f"Error creating content: {e}")
        
        another = input("\nWould you like to generate content for another topic? (yes/no): ").lower()
        if another != "yes":
            break
    
    print("\nThank you for using the History Education Content Generator!")

if __name__ == "__main__":
    main()

