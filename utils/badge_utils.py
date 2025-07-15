from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from db.models import Profile, UserStoryView, UserTimelineView, QuizAttempt, StandAloneGameAttempt, User
from sqlalchemy import func, text

# Badge path constants
BADGE_PATH_ILLUMINATION = 'illumination'
BADGE_PATH_GAME = 'game'
BADGE_PATH_REFLECTION = 'reflection'
BADGE_PATH_ALLYSHIP = 'allyship'
BADGE_PATH_STREAK = 'streak'

# Illumination Path Badge Definitions
ILLUMINATION_BADGES = [
    {
        'id': 'spark',
        'name': 'Spark',
        'path': BADGE_PATH_ILLUMINATION,
        'tier': '1',
        'criteria': {'stories_completed': 3},
        'description': "You've taken the first step into untold truths",
        'icon_url': 'media/badges/spark.png'
    },
    {
        'id': 'candlebearer',
        'name': 'Candlebearer',
        'path': BADGE_PATH_ILLUMINATION,
        'tier': '2',
        'criteria': {'stories_completed': 10},
        'description': "You're starting to light the darkness with knowledge",
        'icon_url': 'media/badges/candlebearer.png'
    },
    {
        'id': 'torchbearer',
        'name': 'Torchbearer',
        'path': BADGE_PATH_ILLUMINATION,
        'tier': '3',
        'criteria': {'stories_completed': 25},
        'description': "You carry the truth forward, one story at a time",
        'icon_url': 'media/badges/torchbearer.png'
    },
    {
        'id': 'flamekeeper',
        'name': 'Flamekeeper',
        'path': BADGE_PATH_ILLUMINATION,
        'tier': '4',
        'criteria': {'stories_completed': 50, 'timelines_completed': 2},
        'description': "You protect what others tried to extinguish",
        'icon_url': 'media/badges/flamekeeper.png'
    },
    {
        'id': 'beacon',
        'name': 'Beacon',
        'path': BADGE_PATH_ILLUMINATION,
        'tier': '5',
        'criteria': {'stories_completed': 100, 'timelines_completed': 5},
        'description': "You shine so others can see. Your knowledge guides generations",
        'icon_url': 'media/badges/beacon.png'
    },
    {
        'id': 'constellation',
        'name': 'Constellation',
        'path': BADGE_PATH_ILLUMINATION,
        'tier': '6',
        'criteria': {'timelines_completed_across_categories': 3},
        'description': "You've connected erased histories across communities",
        'icon_url': 'media/badges/constellation.png'
    }
]

# Game Badge Definitions
GAME_BADGES = [
    {
        'id': 'uncover',
        'name': 'Uncover',
        'path': BADGE_PATH_GAME,
        'tier': '1',
        'criteria': {'games_played': 1},
        'description': "Play 1 game of any type",
        'icon_url': 'media/badges/uncover.png'
    },
    {
        'id': 'seeker',
        'name': 'Seeker',
        'path': BADGE_PATH_GAME,
        'tier': '2',
        'criteria': {'game_types_played': 3},
        'description': "Play 3 different game types",
        'icon_url': 'media/badges/seeker.png'
    },
    {
        'id': 'revealer',
        'name': 'Revealer',
        'path': BADGE_PATH_GAME,
        'tier': '3',
        'criteria': {'high_score_games': 3},
        'description': "Score 80%+ on 3 games",
        'icon_url': 'media/badges/revealer.png'
    },
    {
        'id': 'historian',
        'name': 'Historian',
        'path': BADGE_PATH_GAME,
        'tier': '4',
        'criteria': {'games_played': 10},
        'description': "Play 10 total games",
        'icon_url': 'media/badges/historian.png'
    },
    {
        'id': 'archivist',
        'name': 'Archivist',
        'path': BADGE_PATH_GAME,
        'tier': '5',
        'criteria': {'challenge_sets_completed': 1},
        'description': "Complete all games in a challenge set",
        'icon_url': 'media/badges/archivist.png'
    }
]

