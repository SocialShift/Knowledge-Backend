from pydantic import BaseModel
from models import TimelineCategory
from openai import OpenAI
import json


class CategorySelection(BaseModel):
    categories: list[TimelineCategory]

def generate_categories(title: str, overview: str, client=None):
    if client is None:
        client = OpenAI()
        
    formatted_timeline= f"""
    Title: {title}
    Overview: {overview}
    """
    
    while True:
        response = client.responses.parse(
            model="gpt-4o",
            input=[
                {
                    "role": "system",
                    "content": "You are an expert at categories selection for a particular timeline/playbook Your task is to select categories (multiple) based out of the given timelines based on it's title and overview ",
                },
                {"role": "user", "content": formatted_timeline},
            ],
            text_format= CategorySelection 
        )
        research_paper = response.output_parsed
        print(research_paper.model_dump_json())
        
        # Extract string values from enum objects
        category_values = [category.value for category in research_paper.categories]
        
        # Ask for user confirmation
        user_confirmation = input("Are you satisfied with these categories? (yes/no): ").lower()
        if user_confirmation == "yes":
            return json.dumps(category_values)
        print("Regenerating categories...")