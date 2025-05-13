# Knowledge History Platform Architecture

This document outlines the architecture of the Knowledge History educational platform focusing on underrepresented groups in history.

## Database Schema (ER Diagram)

The system is built on a relational database with the following key entities:

### User Management
```
+----------------+      +----------------+      +-------------+
| User           |      | Profile        |      | UserFollow  |
+----------------+      +----------------+      +-------------+
| id             |<---->| id             |<---->| id          |
| email          |      | user_id        |      | follower_id |
| username       |      | points         |      | followed_id |
| password       |      | nickname       |      | created_at  |
| joined_at      |      | avatar_url     |      +-------------+
| is_active      |      | referral_code  |
| is_admin       |      | total_referrals|
+----------------+      | login_streak   |
                        | language_pref  |
                        | pronouns       |
                        | location       |
                        +----------------+
```

### Social Features
```
+----------------+      +----------------+      +----------------+
| Community      |      | Post           |      | Comment        |
+----------------+      +----------------+      +----------------+
| id             |<---->| id             |<---->| id             |
| name           |      | community_id   |      | post_id        |
| description    |      | title          |      | commented_by   |
| banner_url     |      | body           |      | comment        |
| icon_url       |      | image_url      |      | upvote         |
| topics         |      | upvote         |      | downvote       |
| created_at     |      | downvote       |      | created_at     |
| created_by     |      | created_at     |      +----------------+
+----------------+      | created_by     |
                        +----------------+
```

### Educational Content
```
+----------------+      +----------------+      +----------------+
| Timeline       |      | Story          |      | Quiz           |
+----------------+      +----------------+      +----------------+
| id             |<---->| id             |<---->| id             |
| title          |      | timeline_id    |      | story_id       |
| thumbnail_url  |      | story_date     |      | created_at     |
| year_range     |      | title          |      +----------------+
| overview       |      | desc           |            |
| main_char_id   |----->| story_type     |            |
| categories     |      | thumbnail_url  |            |
| created_at     |      | video_url      |     +----------------+
+----------------+      | likes          |     | Question       |
        ^               | views          |     +----------------+
        |               | created_at     |---->| id             |
        |               +----------------+     | quiz_id        |
+----------------+             |               | text           |
| Character      |             |               | created_at     |
+----------------+             |               +----------------+
| id             |             |                      |
| avatar_url     |      +----------------+     +----------------+
| persona        |      | Timestamp      |     | Option         |
| created_at     |      +----------------+     +----------------+
+----------------+      | id             |     | id             |
                        | story_id       |     | question_id    |
                        | time_sec       |     | text           |
                        | label          |     | is_correct     |
                        +----------------+     +----------------+
```

### Games and Engagement
```
+--------------------+      +----------------------+
| OnThisDay          |      | StandAloneGame      |
+--------------------+      +----------------------+
| id                 |      | id                  |
| date               |      | game_type           |
| title              |      | title               |
| short_desc         |      | image_url           |
| image_url          |      | story_id            |
| story_id           |----->| created_at          |
| created_at         |      +----------------------+
+--------------------+               |
                                     |
                            +----------------------+      +----------------------+
                            | GameOption           |      | GameAttempt         |
                            +----------------------+      +----------------------+
                            | id                  |      | id                  |
                            | question_id         |<-----| user_id             |
                            | text                |      | game_id             |
                            | is_correct          |      | selected_option_id  |
                            +----------------------+      | is_correct          |
                                                         | created_at          |
                                                         +----------------------+
```

## Core Workflows

### 1. Content Generation (injection.py)

The system uses advanced AI (GPT-4) to generate educational content about historically underrepresented groups.

```
+------------------+        +------------------+        +------------------+
| User Input       |        | GPT-4 Content    |        | Structure        |
| Historical Topic |------->| Generation       |------->| Content          |
+------------------+        +------------------+        +------------------+
                                                               |
                                                               v
+------------------+        +------------------+        +------------------+
| Create Quizzes   |<-------| Create Stories   |<-------| Create Timeline  |
| for each Story   |        | with Media       |        | & Character      |
+------------------+        +------------------+        +------------------+
        |                          |                           |
        |                          |                           |
        v                          v                           v
+--------------------------------------------------+
|               Database Storage                   |
+--------------------------------------------------+
```