# Streak Badge Definitions
STREAK_BADGES = [
    {
        'id': 'ember',
        'name': 'Ember',
        'path': BADGE_PATH_STREAK,
        'tier': '1',
        'criteria': {'streak_days': 3},
        'description': "3-day streak",
        'icon_url': 'media/badges/ember.png'
    },
    {
        'id': 'flame',
        'name': 'Flame',
        'path': BADGE_PATH_STREAK,
        'tier': '2',
        'criteria': {'streak_days': 7},
        'description': "7-day streak",
        'icon_url': 'media/badges/flame.png'
    },
    {
        'id': 'inferno',
        'name': 'Inferno',
        'path': BADGE_PATH_STREAK,
        'tier': '3',
        'criteria': {'streak_days': 30},
        'description': "30-day streak",
        'icon_url': 'media/badges/inferno.png'
    },
    {
        'id': 'eternal_flame',
        'name': 'Eternal Flame',
        'path': BADGE_PATH_STREAK,
        'tier': '4',
        'criteria': {'streak_days': 90},
        'description': "90-day streak",
        'icon_url': 'media/badges/eternal_flame.png'
    }
]

# Default starter badges that everyone gets
DEFAULT_BADGES = [
    {
        'id': 'truth_seeker',
        'name': 'Truth Seeker',
        'path': 'starter',
        'tier': '0',
        'criteria': {},  # No criteria - given by default
        'description': "Welcome to Knowledge. Your journey to uncover hidden truths begins now.",
        'icon_url': 'media/badges/truth_seeker.png'
    },
    {
        'id': 'first_step',
        'name': 'First Step',
        'path': 'starter',
        'tier': '0',
        'criteria': {},  # No criteria - given by default
        'description': "Every journey begins with a single step. You've taken yours.",
        'icon_url': 'media/badges/first_step.png'
    }
]

# All badges combined
ALL_BADGES = ILLUMINATION_BADGES + GAME_BADGES + STREAK_BADGES + DEFAULT_BADGES

def get_user_progress(user_id: int, db: Session) -> Dict[str, Any]:
    """Calculate user progress for badge evaluation"""
    
    # Get stories completed
    stories_completed = db.query(UserStoryView).filter(
        UserStoryView.user_id == user_id,
        UserStoryView.is_seen == True
    ).count()
    
    # Get timelines completed (assuming a timeline is completed when all its stories are viewed)
    timelines_completed_query = text("""
        SELECT COUNT(DISTINCT t.id) as timeline_count
        FROM timelines t
        WHERE t.id IN (
            SELECT DISTINCT s.timeline_id
            FROM stories s
            WHERE s.timeline_id = t.id
            AND NOT EXISTS (
                SELECT 1 FROM stories s2
                WHERE s2.timeline_id = t.id
                AND s2.id NOT IN (
                    SELECT story_id FROM user_story_views
                    WHERE user_id = :user_id AND is_seen = true
                )
            )
        )
    """)
    
    timelines_completed = db.execute(timelines_completed_query, {"user_id": user_id}).scalar() or 0
    
    # Get games played
    games_played = db.query(StandAloneGameAttempt).filter(
        StandAloneGameAttempt.user_id == user_id
    ).count()
    
    # Get high score games (80%+ correct)
    high_score_games = db.query(StandAloneGameAttempt).filter(
        StandAloneGameAttempt.user_id == user_id,
        StandAloneGameAttempt.is_correct == True
    ).count()
    
    # Get different game types played
    game_types_played = db.query(func.count(func.distinct(text('sg.game_type')))).select_from(
        text('stand_alone_game_attempts sa JOIN stand_alone_game_questions sg ON sa.game_id = sg.id')
    ).filter(text('sa.user_id = :user_id')).params(user_id=user_id).scalar() or 0
    
    # Get current streak
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    current_streak = profile.current_login_streak if profile else 0
    
    # Get completed quizzes
    quizzes_completed = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.completed == True
    ).count()
    
    return {
        'stories_completed': stories_completed,
        'timelines_completed': timelines_completed,
        'games_played': games_played,
        'high_score_games': high_score_games,
        'game_types_played': game_types_played,
        'streak_days': current_streak,
        'quizzes_completed': quizzes_completed,
        'timelines_completed_across_categories': 0,  # TODO: Implement category tracking
        'challenge_sets_completed': 0  # TODO: Implement challenge set tracking
    }

