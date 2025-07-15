#!/usr/bin/env python3
"""
Migration script to give default badges to existing users.
Run this once to ensure all existing users have the default starter badges.
"""

import sys
import os

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_db, Profile
from utils.badge_utils import ensure_default_badges
from sqlalchemy.orm import Session

def migrate_default_badges():
    """Give default badges to all existing users who don't have any badges"""
    db = next(get_db())
    
    try:
        # Get all profiles
        profiles = db.query(Profile).all()
        
        print(f"Found {len(profiles)} user profiles")
        
        updated_count = 0
        for profile in profiles:
            # Ensure each user has default badges
            missing_badges = ensure_default_badges(profile.user_id, db)
            
            if missing_badges:
                print(f"User {profile.user_id} ({profile.nickname or 'No nickname'}): Added {len(missing_badges)} default badges")
                updated_count += 1
            else:
                print(f"User {profile.user_id} ({profile.nickname or 'No nickname'}): Already has default badges")
        
        print(f"\nMigration complete! Updated {updated_count} users with default badges.")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_default_badges() 