from sqladmin import ModelView
from wtforms import SelectMultipleField
from .models import User, Profile, Timeline, Story, Quiz, Question, Option, Character, OnThisDay, QuizAttempt, UserStoryLike, Timestamp, Feedback, TimelineCategory, StandAloneGameQuestion, StandAloneGameOption, GameTypes, StandAloneGameAttempt

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.password, User.joined_at, User.is_active, User.is_admin]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    
    # Display related profile
    column_formatters = {
        User.profile: lambda m, a: m.profile.nickname if m.profile else "No profile"
    }

class ProfileAdmin(ModelView, model=Profile):
    column_list = [Profile.id, Profile.user_id, Profile.nickname, Profile.points, Profile.avatar_url, 
                   Profile.referral_code, Profile.total_referrals, Profile.current_login_streak, 
                   Profile.max_login_streak, Profile.last_login_date, Profile.language_preference, 
                   Profile.pronouns, Profile.location, Profile.personalization_questions]
    name = "Profile"
    name_plural = "Profiles"
    icon = "fa-solid fa-address-card"
    
    # Display related user
    column_formatters = {
        Profile.user: lambda m, a: f"{m.user.email}" if m.user else "No user"
    }
    
class TimelineAdmin(ModelView, model=Timeline):
    column_list = [Timeline.id, Timeline.title, Timeline.thumbnail_url, Timeline.year_range, 
                   Timeline.overview, Timeline.main_character_id, Timeline.categories, Timeline.created_at]
    name = "Timeline"
    name_plural = "Timelines"
    icon = "fa-solid fa-clock-rotate-left"
    
    # Add form_overrides to use a multi-select field for categories
    form_overrides = {
        "categories": SelectMultipleField
    }
    
    # Configure the categories field with TimelineCategory options
    form_args = {
        "categories": {
            "choices": [(category.name, category.value) for category in TimelineCategory],
            "coerce": str
        }
    }
    
    # Handle JSON conversion when saving the form
    async def on_model_change(self, model, is_created, request=None, extra_param=None):
        # The form data is already set to model.categories as a list of strings
        # No need to do anything else
        pass
    
    # Handle data transformation when loading form data
    async def on_form_prefill(self, form, id, request=None):
        # Get the Timeline instance
        model = self.get_one(id)
        # If categories exists and is a list, use the values for the form
        if model and model.categories and isinstance(model.categories, list):
            # Set the form data to the list of category names
            form.categories.data = model.categories
    
    # Display related character
    column_formatters = {
        Timeline.main_character: lambda m, a: f"{m.main_character.persona[:30]}..." if m.main_character else "None",
        Timeline.stories: lambda m, a: f"{len(m.stories)} stories" if m.stories else "No stories",
        Timeline.categories: lambda m, a: ", ".join(m.categories) if m.categories else "No categories"
    }
    
class StoryAdmin(ModelView, model=Story):
    column_list = [Story.id, Story.timeline_id, Story.story_date, Story.title, Story.desc, 
                   Story.story_type, Story.thumbnail_url, Story.video_url, Story.likes, 
                   Story.views, Story.created_at]
    name = "Story"
    name_plural = "Stories"
    icon = "fa-solid fa-book"
    
    # Display related timeline
    column_formatters = {
        Story.timeline: lambda m, a: f"{m.timeline.title}" if m.timeline else "None",
        Story.timestamps: lambda m, a: f"{len(m.timestamps)} timestamps" if m.timestamps else "None",
        Story.quiz: lambda m, a: f"Quiz #{m.quiz.id}" if m.quiz else "None"
    }
    
class QuizAdmin(ModelView, model=Quiz):
    column_list = [Quiz.id, Quiz.story_id, Quiz.created_at]
    name = "Quiz"
    name_plural = "Quizzes"
    icon = "fa-solid fa-question-circle"
    
    # Display related story and questions
    column_formatters = {
        Quiz.story: lambda m, a: f"{m.story.title}" if m.story else "None",
        Quiz.questions: lambda m, a: f"{len(m.questions)} questions" if m.questions else "No questions"
    }

class QuestionAdmin(ModelView, model=Question):
    column_list = [Question.id, Question.quiz_id, Question.text, Question.created_at]
    name = "Question"
    name_plural = "Questions"
    icon = "fa-solid fa-question"
    
    # Display related quiz and options
    column_formatters = {
        Question.quiz: lambda m, a: f"Quiz #{m.quiz.id}" if m.quiz else "None",
        Question.options: lambda m, a: f"{len(m.options)} options" if m.options else "No options"
    }

class OptionAdmin(ModelView, model=Option):
    column_list = [Option.id, Option.question_id, Option.text, Option.is_correct]
    name = "Option" 
    name_plural = "Options"
    icon = "fa-solid fa-list"
    
    # Display related question
    column_formatters = {
        Option.question: lambda m, a: f"{m.question.text[:30]}..." if m.question else "None"
    }
    
