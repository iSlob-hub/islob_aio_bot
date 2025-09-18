import re
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from app.db.models import User, Notification, NotificationType, MorningQuiz, TrainingGoal
from app.keyboards import get_main_menu_keyboard, get_notifications_menu_keyboard
from app.utils.bot_utils import is_valid_morning_time
from app.utils.text_templates import get_template, format_template, sync_get_template

def generate_username_from_name(full_name: str) -> str:
    if not full_name:
        return "user"
    
    clean_name = re.sub(r'[^a-zA-Zа-яА-Я0-9\s]', '', full_name.lower())
    username = re.sub(r'\s+', '_', clean_name.strip())

    if len(username) > 32:
        username = username[:32]

    if not username:
        return "user"
        
    return username


class InitialConversationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_morning_notification_time = State()
    waiting_for_training_goal = State()


class MainMenuState(StatesGroup):
    training_menu = State()
    notifications_menu = State()
    report_problem = State()
    main_menu = State()


main_router = Router()


@main_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:

    user_telegram_id = message.from_user.id
    user_telegram_username = message.from_user.username

    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user and user.is_verified:

        await message.answer(
            text=await format_template(
                "start_command",
                full_name=user.full_name
            ),
            reply_markup=await get_main_menu_keyboard(),
        )
        await state.set_state(MainMenuState.main_menu)
        return

    if not user:
        generated_username = user_telegram_username or generate_username_from_name(
            message.from_user.full_name or "Поки невідомий користувач"
        )
        
        user = User(
            telegram_id=str(user_telegram_id),
            telegram_username=generated_username,
            is_verified=False,
            full_name=message.from_user.full_name or "Поки невідомий користувач",
            training_goal=TrainingGoal.MAINTAIN_FITNESS,  # Default goal
        )
        await user.save()
    await state.set_state(InitialConversationState.waiting_for_name)
    await message.answer(
        text=await get_template("intro_message"),
        reply_markup=ReplyKeyboardRemove(),
    )


@main_router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """
    Universal command to return to main menu from any state
    """
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    
    # Only verified users can use this command
    if not user or not user.is_verified:
        # If user is not verified, treat it like /start
        return await cmd_start(message, state)
    
    # Return to main menu
    await state.set_state(MainMenuState.main_menu)
    await message.answer(
        text=await get_template("menu_command"),
        reply_markup=await get_main_menu_keyboard(),
    )


@main_router.message(StateFilter(InitialConversationState.waiting_for_name))
async def process_name(message: Message, state: FSMContext) -> None:
    user_name = message.text
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user:
        user.full_name = user_name
        user.is_verified
        await user.save()
        await state.set_state(
            InitialConversationState.waiting_for_morning_notification_time
        )
        await message.answer(
            text=await format_template(
                "first_interraction_morning_time_message",
                full_name=user.full_name
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            await get_template("sorry_issue_happened"),
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(InitialConversationState.waiting_for_name)


@main_router.message(
    StateFilter(InitialConversationState.waiting_for_morning_notification_time)
)
async def process_morning_notification_time(
    message: Message, state: FSMContext
) -> None:
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user:
        time_str = message.text
        if is_valid_morning_time(time_str):
            notification = Notification(
                user_id=str(user_telegram_id),
                notification_time=time_str,
                notification_text="",
                notification_type=NotificationType.DAILY_MORNING_NOTIFICATION,
            )
            await notification.save()
            
            # Ask for training goal next
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=TrainingGoal.LOSE_WEIGHT.value)],
                    [KeyboardButton(text=TrainingGoal.BUILD_MUSCLE.value)],
                    [KeyboardButton(text=TrainingGoal.MAINTAIN_FITNESS.value)]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            await message.answer(
                text=await format_template("training_goal_question"),
                reply_markup=keyboard,
            )
            
            # Set the state to waiting for training goal
            await state.set_state(InitialConversationState.waiting_for_training_goal)
        else:
            await message.answer(
                text=await get_template("invalid_time"),
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.set_state(
                InitialConversationState.waiting_for_morning_notification_time
            )


@main_router.message(
    StateFilter(InitialConversationState.waiting_for_training_goal)
)
async def process_training_goal(
    message: Message, state: FSMContext
) -> None:
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user:
        training_goal_text = message.text
        
        # Map the text to enum value
        if training_goal_text == "Зниженя ваги":
            user.training_goal = TrainingGoal.LOSE_WEIGHT
        elif training_goal_text == "Набір м'язової маси":
            user.training_goal = TrainingGoal.BUILD_MUSCLE
        elif training_goal_text == "Підтримка форми":
            user.training_goal = TrainingGoal.MAINTAIN_FITNESS
        else:
            # Default option if the text doesn't match
            user.training_goal = TrainingGoal.MAINTAIN_FITNESS
        
        # Set user as verified and save
        user.is_verified = True
        await user.save()
        
        # Complete the setup and go to main menu
        await state.set_state(MainMenuState.main_menu)
        await message.answer(
            text=await format_template(
                "training_goal_setup_finished", 
                goal=user.training_goal.value
            ),
            reply_markup=await get_main_menu_keyboard(),
        )


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == sync_get_template("training_menu_button")
)
async def process_training_menu(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await get_template("what_do_with_training"),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=await get_template("start_training_button")),
                ],
                [
                    KeyboardButton(text=await get_template("back_to_main_menu_button"))
                ]
            ],
            resize_keyboard=True,
        ),
    )
    await state.set_state(MainMenuState.training_menu)


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == sync_get_template("notifications_menu_button")
)
async def process_notifications_menu(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await get_template("what_do_with_notifications"),
        reply_markup=await get_notifications_menu_keyboard(),
    )
    await state.set_state(MainMenuState.notifications_menu)


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == sync_get_template("report_problem_button")
)
async def process_report_problem(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=await get_template("describe_problem_prompt"),
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(MainMenuState.report_problem)


@main_router.message(Command("morning_quiz"), StateFilter(MainMenuState.main_menu))
async def cmd_morning_quiz(message: Message, state: FSMContext) -> None:
    user_telegram_id = message.from_user.id
    morning_quiz = MorningQuiz(
        user_id=str(user_telegram_id),
    )
    await morning_quiz.save()
    morning_quiz_id = morning_quiz.id

    await message.answer(
        text=await get_template("morning_quiz_intro"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=await get_template("start_quiz_button"),
                        callback_data=f"start_morning_quiz_{morning_quiz_id}",
                    )
                ]
            ]
        ),
    )


@main_router.message(StateFilter(MainMenuState.main_menu))
async def process_main_menu(message: Message, state: FSMContext) -> None:

    await message.answer(
        text=await get_template("select_option"),
        reply_markup=await get_main_menu_keyboard(),
    )
