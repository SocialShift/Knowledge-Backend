from sqlalchemy import Column, Integer, String, Boolean, DateTime,Enum,JSON, ForeignKey, Table, Text, Float
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
from sqlalchemy import create_engine
from passlib.context import CryptContext
import random

engine = create_engine("postgresql://postgres:Iamreal123@localhost:5432/knowledge")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LanguagePreference(Enum):
    ENGLISH = "English"
    SPANISH = "Spanish"
    FRENCH = "French"
    GERMAN = "German"
    CHINESE = "Chinese"

class Pronouns(Enum):
    HE_HIM = "He/Him"
    SHE_HER = "She/Her"
    THEY_THEM = "They/Them"
    OTHER = "Other"

class Location(Enum):
    USA_EAST = "East Coast"
    USA_WEST = "West Coast"
    USA_CENTRAL = "Central"
    USA_SOUTH = "South"

class LearningMode(Enum):
    STORYTELLING = "Storytelling"
    RESEARCH = "Research"
    INTERACTIVE = "Interactive"
    SUMMARIES = "Summaries"

class User(Base):
    __tablename__= 'users'

    id= Column(Integer, primary_key=True)

    email= Column(String(255), unique=True, nullable=False)
    password= Column(String(255), nullable=False)
    nickname= Column(String(255), nullable=False)

    language_preference= Column(Enum(LanguagePreference), nullable=False, default=LanguagePreference.ENGLISH)
    pronouns= Column(Enum(Pronouns), nullable=True)
    location= Column(Enum(Location), nullable=True)


     # 🎯 Learning Style Hybrid
    learning_style_mode= Column(Enum(LearningMode), nullable=False, default=LearningMode.STORYTELLING)  # Fast Querying
    learning_style_details= Column(JSON, nullable=True)  # {"frequency": "Daily", "preferred_media": "Podcasts"}

     # 🎯 Accessibility Hybrid
    accessibility_dark_mode= Column(Boolean, default=False)  # Fast Query
    accessibility_text_to_speech= Column(Boolean, default=False)  # Fast Query
    accessibility_settings= Column(JSON, nullable=True)  # {"font_size": "Large", "color_blind_mode": "Protanopia"}


    avatar_url= Column(String(255), nullable=True, default='')
    referral_code = Column(String(6), default=lambda: User.create_random(), nullable=True)
    total_referrals= Column(Integer, default=0, nullable=True)

    joined_at= Column(DateTime, default=datetime.now()) 
    is_active= Column(Boolean, default=True)

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.password)

    def set_password(self, password):
        self.password = pwd_context.hash(password)

    @staticmethod
    def create_random():
        """Generate a random 6-digit referral code."""
        return "".join([str(random.randint(0, 9)) for _ in range(6)])