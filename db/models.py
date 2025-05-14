from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON, ForeignKey, create_engine,Text,Date, UniqueConstraint, Table
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
from passlib.context import CryptContext
import random
import enum
from dotenv import load_dotenv
import os
load_dotenv()

# Database setup
#DATABASE_URL = "postgresql://postgres:Iamreal123@localhost/knowledge"
DATABASE_URL= os.environ['DATABASE_URL']
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_timeout=30,     # Timeout for getting a connection from pool
    max_overflow=10,     # Allow 10 connections to be created beyond pool_size
    pool_size=10,        # Maintain a pool of 10 connections
    connect_args={
        "connect_timeout": 10,  # 10 seconds connection timeout
        "keepalives": 1,        # Enable TCP keepalives
        "keepalives_idle": 60,  # Idle time before sending keepalives
        "keepalives_interval": 10,  # Time between keepalives
        "keepalives_count": 3   # Number of keepalives before giving up
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = None
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            db = SessionLocal()
            yield db
            break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                # Re-raise the exception if we've exhausted retries
                raise
            # Log the error (you may want to implement proper logging)
            print(f"Database connection error (attempt {retry_count}/{max_retries}): {str(e)}")
            # If we had a connection but it failed, ensure it's closed
            if db is not None:
                try:
                    db.close()
                except:
                    pass
    
    if db is not None:
        db.close()

        
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Enums
class LanguagePreference(str, enum.Enum):  # ✅ Added str for proper DB storage
    ENGLISH = "English"
    SPANISH = "Spanish"
    FRENCH = "French"
    GERMAN = "German"
    CHINESE = "Chinese"

class Pronouns(str, enum.Enum):
    HE_HIM = "He/Him"
    SHE_HER = "She/Her"
    THEY_THEM = "They/Them"
    OTHER = "Other"

class StoryType(enum.IntEnum):
    DOCUMENTARY = 1
    BIOGRAPHY = 2
    HISTORICAL_EVENT = 3
    SCIENTIFIC_DISCOVERY = 4
    CULTURAL_PHENOMENON = 5
    TECHNOLOGICAL_ADVANCEMENT = 6
    EDUCATIONAL = 7
    MYTHOLOGICAL = 8
    ENVIRONMENTAL = 9
    POLITICAL = 10
    SOCIAL_MOVEMENT = 11
    ARTISTIC_DEVELOPMENT = 12

class TimelineCategory(str, enum.Enum):
    # Racial/Ethnic Categories
    AFRICAN = "African/African Diaspora"
    ASIAN = "Asian/Asian Diaspora"
    INDIGENOUS = "Indigenous/Native"
    LATINO = "Latino/Hispanic"
    MIDDLE_EASTERN = "Middle Eastern/North African"
    PACIFIC_ISLANDER = "Pacific Islander"
    WHITE = "White/European"
    MULTIRACIAL = "Multiracial/Mixed Heritage"
    RACIAL_OTHER = "Other"
    RACIAL_NO_ANSWER = "Prefer not to say"
    
    # Gender Categories
    WOMAN = "Woman"
    MAN = "Man"
    NON_BINARY = "Non-Binary"
    GENDERQUEER = "Genderqueer/Gender Non-Conforming"
    TRANSGENDER = "Transgender"
    TWO_SPIRIT = "Two-Spirit (Indigenous-specific identity)"
    GENDER_OTHER = "Other"
    GENDER_NO_ANSWER = "Prefer not to say"
    
    # Sexual Orientation Categories
    STRAIGHT = "Heterosexual/Straight"
    GAY = "Gay/Lesbian"
    BISEXUAL = "Bisexual/Pansexual"
    ASEXUAL = "Asexual"
    QUEER = "Queer"
    SEXUAL_OTHER = "Other"
    SEXUAL_NO_ANSWER = "Prefer not to say"
    
    # Historical Focus Categories
    INDIGENOUS_HISTORY = "Indigenous Histories and Cultures"
    BLACK_HISTORY = "African Diaspora and Black History"
    LGBTQ_HISTORY = "LGBTQ+ Movements and Milestones"
    WOMEN_HISTORY = "Women's Histories and Contributions"
    IMMIGRANT_HISTORY = "Immigrant and Refugee Stories"
    COLONIAL_HISTORY = "Colonialism and Post-Colonial Histories"
    CIVIL_RIGHTS = "Civil Rights and Social Justice Movements"
    LESSER_KNOWN = "Lesser-Known Historical Figures"
    HISTORY_OTHER = "Other"

class Location(str, enum.Enum):
    ALABAMA = "Alabama"
    ALASKA = "Alaska"
    ARIZONA = "Arizona"
    ARKANSAS = "Arkansas"
    CALIFORNIA = "California"
    COLORADO = "Colorado"
    CONNECTICUT = "Connecticut"
    DELAWARE = "Delaware"
    FLORIDA = "Florida"
    GEORGIA = "Georgia"
    HAWAII = "Hawaii"
    IDAHO = "Idaho"
    ILLINOIS = "Illinois"
    INDIANA = "Indiana"
    IOWA = "Iowa"
    KANSAS = "Kansas"
    KENTUCKY = "Kentucky"
    LOUISIANA = "Louisiana"
    MAINE = "Maine"
    MARYLAND = "Maryland"
    MASSACHUSETTS = "Massachusetts"
    MICHIGAN = "Michigan"
    MINNESOTA = "Minnesota"
    MISSISSIPPI = "Mississippi"
    MISSOURI = "Missouri"
    MONTANA = "Montana"
    NEBRASKA = "Nebraska"
    NEVADA = "Nevada"
    NEW_HAMPSHIRE = "New Hampshire"
    NEW_JERSEY = "New Jersey"
    NEW_MEXICO = "New Mexico"
    NEW_YORK = "New York"
    NORTH_CAROLINA = "North Carolina"
    NORTH_DAKOTA = "North Dakota"
    OHIO = "Ohio"
    OKLAHOMA = "Oklahoma"
    OREGON = "Oregon"
    PENNSYLVANIA = "Pennsylvania"
    RHODE_ISLAND = "Rhode Island"
    SOUTH_CAROLINA = "South Carolina"
    SOUTH_DAKOTA = "South Dakota"
    TENNESSEE = "Tennessee"
    TEXAS = "Texas"
    UTAH = "Utah"
    VERMONT = "Vermont"
    VIRGINIA = "Virginia"
    WASHINGTON = "Washington"
    WEST_VIRGINIA = "West Virginia"
    WISCONSIN = "Wisconsin"
    WYOMING = "Wyoming"

# User Follow relationship table
class UserFollow(Base):
    __tablename__ = "user_follows"
    
    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey('profiles.id', ondelete="CASCADE"), nullable=False)
    followed_id = Column(Integer, ForeignKey('profiles.id', ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    follower = relationship("Profile", foreign_keys=[follower_id], back_populates="following")
    followed = relationship("Profile", foreign_keys=[followed_id], back_populates="followers")
    
    __table_args__ = (
        UniqueConstraint('follower_id', 'followed_id', name='unique_follow_relationship'),
    )
    
    def __repr__(self):
        return f"Follow: {self.follower_id} -> {self.followed_id}"

# User Model
class User(Base):
    __tablename__= 'users'

    id= Column(Integer, primary_key=True)
    email= Column(String(255), unique=True, nullable=False)
    username= Column(String(255), unique=True, nullable=True)
    password= Column(String(255), nullable=False)
    joined_at= Column(DateTime, default=datetime.now())
    is_active= Column(Boolean, default=True)
    is_admin= Column(Boolean, default=False)

    # Relationship with Profile
    profile= relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    
    # Community relationships
    communities = relationship("Community", back_populates="creator", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    
    # Feedback relationship
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.password)

    def set_password(self, password):
        self.password= pwd_context.hash(password)

    def generate_username(self):
        if self.email and self.id:
            email_username = self.email.split('@')[0]
            self.username = f"{email_username}{self.id}"
        return self.username
    
    def __repr__(self):
        return self.email
# Profile Model
class Profile(Base):
    __tablename__= 'profiles'

    id= Column(Integer, primary_key=True)
    user_id= Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), unique=True, nullable=False)
    points= Column(Integer, default=100)
    
    nickname= Column(String(255), nullable=True)
    avatar_url= Column(String(255), default="media/images/default.jpeg")
    referral_code = Column(String(6), nullable=True)
    total_referrals= Column(Integer, default=0, nullable=True)

    current_login_streak = Column(Integer, default=0)
    max_login_streak = Column(Integer, default=0)
    last_login_date = Column(Date, nullable=True)
    # ✅ Fixed Enums
    language_preference= Column(Enum(LanguagePreference, native_enum=False), nullable=True, default=LanguagePreference.ENGLISH)
    pronouns= Column(Enum(Pronouns, native_enum=False), nullable=True)
    location= Column(Enum(Location, native_enum=False), nullable=True)

    # Learning Style
    personalization_questions= Column(JSON, nullable=True)

    # Relationship with User
    user= relationship("User", back_populates="profile")
    
    # Followers and Following relationships
    followers = relationship("UserFollow", foreign_keys="UserFollow.followed_id", back_populates="followed", cascade="all, delete-orphan")
    following = relationship("UserFollow", foreign_keys="UserFollow.follower_id", back_populates="follower", cascade="all, delete-orphan")


    def __init__(self, **kwargs):
        """Auto-generate referral code only if it's missing"""
        super().__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.create_random()

    @staticmethod
    def create_random():
        return "".join([str(random.randint(0, 9)) for _ in range(6)])
    
    def __repr__(self):
        return self.nickname