def get_user_badges(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """Get all badges earned by a user"""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile or not profile.badges:
        return []
    
    return profile.badges

def check_badge_earned(badge: Dict[str, Any], progress: Dict[str, Any]) -> bool:
    """Check if a badge has been earned based on user progress"""
    criteria = badge['criteria']
    
    for key, required_value in criteria.items():
        if progress.get(key, 0) < required_value:
            return False
    
    return True

def check_badge_retention(badge: Dict[str, Any], user_id: int, db: Session) -> bool:
    """Check if user maintains badge retention requirements"""
    
    # Only apply retention to Illumination and Game badges
    if badge['path'] not in [BADGE_PATH_ILLUMINATION, BADGE_PATH_GAME]:
        return True
    
    # Check if user has qualifying activity in the last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # Check for story completion
    recent_story_views = db.query(UserStoryView).filter(
        UserStoryView.user_id == user_id,
        UserStoryView.viewed_at >= seven_days_ago
    ).count()
    
    # Check for timeline completion
    recent_timeline_views = db.query(UserTimelineView).filter(
        UserTimelineView.user_id == user_id,
        UserTimelineView.viewed_at >= seven_days_ago
    ).count()
    
    # Check for quiz completion
    recent_quiz_completion = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.completed_at >= seven_days_ago
    ).count()
    
    # Check for game completion
    recent_game_attempts = db.query(StandAloneGameAttempt).filter(
        StandAloneGameAttempt.user_id == user_id,
        StandAloneGameAttempt.created_at >= seven_days_ago
    ).count()
    
    return (recent_story_views + recent_timeline_views + recent_quiz_completion + recent_game_attempts) > 0

