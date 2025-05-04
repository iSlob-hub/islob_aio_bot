"""
Survey conversation with multiple branches
"""
from typing import Any, Dict

from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.convo_graph import Node, conversation_graph
from app.models import User


# Helper function to create simple inline keyboards
def create_options_keyboard(options: Dict[str, str]) -> InlineKeyboardMarkup:
    """Create a keyboard with options as buttons"""
    builder = InlineKeyboardBuilder()
    for callback_data, text in options.items():
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


# Node handlers
async def survey_start_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the survey start node"""
    # Initialize survey context if not exists
    if not user.context:
        user.context = {}
    
    user.context["survey_results"] = {}
    await session.commit()
    
    # Check if it's a message or callback
    if update.message:
        await update.message.answer(
            "Welcome to our survey! Let's get started.\n\n"
            "First, what's your preferred way to learn?",
            reply_markup=create_options_keyboard({
                "learn_reading": "Reading",
                "learn_video": "Video tutorials",
                "learn_practice": "Hands-on practice"
            })
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            "Welcome to our survey! Let's get started.\n\n"
            "First, what's your preferred way to learn?",
            reply_markup=create_options_keyboard({
                "learn_reading": "Reading",
                "learn_video": "Video tutorials",
                "learn_practice": "Hands-on practice"
            })
        )
        await update.callback_query.answer()
    
    return "waiting_for_input"


async def learning_preference_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the learning preference node"""
    if not update.callback_query:
        # Only process callback queries
        return "waiting_for_input"
    
    callback_data = update.callback_query.data
    
    # Save the learning preference
    if not user.context:
        user.context = {}
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["learning_preference"] = callback_data
    await session.commit()
    
    # Determine next question based on learning preference
    if callback_data == "learn_reading":
        await update.callback_query.message.edit_text(
            "Great! You prefer reading.\n\n"
            "What kind of reading materials do you prefer?",
            reply_markup=create_options_keyboard({
                "reading_books": "Books",
                "reading_articles": "Articles",
                "reading_docs": "Documentation"
            })
        )
        await update.callback_query.answer()
        return "reading_branch"
    
    elif callback_data == "learn_video":
        await update.callback_query.message.edit_text(
            "Nice! You prefer video tutorials.\n\n"
            "What length of videos do you prefer?",
            reply_markup=create_options_keyboard({
                "video_short": "Short (< 10 min)",
                "video_medium": "Medium (10-30 min)",
                "video_long": "Long (> 30 min)"
            })
        )
        await update.callback_query.answer()
        return "video_branch"
    
    elif callback_data == "learn_practice":
        await update.callback_query.message.edit_text(
            "Excellent! You prefer hands-on practice.\n\n"
            "What type of practice do you prefer?",
            reply_markup=create_options_keyboard({
                "practice_guided": "Guided tutorials",
                "practice_challenges": "Coding challenges",
                "practice_projects": "Building projects"
            })
        )
        await update.callback_query.answer()
        return "practice_branch"
    
    return "waiting_for_input"


async def reading_branch_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the reading branch"""
    if not update.callback_query:
        # Only process callback queries
        return "reading_branch"
    
    callback_data = update.callback_query.data
    
    # Save the reading preference
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["reading_type"] = callback_data
    await session.commit()
    
    # Ask about frequency
    await update.callback_query.message.edit_text(
        f"You prefer {callback_data.replace('reading_', '')}.\n\n"
        "How often do you read technical content?",
        reply_markup=create_options_keyboard({
            "frequency_daily": "Daily",
            "frequency_weekly": "Weekly",
            "frequency_monthly": "Monthly"
        })
    )
    await update.callback_query.answer()
    
    return "frequency_question"


async def video_branch_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the video branch"""
    if not update.callback_query:
        # Only process callback queries
        return "video_branch"
    
    callback_data = update.callback_query.data
    
    # Save the video preference
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["video_length"] = callback_data
    await session.commit()
    
    # Ask about platform
    await update.callback_query.message.edit_text(
        f"You prefer {callback_data.replace('video_', '')} videos.\n\n"
        "Which platform do you use most for video tutorials?",
        reply_markup=create_options_keyboard({
            "platform_youtube": "YouTube",
            "platform_coursera": "Coursera",
            "platform_udemy": "Udemy"
        })
    )
    await update.callback_query.answer()
    
    return "platform_question"


async def practice_branch_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the practice branch"""
    if not update.callback_query:
        # Only process callback queries
        return "practice_branch"
    
    callback_data = update.callback_query.data
    
    # Save the practice preference
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["practice_type"] = callback_data
    await session.commit()
    
    # Ask about experience level
    await update.callback_query.message.edit_text(
        f"You prefer {callback_data.replace('practice_', '')}.\n\n"
        "What's your experience level?",
        reply_markup=create_options_keyboard({
            "experience_beginner": "Beginner",
            "experience_intermediate": "Intermediate",
            "experience_advanced": "Advanced"
        })
    )
    await update.callback_query.answer()
    
    return "experience_question"


async def frequency_question_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the frequency question"""
    if not update.callback_query:
        # Only process callback queries
        return "frequency_question"
    
    callback_data = update.callback_query.data
    
    # Save the frequency
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["frequency"] = callback_data
    await session.commit()
    
    # Go to summary
    return await go_to_summary(update, user, session)