class OnThisDay(Base):
    __tablename__ = "on_this_day"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)  # Ensures unique historical events per date
    title = Column(String(255), nullable=False)  # Catchy notification title
    short_desc = Column(Text, nullable=False)  # Hook message for the user
    image_url = Column(String(255), nullable=True)  # Optional image for the event
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="SET NULL"), nullable=True)  # Links to a Story
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    story = relationship("Story", back_populates="on_this_day")  # Connects to Story

    def __repr__(self):
        return self.title

class Character(Base):
    __tablename__= "characters"

    id= Column(Integer, primary_key=True)
    name= Column(String(255), default="name")
    avatar_url= Column(String(255), unique=True, nullable=True)
    persona= Column(Text, nullable=False)
    created_at= Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return self.persona
    

class Timeline(Base):
    __tablename__ = "timelines"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, unique=True)  # Example: "Mahatma Gandhi's Role in Independence"
    thumbnail_url = Column(String(255), unique=True)
    year_range = Column(String(50), nullable=False)
    overview = Column(Text)
    main_character_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
    categories= Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with Stories
    stories = relationship("Story", back_populates="timeline", cascade="all, delete-orphan")
    main_character = relationship("Character")

    def __repr__(self):
        return self.title

class Timestamp(Base):
    __tablename__ = "timestamps"

    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"))
    time_sec = Column(Integer, nullable=False)  # Timestamp in seconds
    label = Column(String(100))  # Optional: Label for the timestamp (e.g., "Chapter 1")

    story = relationship("Story", back_populates="timestamps")


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    timeline_id = Column(Integer, ForeignKey("timelines.id", ondelete="CASCADE"), nullable=True)  # Links to Timeline
    story_date= Column(Date, nullable=False)
    title = Column(String(100), nullable=False)
    desc = Column(Text)
    story_type = Column(Integer, nullable=True)  # Using the StoryType enum
    thumbnail_url = Column(String(255), unique=True)
    video_url = Column(String(255), unique=True, nullable=True)
    likes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    timeline = relationship("Timeline", back_populates="stories")
    on_this_day = relationship("OnThisDay", back_populates="story", uselist=False)
    timestamps = relationship("Timestamp", back_populates="story", cascade="all, delete-orphan")
    quiz = relationship("Quiz", back_populates="story", uselist=False, cascade="all, delete-orphan")
    stand_alone_games = relationship("StandAloneGameQuestion", back_populates="story")

    def __repr__(self):
        return self.title


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    story = relationship("Story", back_populates="quiz")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"))
    text = Column(Text, nullable=False)  # The question itself
    created_at = Column(DateTime, default=datetime.utcnow)

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")