def update_user_badges(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """Update user badges based on current progress and return newly earned badges"""
    
    # Get current progress
    progress = get_user_progress(user_id, db)
    
    # Get current badges
    current_badges = get_user_badges(user_id, db)
    current_badge_ids = {badge['id'] for badge in current_badges}
    
    # Get user profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        return []
    
    newly_earned_badges = []
    updated_badges = []
    
    # Process each badge
    for badge in ALL_BADGES:
        badge_earned = check_badge_earned(badge, progress)
        
        if badge_earned and badge['id'] not in current_badge_ids:
            # New badge earned
            earned_badge = {
                'id': badge['id'],
                'name': badge['name'],
                'path': badge['path'],
                'tier': badge['tier'],
                'description': badge['description'],
                'icon_url': badge['icon_url'],
                'earned_at': datetime.utcnow().isoformat()
            }
            updated_badges.append(earned_badge)
            newly_earned_badges.append(earned_badge)
            
        elif badge['id'] in current_badge_ids:
            # Existing badge - check retention
            existing_badge = next((b for b in current_badges if b['id'] == badge['id']), None)
            if existing_badge:
                if check_badge_retention(badge, user_id, db):
                    # Keep the badge
                    updated_badges.append(existing_badge)
                else:
                    # Badge lost due to retention rules - revert to previous tier
                    previous_tier_badge = get_previous_tier_badge(badge['path'], badge['tier'])
                    if previous_tier_badge and previous_tier_badge['id'] in current_badge_ids:
                        updated_badges.append(previous_tier_badge)
    
    # Update profile with new badges
    profile.badges = updated_badges
    db.commit()
    
    return newly_earned_badges

def get_previous_tier_badge(path: str, current_tier: str) -> Optional[Dict[str, Any]]:
    """Get the previous tier badge for retention fallback"""
    path_badges = [badge for badge in ALL_BADGES if badge['path'] == path]
    path_badges.sort(key=lambda x: int(x['tier']))
    
    current_tier_num = int(current_tier)
    if current_tier_num > 1:
        previous_tier_num = current_tier_num - 1
        return next((badge for badge in path_badges if int(badge['tier']) == previous_tier_num), None)
    
    return None

def get_badge_unlock_message(badge: Dict[str, Any]) -> str:
    """Generate unlock message for a badge"""
    messages = {
        'spark': "🎉 Badge Unlocked: Spark\nYou've taken the first step into untold truths — keep going.",
        'candlebearer': "🎉 Badge Unlocked: Candlebearer\nYou're starting to light the darkness with knowledge.",
        'torchbearer': "🎉 Badge Unlocked: Torchbearer\nYou've completed 25 erased stories. You carry their voices with you — keep going.",
        'flamekeeper': "🎉 Badge Unlocked: Flamekeeper\nYou protect what others tried to extinguish.",
        'beacon': "🎉 Badge Unlocked: Beacon\nYou shine so others can see. Your knowledge guides generations.",
        'constellation': "🎉 Badge Unlocked: Constellation\nYou've connected erased histories across communities. You're one of few to earn this.",
        'ember': "🔥 3-Day Streak: You're now an Ember.\nYour consistency keeps truth alive.",
        'flame': "🔥 7-Day Streak: You're now a Flame.\nYour consistency keeps truth alive. Protect your streak and level up to Inferno.",
        'inferno': "🔥 30-Day Streak: You're now an Inferno.\nYour dedication to learning is extraordinary.",
        'eternal_flame': "🔥 90-Day Streak: You're now an Eternal Flame.\nYour commitment to truth is unbreakable."
    }
    
    return messages.get(badge['id'], f"🎉 Badge Unlocked: {badge['name']}\n{badge['description']}")

def evaluate_badge_progress(user_id: int, db: Session) -> Dict[str, Any]:
    """Evaluate and update badge progress for a user"""
    newly_earned_badges = update_user_badges(user_id, db)
    
    # Get current badges and progress
    current_badges = get_user_badges(user_id, db)
    progress = get_user_progress(user_id, db)
    
    return {
        'newly_earned_badges': newly_earned_badges,
        'current_badges': current_badges,
        'progress': progress,
        'unlock_messages': [get_badge_unlock_message(badge) for badge in newly_earned_badges]
    } 

def get_default_badges() -> List[Dict[str, Any]]:
    """Get default badges that should be given to all new users"""
    default_badges = []
    
    for badge in DEFAULT_BADGES:
        earned_badge = {
            'id': badge['id'],
            'name': badge['name'],
            'path': badge['path'],
            'tier': badge['tier'],
            'description': badge['description'],
            'icon_url': badge['icon_url'],
            'earned_at': datetime.utcnow().isoformat()
        }
        default_badges.append(earned_badge)
    
    return default_badges

def initialize_user_badges(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """Initialize badges for a new user with default starter badges"""
    # Get user profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        return []
    
    # Set default badges
    default_badges = get_default_badges()
    profile.badges = default_badges
    db.commit()
    
    return default_badges 

def ensure_default_badges(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """Ensure user has default badges - give them if they don't have any badges yet"""
    # Get user profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        return []
    
    # If user has no badges, give them default ones
    if not profile.badges or len(profile.badges) == 0:
        default_badges = get_default_badges()
        profile.badges = default_badges
        db.commit()
        return default_badges
    
    # Check if user has default badges, if not add them
    current_badge_ids = {badge['id'] for badge in profile.badges}
    missing_default_badges = []
    
    for default_badge in DEFAULT_BADGES:
        if default_badge['id'] not in current_badge_ids:
            earned_badge = {
                'id': default_badge['id'],
                'name': default_badge['name'],
                'path': default_badge['path'],
                'tier': default_badge['tier'],
                'description': default_badge['description'],
                'icon_url': default_badge['icon_url'],
                'earned_at': datetime.utcnow().isoformat()
            }
            missing_default_badges.append(earned_badge)
    
    # Add missing default badges
    if missing_default_badges:
        profile.badges.extend(missing_default_badges)
        db.commit()
        return missing_default_badges
    
    return [] 