async def platform_question_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the platform question"""
    if not update.callback_query:
        # Only process callback queries
        return "platform_question"
    
    callback_data = update.callback_query.data
    
    # Save the platform
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["platform"] = callback_data
    await session.commit()
    
    # Go to summary
    return await go_to_summary(update, user, session)


async def experience_question_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the experience question"""
    if not update.callback_query:
        # Only process callback queries
        return "experience_question"
    
    callback_data = update.callback_query.data
    
    # Save the experience
    if "survey_results" not in user.context:
        user.context["survey_results"] = {}
    
    user.context["survey_results"]["experience"] = callback_data
    await session.commit()
    
    # Go to summary
    return await go_to_summary(update, user, session)


async def go_to_summary(
    update: types.Update, 
    user: User, 
    session: AsyncSession
) -> str:
    """Transition to summary"""
    # Generate summary text based on user's answers
    survey_results = user.context.get("survey_results", {})
    
    summary_text = "📊 **Survey Results**\n\n"
    
    # Format the results for display
    for key, value in survey_results.items():
        # Clean up the keys and values for display
        display_key = key.replace("_", " ").title()
        display_value = value.split("_")[-1].title()
        summary_text += f"**{display_key}**: {display_value}\n"
    
    summary_text += "\nThank you for completing our survey!"
    
    # Show summary and option to restart
    await update.callback_query.message.edit_text(
        summary_text,
        reply_markup=create_options_keyboard({
            "restart_survey": "Take Survey Again",
            "exit_survey": "Exit Survey"
        }),
        parse_mode="Markdown"
    )
    await update.callback_query.answer()
    
    return "summary"


async def summary_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Handler for the summary node"""
    if not update.callback_query:
        # Only process callback queries
        return "summary"
    
    callback_data = update.callback_query.data
    
    if callback_data == "restart_survey":
        # Reset and restart the survey
        user.context["survey_results"] = {}
        await session.commit()
        
        await update.callback_query.message.edit_text(
            "Welcome back to our survey! Let's get started.\n\n"
            "First, what's your preferred way to learn?",
            reply_markup=create_options_keyboard({
                "learn_reading": "Reading",
                "learn_video": "Video tutorials",
                "learn_practice": "Hands-on practice"
            })
        )
        await update.callback_query.answer()
        
        return "waiting_for_input"
    
    elif callback_data == "exit_survey":
        # Exit the survey
        await update.callback_query.message.edit_text(
            "Thank you for participating in our survey!\n\n"
            "You can start a new survey anytime with the /survey command."
        )
        await update.callback_query.answer()
        
        # Reset the conversation state
        user.current_node = None
        await session.commit()
        
        return "exit"
    
    return "summary"


# Create nodes
survey_start_node = Node(
    name="survey_start",
    handler=survey_start_handler,
    transitions={
        "waiting_for_input": "learning_preference"
    }
)

learning_preference_node = Node(
    name="learning_preference",
    handler=learning_preference_handler,
    transitions={
        "waiting_for_input": "learning_preference",
        "reading_branch": "reading_branch",
        "video_branch": "video_branch",
        "practice_branch": "practice_branch"
    }
)

reading_branch_node = Node(
    name="reading_branch",
    handler=reading_branch_handler,
    transitions={
        "reading_branch": "reading_branch",
        "frequency_question": "frequency_question"
    }
)

video_branch_node = Node(
    name="video_branch",
    handler=video_branch_handler,
    transitions={
        "video_branch": "video_branch",
        "platform_question": "platform_question"
    }
)

practice_branch_node = Node(
    name="practice_branch",
    handler=practice_branch_handler,
    transitions={
        "practice_branch": "practice_branch",
        "experience_question": "experience_question"
    }
)

frequency_question_node = Node(
    name="frequency_question",
    handler=frequency_question_handler,
    transitions={
        "frequency_question": "frequency_question",
        "summary": "summary"
    }
)

platform_question_node = Node(
    name="platform_question",
    handler=platform_question_handler,
    transitions={
        "platform_question": "platform_question",
        "summary": "summary"
    }
)

experience_question_node = Node(
    name="experience_question",
    handler=experience_question_handler,
    transitions={
        "experience_question": "experience_question",
        "summary": "summary"
    }
)

summary_node = Node(
    name="summary",
    handler=summary_handler,
    transitions={
        "summary": "summary",
        "waiting_for_input": "learning_preference",
        "exit": None  # None means exit the conversation
    }
)


# Add nodes to the conversation graph
def register_survey_conversation():
    """Register all survey conversation nodes to the graph"""
    conversation_graph.add_node(survey_start_node)
    conversation_graph.add_node(learning_preference_node)
    conversation_graph.add_node(reading_branch_node)
    conversation_graph.add_node(video_branch_node)
    conversation_graph.add_node(practice_branch_node)
    conversation_graph.add_node(frequency_question_node)
    conversation_graph.add_node(platform_question_node)
    conversation_graph.add_node(experience_question_node)
    conversation_graph.add_node(summary_node)
    
    # Note: We don't set this as the initial node for the entire bot
    # Instead, we'll start this conversation explicitly with a command
