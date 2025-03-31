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

def create_story(timeline_id, title, desc, story_date, story_type, story_description, timestamps=None):
    """Create a story within a timeline with generated media"""
    url = f"{BASE_URL}/{timeline_id}/story/create"
    
    if timestamps is None:
        timestamps = []
    
    # Generate story images
    print(f"Generating image for story: {title}")
    thumbnail_file_path = generate_image(f"Historical scene depicting {story_description}")
    
    # Use the same image for video for now
    video_file_path = thumbnail_file_path
    
    form_data = {
        "title": title,
        "desc": desc,
        "story_date": story_date,
        "story_type": story_type,
        "timestamps_json": json.dumps(timestamps),
        "thumbnail_file": thumbnail_file_path,
        "video_file": video_file_path
    }
    
    response = upload_media(url, form_data)
    print(f"Story created: {response}")
    return response, thumbnail_file_path

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
1. A character profile (historical figure or composite representative)
2. A timeline with precise year range
3. At least 3 detailed stories within that timeline (each should be substantial, 5-7 paragraphs)
4. Quiz questions for each story (with 4 options per question)

Focus on historically accurate information about underrepresented groups. The content should be college-level depth and detail while remaining engaging."""
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
            "persona": "Detailed description of the historical figure",
            "avatar_description": "Description for generating an image of this character"
        }}
        
        2. timeline: {{
            "title": "Title of the timeline",
            "year_range": "YYYY-YYYY",
            "overview": "Comprehensive overview of the timeline",
            "description": "Visual description for generating an image representing this timeline"
        }}
        
        3. stories: [
            {{
                "title": "Story title",
                "desc": "Detailed story description (keep all paragraphs)",
                "story_date": "YYYY-MM-DD",
                "story_type": 1-12 (use the number),
                "description": "Visual description for generating an image representing this story",
                "timestamps": [
                    {{"time_sec": 30, "label": "Introduction"}},
                    {{"time_sec": 60, "label": "Event starts"}},
                    {{"time_sec": 120, "label": "Key moment"}},
                    {{"time_sec": 180, "label": "Conclusion"}}
                ]
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
                
                return structured_data
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
                        story_data.get("timestamps", [])
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

