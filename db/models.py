from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
from passlib.context import CryptContext
import random
import enum

# Database setup
DATABASE_URL = "postgresql://postgres:Iamreal123@localhost/knowledge"
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
    USA_EAST = "East Coast"
    USA_WEST = "West Coast"
    USA_CENTRAL = "Central"
    USA_SOUTH = "South"


# User Model
class User(Base):
    __tablename__= 'users'

    id= Column(Integer, primary_key=True)
    email= Column(String(255), unique=True, nullable=False)
    password= Column(String(255), nullable=False)
    joined_at= Column(DateTime, default=datetime.now())
    is_active= Column(Boolean, default=True)

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
    
    nickname= Column(String(255), nullable=True)
    avatar_url= Column(String(255), nullable=True)
    referral_code = Column(String(6), nullable=True)
    total_referrals= Column(Integer, default=0, nullable=True)

    # ✅ Fixed Enums
    language_preference= Column(Enum(LanguagePreference, native_enum=False), nullable=True, default=LanguagePreference.ENGLISH)
    pronouns= Column(Enum(Pronouns, native_enum=False), nullable=True)
    location= Column(Enum(Location, native_enum=False), nullable=True)

    # Learning Style
    learning_style= Column(JSON, nullable=True)

    # Accessibility
    accessibility_settings= Column(JSON, nullable=True)

    user= relationship("User", back_populates="profile")


    def __init__(self, **kwargs):
        """Auto-generate referral code only if it's missing"""
        super().__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.create_random()

    @staticmethod
    def create_random():
        return "".join([str(random.randint(0, 9)) for _ in range(6)])