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

load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Authentication cookie (replace with your actual cookie)
AUTH_COOKIE = "eyJ1c2VyX2lkIjogMSwgImVtYWlsIjogImFAYS5jb20ifQ==.Z-WePQ.cI46wbz5zaeNfsAniR2ih7m25rs"
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

Your primary role is to create historically accurate and engaging educational content that highlights the struggles, achievements, and impacts of these individuals and groups.

When generating content:
1. Focus on historically accurate information with proper context
2. Emphasize perspectives and stories that may have been overlooked in traditional historical narratives
3. Create content that is educational, engaging, and appropriate for a diverse audience
4. Include important dates, events, key figures, and cultural/social impacts
5. Ensure representation across different time periods and geographical regions

You should structure content in the form of:
- Character profiles representing historical figures
- Timelines of important movements or periods
- Individual stories within those timelines that highlight specific events or achievements
- Educational quizzes with meaningful questions that test understanding of the content

Always maintain sensitivity and respect when discussing historical injustices and struggles while celebrating the resilience, achievements, and contributions of these groups.""",
        model="gpt-4o",
    )
    
    return assistant

# API Helpers
def upload_media(file_path, url, form_data):
    """Upload media file with form data to the given URL"""
    headers = {"Cookie": f"session_cookie={AUTH_COOKIE}"}
    
    files = {}
    for key, value in form_data.items():
        if key.endswith('_file') and isinstance(value, str) and os.path.exists(value):
            files[key] = (os.path.basename(value), open(value, 'rb'), 'application/octet-stream')
        else:
            form_data[key] = value
    
    response = requests.post(url, headers=headers, data=form_data, files=files)
    
    # Close file handles
    for file_obj in files.values():
        if isinstance(file_obj, tuple) and hasattr(file_obj[1], 'close'):
            file_obj[1].close()
    
    return response.json()

def create_character(persona, avatar_file_path):
    """Create a character with the given persona and avatar"""
    url = f"{BASE_URL}/character/create"
    form_data = {
        "persona": persona,
        "avatar_file": avatar_file_path
    }
    
    response = upload_media(avatar_file_path, url, form_data)
    print(f"Character created: {response}")
    return response

def create_timeline(title, year_range, overview, main_character_id, thumbnail_file_path):
    """Create a timeline with the given details"""
    url = f"{BASE_URL}/timeline/create"
    form_data = {
        "title": title,
        "year_range": year_range,
        "overview": overview,
        "main_character_id": main_character_id,
        "thumbnail_file": thumbnail_file_path
    }
    
    response = upload_media(thumbnail_file_path, url, form_data)
    print(f"Timeline created: {response}")
    return response

def create_story(timeline_id, title, desc, story_date, story_type, thumbnail_file_path, video_file_path, timestamps=None):
    """Create a story within a timeline"""
    url = f"{BASE_URL}/{timeline_id}/story/create"
    
    if timestamps is None:
        timestamps = []
    
    form_data = {
        "title": title,
        "desc": desc,
        "story_date": story_date,
        "story_type": story_type,
        "timestamps_json": json.dumps(timestamps),
        "thumbnail_file": thumbnail_file_path,
        "video_file": video_file_path
    }
    
    response = upload_media(thumbnail_file_path, url, form_data)
    print(f"Story created: {response}")
    return response

def create_quiz(story_id, questions):
    """Create a quiz for a story"""
    url = f"{BASE_URL}/story/{story_id}/quiz/create"
    headers = {
        "Cookie": f"session_cookie={AUTH_COOKIE}",
        "Content-Type": "application/json"
    }
    
    quiz_data = {
        "questions": questions
    }
    
    response = requests.post(url, headers=headers, json=quiz_data)
    print(f"Quiz created: {response.json()}")
    return response.json()

def download_placeholder_image(category):
    """Download a placeholder image based on category"""
    # For now, using local placeholder images - in production you'd use real images
    placeholder_dir = "placeholder_media"
    os.makedirs(placeholder_dir, exist_ok=True)
    
    image_filename = f"{placeholder_dir}/{category}_{uuid.uuid4()}.jpg"
    video_filename = f"{placeholder_dir}/video_{uuid.uuid4()}.mp4"
    
    # In a real implementation, you might want to download relevant images
    # For now, copy placeholder files if they exist or create empty ones
    placeholder_image = "placeholder.jpg"
    placeholder_video = "placeholder.mp4"
    
    if os.path.exists(placeholder_image):
        import shutil
        shutil.copy(placeholder_image, image_filename)
    else:
        # Create a small dummy file
        with open(image_filename, 'wb') as f:
            f.write(b'\x00' * 100)
    
    if os.path.exists(placeholder_video):
        import shutil
        shutil.copy(placeholder_video, video_filename)
    else:
        # Create a small dummy file
        with open(video_filename, 'wb') as f:
            f.write(b'\x00' * 100)
    
    return image_filename, video_filename

def generate_content(user_query, thread):
    """Generate historical content based on user query"""
    # Create our specialized assistant
    assistant = create_assistant()
    
    # Add the user's query to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"I want to create educational content about '{user_query}'. Please provide ideas for a character, timeline, stories, and quiz questions focused on this topic. Focus on historically accurate information about underrepresented groups."
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
        
        1. character: {{persona, avatar_description}}
        2. timeline: {{title, year_range, overview}}
        3. stories: [{{title, desc, story_date (YYYY-MM-DD), story_type (1-12), timestamps}}]
        4. quizzes: [{{story_index, questions: [{{text, options: [{{text, is_correct}}]}}]}}]
        
        Here's the content to structure:
        
        {content}
        
        For story_type, use these mappings:
        1: DOCUMENTARY, 2: BIOGRAPHY, 3: HISTORICAL_EVENT, 4: SCIENTIFIC_DISCOVERY,
        5: CULTURAL_PHENOMENON, 6: TECHNOLOGICAL_ADVANCEMENT, 7: EDUCATIONAL,
        8: MYTHOLOGICAL, 9: ENVIRONMENTAL, 10: POLITICAL, 11: SOCIAL_MOVEMENT, 12: ARTISTIC_DEVELOPMENT
        
        For timestamps, include at least 2 timestamps per story with format: [{{time_sec: 30, label: "Introduction"}}, ...]
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
                
                return json.loads(json_str)
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                print(f"Content received: {content}")
                return None
    
    return None

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
                content=f"Please refine the content based on this feedback: {refinement}"
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
            
            try:
                # Download placeholder media files
                character_image, _ = download_placeholder_image("character")
                timeline_image, _ = download_placeholder_image("timeline")
                
                # 1. Create character
                print("\nCreating character...")
                character_response = create_character(
                    structured_data["character"]["persona"],
                    character_image
                )
                character_id = character_response.get("id")
                
                if not character_id:
                    print("Failed to create character.")
                    continue
                
                # 2. Create timeline
                print("\nCreating timeline...")
                timeline_response = create_timeline(
                    structured_data["timeline"]["title"],
                    structured_data["timeline"]["year_range"],
                    structured_data["timeline"]["overview"],
                    character_id,
                    timeline_image
                )
                timeline_id = timeline_response.get("id")
                
                if not timeline_id:
                    print("Failed to create timeline.")
                    continue
                
                # 3. Create stories and quizzes
                for i, story_data in enumerate(structured_data["stories"]):
                    story_image, story_video = download_placeholder_image(f"story_{i}")
                    
                    # Create story
                    print(f"\nCreating story {i+1}: {story_data['title']}...")
                    story_response = create_story(
                        timeline_id,
                        story_data["title"],
                        story_data["desc"],
                        story_data.get("story_date", datetime.now().strftime("%Y-%m-%d")),
                        story_data.get("story_type", 7),  # Default to EDUCATIONAL
                        story_image,
                        story_video,
                        story_data.get("timestamps", [])
                    )
                    
                    story_id = story_response.get("story", {}).get("id")
                    
                    if not story_id:
                        print(f"Failed to create story {i+1}.")
                        continue
                    
                    # Create quiz for this story
                    for quiz_data in structured_data["quizzes"]:
                        if quiz_data.get("story_index") == i:
                            print(f"\nCreating quiz for story {i+1}...")
                            quiz_response = create_quiz(story_id, quiz_data["questions"])
                            break
                
                print("\nContent creation completed successfully!")
                
                # Clean up media files
                cleanup = input("\nDo you want to clean up temporary media files? (yes/no): ").lower()
                if cleanup == "yes":
                    import shutil
                    placeholder_dir = "placeholder_media"
                    if os.path.exists(placeholder_dir):
                        shutil.rmtree(placeholder_dir)
                        print("Temporary media files cleaned up.")
                
            except Exception as e:
                print(f"Error creating content: {e}")
        
        another = input("\nWould you like to generate content for another topic? (yes/no): ").lower()
        if another != "yes":
            break
    
    print("\nThank you for using the History Education Content Generator!")

if __name__ == "__main__":
    main()