class CharacterAdmin(ModelView, model=Character):
    column_list = [Character.id, Character.avatar_url, Character.persona, Character.created_at]
    name = "Character"
    name_plural = "Characters"
    icon = "fa-solid fa-user-astronaut"
    
class OnThisDayAdmin(ModelView, model=OnThisDay):
    column_list = [OnThisDay.id, OnThisDay.date, OnThisDay.title, OnThisDay.short_desc, 
                   OnThisDay.image_url, OnThisDay.story_id, OnThisDay.created_at]
    name = "On This Day"
    name_plural = "On This Day Events"
    icon = "fa-solid fa-calendar-day"
    
    # Display related story
    column_formatters = {
        OnThisDay.story: lambda m, a: f"{m.story.title}" if m.story else "None"
    }

class QuizAttemptAdmin(ModelView, model=QuizAttempt):
    column_list = [QuizAttempt.id, QuizAttempt.user_id, QuizAttempt.quiz_id, 
                   QuizAttempt.completed, QuizAttempt.score, QuizAttempt.created_at, 
                   QuizAttempt.completed_at]
    name = "Quiz Attempt"
    name_plural = "Quiz Attempts"
    icon = "fa-solid fa-clipboard-check"
    
    # Display related user and quiz
    column_formatters = {
        QuizAttempt.user_id: lambda m, a: f"{User.query.get(m.user_id).email}" if User.query.get(m.user_id) else f"User #{m.user_id}",
        QuizAttempt.quiz_id: lambda m, a: f"Quiz #{m.quiz_id}"
    }

class UserStoryLikeAdmin(ModelView, model=UserStoryLike):
    column_list = [UserStoryLike.id, UserStoryLike.user_id, UserStoryLike.story_id, UserStoryLike.created_at]
    name = "User Story Like"
    name_plural = "User Story Likes"
    icon = "fa-solid fa-thumbs-up"
    
    # Display related user and story
    column_formatters = {
        UserStoryLike.user_id: lambda m, a: f"{User.query.get(m.user_id).email}" if User.query.get(m.user_id) else f"User #{m.user_id}",
        UserStoryLike.story_id: lambda m, a: f"{Story.query.get(m.story_id).title}" if Story.query.get(m.story_id) else f"Story #{m.story_id}"
    }

class TimestampAdmin(ModelView, model=Timestamp):
    column_list = [Timestamp.id, Timestamp.story_id, Timestamp.time_sec, Timestamp.label]
    name = "Timestamp"
    name_plural = "Timestamps"
    icon = "fa-solid fa-stopwatch"
    
    # Display related story
    column_formatters = {
        Timestamp.story: lambda m, a: f"{m.story.title}" if m.story else "None"
    }

class FeedbackAdmin(ModelView, model=Feedback):
    column_list = [Feedback.id, Feedback.user_id, Feedback.text]
    name = "Feedback"
    name_plural = "Feedbacks"
    icon = "fa-solid fa-comment"
    
    # Display related user
    column_formatters = {
        Feedback.user: lambda m, a: f"{m.user.email}" if m.user else "None"
    }

class StandAloneGameQuestionAdmin(ModelView, model=StandAloneGameQuestion):
    column_list = [StandAloneGameQuestion.id, StandAloneGameQuestion.game_type, StandAloneGameQuestion.title, 
                   StandAloneGameQuestion.image_url, StandAloneGameQuestion.created_at]
    name = "StandAlone Game Question"
    name_plural = "StandAlone Game Questions"
    icon = "fa-solid fa-gamepad"
    
    # Display related options
    column_formatters = {
        StandAloneGameQuestion.options: lambda m, a: f"{len(m.options)} options" if m.options else "No options"
    }

class StandAloneGameOptionAdmin(ModelView, model=StandAloneGameOption):
    column_list = [StandAloneGameOption.id, StandAloneGameOption.question_id, StandAloneGameOption.text, 
                   StandAloneGameOption.is_correct]
    name = "StandAlone Game Option"
    name_plural = "StandAlone Game Options"
    icon = "fa-solid fa-list-check"
    
    # Display related question
    column_formatters = {
        StandAloneGameOption.question: lambda m, a: f"{m.question.title}" if m.question else "None"
    }

class StandAloneGameAttemptAdmin(ModelView, model=StandAloneGameAttempt):
    column_list = [StandAloneGameAttempt.id, StandAloneGameAttempt.user_id, StandAloneGameAttempt.game_id, 
                   StandAloneGameAttempt.selected_option_id, StandAloneGameAttempt.is_correct, 
                   StandAloneGameAttempt.created_at]
    name = "StandAlone Game Attempt"
    name_plural = "StandAlone Game Attempts"
    icon = "fa-solid fa-gamepad"