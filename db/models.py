from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
from passlib.context import CryptContext
import random
import enum

# Database setup
#DATABASE_URL = "postgresql://postgres:Iamreal123@localhost/knowledge"
DATABASE_URL = "postgresql://knowledge_k18a_user:8vY2XYI72VnYDQ7VQRXAV1VXMDQVN8Gd@dpg-cukvdkq3esus73b14hk0-a.oregon-postgres.render.com/knowledge_k18a"
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