#### Workflow Steps:

1. **Input Collection**: Administrator enters a historical topic focused on underrepresented groups
2. **AI Content Generation**: 
   - GPT-4 generates detailed, historically accurate content including:
   - Character profiles with concise personas
   - Timeline with title, year range, and overview
   - Multiple stories within the timeline (with rich detail)
   - Quiz questions for each story

3. **Media Generation**:
   - DALL-E 3 creates historically accurate images for characters, timelines, and stories
   - Optional video generation for stories

4. **Content Structuring**:
   - Content is formatted into structured JSON with proper formatting
   - Date standardization and validation

5. **API Storage**:
   - Character, timeline, stories, and quizzes are uploaded via API endpoints
   - Media files are uploaded and linked to appropriate content

### 2. Game Generation System (games.py)

The platform features educational games to reinforce learning with three distinct game types:

```
+------------------+        +------------------+        +------------------+
| Select Game Type |        | Retrieve Story   |        | GPT-4 Question   |
| and Story ID     |------->| from Database    |------->| Generation       |
+------------------+        +------------------+        +------------------+
                                                               |
                                                               v
+------------------+        +------------------+        +------------------+
| Save to Database |<-------| Add Media        |<-------| Format Questions |
| via API          |        | (DALL-E Images)  |        | & Options        |
+------------------+        +------------------+        +------------------+
```

#### Game Types:

1. **Guess The Year (Type 1)**
   - **Purpose**: Test knowledge of historical chronology
   - **Format**: Questions about when historical events occurred
   - **Example**: "In what year did Rosa Parks refuse to give up her seat on a Montgomery bus?"
   - **Implementation**:
     - GPT-4 extracts significant dates from story context
     - Generates 5-7 challenging questions with 4 year options
     - Only one option is correct
     - No image generation required

2. **Image Guess (Type 2)**
   - **Purpose**: Visual recognition of historical elements
   - **Format**: Image-based questions requiring identification
   - **Example**: Shows image of an important historical figure, asks "Who is this person?"
   - **Implementation**:
     - GPT-4 generates question content and detailed image descriptions
     - DALL-E creates historically accurate images
     - Each question has 4 text options
     - Images are automatically generated, saved, and uploaded

3. **Fill in the Blank (Type 3)**
   - **Purpose**: Test factual knowledge in context
   - **Format**: Incomplete sentences from historical narratives
   - **Example**: "The Montgomery Bus Boycott lasted for ____ days."
   - **Implementation**:
     - GPT-4 extracts key facts from story context
     - Creates statements with missing information
     - 4 options for completing each statement
     - No image generation required

#### Workflow Steps:

1. **Game Initialization**:
   - Administrator selects a game type (1-3) and story ID
   - System retrieves story content from database

2. **AI Question Generation**:
   - GPT-4 analyzes story content
   - Generates appropriate questions based on game type
   - Ensures exactly 4 options per question with one correct answer

3. **Media Enhancement** (for Image Guess games):
   - DALL-E generates images based on detailed descriptions
   - Images are saved and linked to questions

4. **API Storage**:
   - Questions, options, and media are formatted as JSON
   - Bulk upload to API endpoint
   - Game becomes available for users to play

## Data Models

### Key Enums:
- **GameTypes**: 
  1. GUESS_THE_YEAR
  2. IMAGE_GUESS
  3. FILL_IN_THE_BLANK
- **StoryType**: Documentary, Biography, Historical Event, etc.
- **TimelineCategory**: Race/Ethnicity, Gender, Sexual Orientation, Historical Focus
- **LanguagePreference**: English, Spanish, French, etc.

### Authentication:
- Password hashing via bcrypt
- Session-based authentication
- Referral code system

## Technology Stack
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **AI Integration**: OpenAI GPT-4 and DALL-E 3
- **API**: RESTful endpoints
- **Authentication**: Cookie-based sessions
- **Media Storage**: File-based with database references

## Deployment Configuration
- Database connection pooling with timeout and keepalive settings
- Environment variable configuration
- Error handling and retry mechanisms 