class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    text = Column(String(255), nullable=False)  # Answer text
    is_correct = Column(Boolean, default=False)  # Only one option should be correct

    question = relationship("Question", back_populates="options")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id= Column(Integer, primary_key=True)
    user_id= Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    quiz_id= Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"))
    completed= Column(Boolean, default=False)  # Whether the quiz was completed
    score= Column(Integer, default=0)  # Points earned from this attempt
    created_at= Column(DateTime, default=datetime.utcnow)
    completed_at= Column(DateTime, nullable=True)  # When the quiz was completed

    # Add relationships
    user = relationship("User")
    quiz = relationship("Quiz")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz'),
    )

class UserStoryLike(Base):
    __tablename__ = "user_story_likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'story_id', name='unique_user_story_like'),
    )

class Community(Base):
    __tablename__= "communities"

    id= Column(Integer, primary_key=True)
    name= Column(String(200), nullable=False)
    description= Column(Text)
    banner_url= Column(String(255), default='media/community-banners/default.jpeg')
    icon_url= Column(String(255), default='media/community-icons/default.jpeg')
    topics= Column(JSON, nullable=True) # select multiples
    
    created_at= Column(DateTime, default=datetime.utcnow)
    created_by= Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)

    creator= relationship("User", back_populates="communities")
    posts = relationship("Post", back_populates="community", cascade="all, delete-orphan")

    def __repr__(self):
        return self.name

