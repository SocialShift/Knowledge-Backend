from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON, ForeignKey, create_engine,Text,Date, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
from passlib.context import CryptContext
import random
import enum

# Database setup
#DATABASE_URL = "postgresql://postgres:Iamreal123@localhost/knowledge"
DATABASE_URL = "postgresql://knowledge_f8o6_user:TTNU3ipJcBPMtKJIhPYXutzrO3VS5CKr@dpg-cvbr42jtq21c73e2dvhg-a.oregon-postgres.render.com/knowledge_f8o6"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
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


# User Model
class User(Base):
    __tablename__= 'users'

    id= Column(Integer, primary_key=True)
    email= Column(String(255), unique=True, nullable=False)
    password= Column(String(255), nullable=False)
    joined_at= Column(DateTime, default=datetime.now())
    is_active= Column(Boolean, default=True)
    is_admin= Column(Boolean, default=False)

    # Relationship with Profile
    profile= relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.password)

    def set_password(self, password):
        self.password= pwd_context.hash(password)

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


    user= relationship("User", back_populates="profile")


    def __init__(self, **kwargs):
        """Auto-generate referral code only if it's missing"""
        super().__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.create_random()

    @staticmethod
    def create_random():
        return "".join([str(random.randint(0, 9)) for _ in range(6)])

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


class Timeline(Base):
    __tablename__ = "timelines"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, unique=True)  # Example: "Mahatma Gandhi's Role in Independence"
    thumbnail_url = Column(String(255), unique=True)
    year_range = Column(String(50), nullable=False)
    overview = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with Stories
    stories = relationship("Story", back_populates="timeline", cascade="all, delete-orphan")

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
    thumbnail_url = Column(String(255), unique=True)
    video_url = Column(String(255), unique=True)
    likes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    timeline = relationship("Timeline", back_populates="stories")
    on_this_day = relationship("OnThisDay", back_populates="story", uselist=False)
    timestamps = relationship("Timestamp", back_populates="story", cascade="all, delete-orphan")
    quiz = relationship("Quiz", back_populates="story", uselist=False, cascade="all, delete-orphan")



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

    __table_args__ = (
        UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz'),
    )