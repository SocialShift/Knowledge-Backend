#!/usr/bin/env python3
"""
Script to add all available badges to a specific user.
Usage: python utils/add_all_badges_to_user.py <user_id>
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import get_db, Profile
from utils.badge_utils import ALL_BADGES
from sqlalchemy.orm import Session

def add_all_badges_to_user(user_id: int):
    """Add all available badges to a specific user"""
    db = next(get_db())
    
    try:
        # Get user profile
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        
        if not profile:
            print(f"❌ User with ID {user_id} not found!")
            return
        
        print(f"👤 Found user: {profile.nickname or 'No nickname'} (ID: {user_id})")
        
        # Create all badges
        all_badges = []
        for badge in ALL_BADGES:
            earned_badge = {
                'id': badge['id'],
                'name': badge['name'],
                'path': badge['path'],
                'tier': badge['tier'],
                'description': badge['description'],
                'icon_url': badge['icon_url'],
                'earned_at': datetime.utcnow().isoformat()
            }
            all_badges.append(earned_badge)
        
        # Update user's badges
        profile.badges = all_badges
        db.commit()
        
        print(f"✅ Successfully added {len(all_badges)} badges to user {user_id}!")
        
        # Display badges by path
        badges_by_path = {}
        for badge in all_badges:
            path = badge['path']
            if path not in badges_by_path:
                badges_by_path[path] = []
            badges_by_path[path].append(badge)
        
        print("\n🏆 Badges added:")
        for path, badges in badges_by_path.items():
            print(f"\n📍 {path.upper()} PATH:")
            for badge in badges:
                print(f"  • {badge['name']} (Tier {badge['tier']}): {badge['description']}")
        
    except Exception as e:
        print(f"❌ Error adding badges: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python utils/add_all_badges_to_user.py <user_id>")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        add_all_badges_to_user(user_id)
    except ValueError:
        print("❌ Please provide a valid user ID (integer)")
        sys.exit(1) 