class Post(Base):
    __tablename__= "posts"

    id= Column(Integer, primary_key=True)
    community_id= Column(Integer, ForeignKey('communities.id', ondelete='CASCADE'))
    title= Column(String(255), nullable=False)
    body= Column(Text, nullable=True)
    image_url= Column(String(255), nullable=True)

    upvote= Column(Integer, default=0)
    downvote= Column(Integer, default=0)

    created_at= Column(DateTime, default=datetime.utcnow)
    created_by= Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)

    author= relationship("User", back_populates="posts")
    community = relationship("Community", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return self.title


class Comment(Base):
    __tablename__= "comments"


    id= Column(Integer, primary_key=True)
    post_id= Column(Integer, ForeignKey('posts.id', ondelete="CASCADE"))
    commented_by= Column(Integer, ForeignKey('users.id', ondelete="CASCADE"))
    comment= Column(Text)
    upvote= Column(Integer, default=0)
    downvote= Column(Integer, default=0)
    created_at= Column(DateTime, default=datetime.utcnow)

    author= relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")

    def __repr__(self):
        return f"Comment by {self.commented_by} on post {self.post_id}"
    
class Feedback(Base):
    __tablename__= "feedbacks"

    id= Column(Integer, primary_key=True)
    user_id= Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), unique=False, nullable=False)
    text= Column(Text, nullable=False)

    user= relationship("User", back_populates="feedback")

    def __repr__(self):
        return f"Feedback by {self.user_id}"
    


class GameTypes(enum.IntEnum):
    GUESS_THE_YEAR= 1
    IMAGE_GUESS= 2
    FILL_IN_THE_BLANK= 3
    

class StandAloneGameQuestion(Base):
    __tablename__= "stand_alone_games"

    id= Column(Integer, primary_key=True)
    game_type= Column(Enum(GameTypes), nullable=False)
    title= Column(String(255), nullable=False)
    image_url= Column(String(255), nullable=True)
    story_id= Column(Integer, ForeignKey("stories.id", ondelete="SET NULL"), nullable=True)
    created_at= Column(DateTime, default=datetime.utcnow)

    # Add relationship to options
    options = relationship("StandAloneGameOption", back_populates="question", cascade="all, delete-orphan")
    
    # Add relationship to story
    story = relationship("Story", back_populates="stand_alone_games")

    def __repr__(self):
        return self.title
    
class StandAloneGameOption(Base):
    __tablename__= "stand_alone_games_options"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("stand_alone_games.id", ondelete="CASCADE"))
    text = Column(String(255), nullable=False)  # Answer text
    is_correct = Column(Boolean, default=False)  # Only one option should be correct

    # Add relationship to question
    question = relationship("StandAloneGameQuestion", back_populates="options")

class StandAloneGameAttempt(Base):
    __tablename__ = "stand_alone_game_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    game_id = Column(Integer, ForeignKey("stand_alone_games.id", ondelete="CASCADE"))
    selected_option_id = Column(Integer, ForeignKey("stand_alone_games_options.id", ondelete="SET NULL"), nullable=True)
    is_correct = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    game = relationship("StandAloneGameQuestion")
    selected_option = relationship("StandAloneGameOption")

    def __repr__(self):
        return f"Attempt on game {self.game_id} by user {self.user_id}"