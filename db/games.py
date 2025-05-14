from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import sys
import os
import json
from typing import List, Optional
from sqlalchemy.orm import Session
import requests
# Add parent directory to path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from project modules
from injection import AUTH_COOKIE, BASE_URL, generate_image, upload_media
from models import Story
from schemas.games import GameOptionBase

load_dotenv()
client= OpenAI()

class GameQuestionItem(BaseModel):
    title: str
    image_url: str = None
    story_id: Optional[int] = None
    options: List[GameOptionBase]

class GameQuestionBulk(BaseModel):
    questions: List[GameQuestionItem]

def generate_game_instance(game_type_selection, story_id, db: Session):
    story = db.query(Story).filter(Story.id == story_id).first()
    
    if not story:
        return f"Story with the associated ID {story_id} not found"
    
    # Extract story details to use as context
    story_title = story.title
    story_description = story.desc
    
    print("Welcome to the Game Generator Script")
    print(f"This tool helps you create game content about '{story_title}' with game type {game_type_selection}.")

    response = client.responses.parse(
        model="gpt-4o",
        input= [
            {
                "role": "system",
                "content": f"""You are generating educational history game questions for game type {game_type_selection} about the story titled "{story_title}".

STORY CONTEXT:
{story_description}

Instructions based on game type:

GAME TYPE 1 (GUESS_THE_YEAR):
- Create 5-7 questions where users must guess the year of historical events mentioned in the story
- Each question should reference specific historical events from the story context
- Options should be different years, with only one correct year
- Make questions historically accurate and educational

GAME TYPE 2 (IMAGE_GUESS):
- Create 5-7 questions where users identify historical elements from images
- Each question title should clearly describe what historical image should be shown
- For image_url, provide a DETAILED IMAGE DESCRIPTION that will be used to generate an image
- Questions should be about identifying people, places, events, or artifacts mentioned in the story
- Make image descriptions very specific for accurate image generation

GAME TYPE 3 (FILL_IN_THE_BLANK):
- Create 5-7 fill-in-the-blank questions based on historical facts from the story
- Each question should use text similar to passages from the story
- Options should be possible words/phrases to fill that blank
- Ensure only one option correctly completes the statement

For ALL game types:
- All questions must have EXACTLY 4 options with only ONE correct answer
- Set story_id to {story_id} for all questions
- Make sure all questions are directly related to the story context provided
- Create challenging but fair questions that test understanding of the story content
"""
            }
        ],
        text_format=GameQuestionBulk
    )
    
    # Get the parsed response
    game_content = response.output_parsed
    questions = game_content.questions
    
    # If this is IMAGE_GUESS (type 2), generate images for each question
    if game_type_selection == 2:
        print("Generating images for IMAGE_GUESS game type...")
        for i, question in enumerate(questions):
            # Use the image_url field as the description for image generation
            image_description = question.image_url
            if image_description:
                try:
                    print(f"Generating image {i+1}/{len(questions)}: {question.title}")
                    # Generate the image using DALL-E through the injection module
                    # This will handle image generation, download and storage
                    image_path = generate_image(f"Historical image showing {image_description}")
                    
                    # The generate_image function already:
                    # 1. Generates the image using DALL-E
                    # 2. Downloads it
                    # 3. Saves it to a local file
                    # 4. Returns the file path
                    
                    # Just use the generated file path directly
                    question.image_url = image_path
                    print(f"✓ Image generated and saved: {image_path}")
                except Exception as e:
                    print(f"Error generating image: {e}")
                    question.image_url = None
    
    # Convert to JSON for the API
    questions_json = json.dumps([question.dict() for question in questions])
    
    url = f"{BASE_URL}/game/questions/bulk"
    headers = {"Cookie": f"session_cookie={AUTH_COOKIE}"}
    form_data = {
        "game_type": game_type_selection,
        "questions_json": questions_json
    }
     
    try:
        print(f"Sending {len(questions)} questions to API at {url}")
        response = requests.post(url, headers=headers, data=form_data)
        
        # Check response
        if response.status_code == 201:
            print("✓ Successfully created game questions!")
            api_response = response.json()
            return {
                "success": True,
                "game_type": game_type_selection,
                "questions": api_response,
                "questions_count": len(questions)
            }
        else:
            print(f"API call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return {
                "success": False,
                "game_type": game_type_selection,
                "error": response.text,
                "questions_json": questions_json
            }
    except Exception as e:
        print(f"Error sending request to API: {e}")
        return {
            "success": False,
            "game_type": game_type_selection,
            "error": str(e),
            "questions_json": questions_json
        }


if __name__ == "__main__":
    # Import inside the if block to avoid circular imports
    from db.models import get_db
    
    x1 = int(input("Enter ur GAME-TYPE \n 1.Guess The Year \n 2. Image Guess \n 3. Fill in the Blanks "))
    x2 = int(input("Enter ur story ID: "))
    
    # Get a database session
    db_session = next(get_db())
    
    try:
        result = generate_game_instance(x1, x2, db_session)
        print(result)
    finally:
        db_session.close()