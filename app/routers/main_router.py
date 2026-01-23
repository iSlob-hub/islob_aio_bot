import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
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
from typing import Optional
from app.db.models import User, Notification, NotificationType, MorningQuiz, TrainingGoal
from app.keyboards import get_main_menu_keyboard, get_notifications_menu_keyboard, get_report_problem_keyboard
import app.text_constants as tc
from app.states import MorningQuizStates
from app.utils.bot_utils import is_valid_morning_time
from app.utils.text_templates import get_template, format_template, sync_get_template
from app.utils.morning_quiz_utils import (
    validate_transform_time,
    convert_time_to_datetime,
    create_gym_reminder_notification,
    get_active_morning_quiz_for_today,
)

KYIV_TIMEZONE = ZoneInfo("Europe/Kyiv")

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


def _normalize_sent_date(value: object) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


async def _daily_morning_quiz_already_sent(user_id: str) -> bool:
    notification = await Notification.find_one(
        Notification.user_id == str(user_id),
        Notification.notification_type == NotificationType.DAILY_MORNING_NOTIFICATION,
    )
    if not notification or not notification.system_data:
        return False
    last_sent_date = _normalize_sent_date(notification.system_data.get("last_sent_date"))
    if not last_sent_date:
        return False
    return last_sent_date == datetime.now(tz=KYIV_TIMEZONE).date()


async def _mark_daily_morning_quiz_sent(user_id: str) -> None:
    notification = await Notification.find_one(
        Notification.user_id == str(user_id),
        Notification.notification_type == NotificationType.DAILY_MORNING_NOTIFICATION,
    )
    if not notification:
        return
    if not notification.system_data:
        notification.system_data = {}
    notification.system_data["last_sent_date"] = datetime.now(tz=KYIV_TIMEZONE)
    await notification.save()


async def _send_morning_quiz_intro(message: Message, morning_quiz_id: str) -> None:
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


async def _start_morning_quiz_for_user(
    message: Message,
    *,
    is_test: bool,
    enforce_daily_limit: bool,
) -> None:
    user_telegram_id = message.from_user.id
    active_quiz = await get_active_morning_quiz_for_today(
        user_telegram_id,
        is_test=is_test,
    )
    if active_quiz:
        await _send_morning_quiz_intro(message, str(active_quiz.id))
        return

    if enforce_daily_limit and await _daily_morning_quiz_already_sent(user_telegram_id):
        await message.answer(text=await get_template("morning_quiz_already_completed"))
        return

    morning_quiz = MorningQuiz(
        user_id=str(user_telegram_id),
        is_test=is_test,
    )
    await morning_quiz.save()
    await _send_morning_quiz_intro(message, morning_quiz.id)
    if enforce_daily_limit:
        await _mark_daily_morning_quiz_sent(user_telegram_id)


async def _finalize_morning_quiz(
    message: Message,
    state: FSMContext,
    morning_quiz: MorningQuiz,
    weight_value: Optional[float],
    weight_display: str,
) -> None:
    gym_time_str = (
        morning_quiz.gym_attendance_time.strftime("%H:%M")
        if morning_quiz.gym_attendance_time
        else ""
    )
    gym_time_text = (
        f"Час відвідування спортзалу: <b>{gym_time_str}</b>.\n"
        if morning_quiz.is_going_to_gym and gym_time_str
        else ""
    )

    if morning_quiz.is_going_to_gym and morning_quiz.gym_attendance_time:
        await message.answer(
            text=await format_template(
                "morning_quiz_step5",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep,
                is_going_to_gym="Так",
                gym_attendance_time=gym_time_str,
                gym_attendance_time_text=gym_time_text,
                weight=weight_display,
            ),
            parse_mode="HTML",
            reply_markup=await _get_main_menu_keyboard_for_user(message.from_user.id),
        )
    else:
        await message.answer(
            text=await format_template(
                "morning_quiz_step51",
                how_do_you_feel_today=morning_quiz.how_do_you_feel_today,
                sleep_time=morning_quiz.how_many_hours_of_sleep,
                is_going_to_gym="Ні",
                gym_attendance_time_text=gym_time_text,
                weight=weight_display,
            ),
            parse_mode="HTML",
            reply_markup=await _get_main_menu_keyboard_for_user(message.from_user.id),
        )

    morning_quiz.weight = weight_value
    morning_quiz.completed = True
    await morning_quiz.save()

    if morning_quiz.is_going_to_gym and morning_quiz.gym_attendance_time:
        await create_gym_reminder_notification(
            user_id=str(message.from_user.id),
            gym_time=morning_quiz.gym_attendance_time,
        )

    await state.clear()
    await state.set_state(MainMenuState.main_menu)


async def _get_main_menu_keyboard_for_user(
    user_id: str,
) -> ReplyKeyboardMarkup:
    active_quiz = await get_active_morning_quiz_for_today(
        user_id,
        is_test=None,
    )
    return await get_main_menu_keyboard(
        include_morning_quiz_resume=bool(active_quiz),
    )


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


def _training_goal_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TrainingGoal.LOSE_WEIGHT.value)],
            [KeyboardButton(text=TrainingGoal.BUILD_MUSCLE.value)],
            [KeyboardButton(text=TrainingGoal.MAINTAIN_FITNESS.value)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _get_or_create_user(message: Message) -> User:
    user_telegram_id = message.from_user.id
    user_telegram_username = message.from_user.username
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user:
        return user

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
    return user


async def ensure_onboarding_not_finished(
    message: Message, state: FSMContext, user: Optional[User] = None
) -> bool:
    """
    Ensure the user finishes onboarding before accessing other menus.
    Returns True if we redirected the user to the pending question.
    """
    user = user or await _get_or_create_user(message)

    # Step 1: ask for the name if it's still the placeholder or empty
    if not user.full_name or user.full_name == "Поки невідомий користувач":
        await state.set_state(InitialConversationState.waiting_for_name)
        await message.answer(
            text=await get_template("intro_message"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return True

    # Step 2: morning notification time is required
    morning_notification = await Notification.find_one(
        Notification.user_id == str(message.from_user.id),
        Notification.notification_type == NotificationType.DAILY_MORNING_NOTIFICATION,
    )
    if not morning_notification:
        await state.set_state(
            InitialConversationState.waiting_for_morning_notification_time
        )
        await message.answer(
            text=await format_template(
                "first_interraction_morning_time_message", full_name=user.full_name
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return True

    # Step 3: training goal (also final verification flag)
    if not user.is_verified:
        await state.set_state(InitialConversationState.waiting_for_training_goal)
        await message.answer(
            text=await format_template("training_goal_question"),
            reply_markup=_training_goal_keyboard(),
        )
        return True

    return False


@main_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:

    user_telegram_id = message.from_user.id

    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    if user and user.is_verified:

        if await ensure_onboarding_not_finished(message, state, user):
            return

        await message.answer(
            text=await format_template(
                "start_command",
                full_name=user.full_name
            ),
            reply_markup=await _get_main_menu_keyboard_for_user(message.from_user.id),
        )
        await state.set_state(MainMenuState.main_menu)
        return

    user = user or await _get_or_create_user(message)

    # Redirect user to the exact onboarding step they stopped at
    await ensure_onboarding_not_finished(message, state, user)


@main_router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """
    Universal command to return to main menu from any state
    """
    user_telegram_id = message.from_user.id
    user = await User.find_one(User.telegram_id == str(user_telegram_id))
    
    # Only verified users can use this command; otherwise continue onboarding
    if await ensure_onboarding_not_finished(message, state, user):
        return
    
    # Return to main menu
    await state.set_state(MainMenuState.main_menu)
    await message.answer(
        text=await get_template("menu_command"),
        reply_markup=await _get_main_menu_keyboard_for_user(message.from_user.id),
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
            # Конвертуємо час користувача в київський час для збереження в БД
            timezone_offset = user.timezone_offset or 0
            
            try:
                user_hour, user_minute = map(int, time_str.split(':'))
            except ValueError:
                await message.answer(
                    text=await get_template("invalid_time"),
                    reply_markup=ReplyKeyboardRemove(),
                )
                return
            
            # Віднімаємо офсет користувача, щоб отримати київський час
            kyiv_hour = user_hour - timezone_offset
            
            # Обробка переходу через межу доби
            if kyiv_hour < 0:
                kyiv_hour += 24
            elif kyiv_hour >= 24:
                kyiv_hour -= 24
            
            kyiv_time_str = f"{kyiv_hour:02d}:{user_minute:02d}"
            
            notification = Notification(
                user_id=str(user_telegram_id),
                notification_time=kyiv_time_str,
                notification_time_base=time_str,  # Зберігаємо оригінальний час користувача
                notification_text="",
                notification_type=NotificationType.DAILY_MORNING_NOTIFICATION,
            )
            await notification.save()
            
            # Ask for training goal next
            await message.answer(
                text=await format_template("training_goal_question"),
                reply_markup=_training_goal_keyboard(),
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

        # Create a template after training notification to store user's preferred time
        # This will be used as a template when creating actual notifications after training
        template_notification = Notification(
            user_id=str(user_telegram_id),
            notification_time="15:00",  # Default time - user can change via web app
            notification_time_base="15:00",  # За замовчуванням той самий час
            notification_text="Шаблон сповіщення після тренування",
            notification_type=NotificationType.AFTER_TRAINING_NOTIFICATION,
            is_active=False,  # Template, never active
            system_data={"is_template": True}  # Mark as template
        )
        await template_notification.save()

        # Complete the setup and go to main menu
        await state.set_state(MainMenuState.main_menu)
        await message.answer(
            text=await format_template(
                "training_goal_setup_finished", 
                goal=user.training_goal.value
            ),
            reply_markup=await _get_main_menu_keyboard_for_user(message.from_user.id),
        )


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == sync_get_template("training_menu_button")
)
async def process_training_menu(message: Message, state: FSMContext) -> None:
    if await ensure_onboarding_not_finished(message, state):
        return
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
    if await ensure_onboarding_not_finished(message, state):
        return
    await message.answer(
        text=await get_template("what_do_with_notifications"),
        reply_markup=await get_notifications_menu_keyboard(),
    )
    await state.set_state(MainMenuState.notifications_menu)


@main_router.message(
    StateFilter(MainMenuState.main_menu), F.text == sync_get_template("report_problem_button")
)
async def process_report_problem(message: Message, state: FSMContext) -> None:
    if await ensure_onboarding_not_finished(message, state):
        return
    await message.answer(
        text=await get_template("describe_problem_prompt"),
        reply_markup=await get_report_problem_keyboard(),
    )
    await state.set_state(MainMenuState.report_problem)


@main_router.message(
    StateFilter(MainMenuState.main_menu),
    F.text == sync_get_template(
        "continue_morning_quiz_button",
        tc.CONTINUE_MORNING_QUIZ_BUTTON,
    ),
)
async def process_continue_morning_quiz(message: Message, state: FSMContext) -> None:
    if await ensure_onboarding_not_finished(message, state):
        return
    active_quiz = await get_active_morning_quiz_for_today(
        message.from_user.id,
        is_test=None,
    )
    if active_quiz:
        await _send_morning_quiz_intro(message, str(active_quiz.id))
        return

    await _start_morning_quiz_for_user(
        message,
        is_test=False,
        enforce_daily_limit=True,
    )


@main_router.message(Command("morning_quiz"), StateFilter(MainMenuState.main_menu))
async def cmd_morning_quiz(message: Message, state: FSMContext) -> None:
    if await ensure_onboarding_not_finished(message, state):
        return
    await _start_morning_quiz_for_user(
        message,
        is_test=False,
        enforce_daily_limit=True,
    )


@main_router.message(Command("morning_quiz_test"), StateFilter(MainMenuState.main_menu))
async def cmd_morning_quiz_test(message: Message, state: FSMContext) -> None:
    if await ensure_onboarding_not_finished(message, state):
        return
    await _start_morning_quiz_for_user(
        message,
        is_test=True,
        enforce_daily_limit=False,
    )


@main_router.message(StateFilter(MainMenuState.main_menu), ~F.text.regexp(r"^/"))
async def process_main_menu(message: Message, state: FSMContext) -> None:

    if await ensure_onboarding_not_finished(message, state):
        return

    active_quiz = await get_active_morning_quiz_for_today(
        message.from_user.id,
        is_test=None,
    )
    if active_quiz:
        await state.update_data(morning_quiz_id=str(active_quiz.id))

        if (
            active_quiz.how_do_you_feel_today is not None
            and active_quiz.how_many_hours_of_sleep is None
        ):
            await state.set_state(MorningQuizStates.waiting_for_how_many_hours_of_sleep)
            sleep_time_str = message.text.strip()
            sleep_time = validate_transform_time(sleep_time_str)
            if sleep_time is None:
                await message.answer(text=await get_template("invalid_time"))
                return
            active_quiz.how_many_hours_of_sleep = sleep_time
            await active_quiz.save()
            await message.answer(
                text=await format_template(
                    "morning_quiz_step2",
                    how_do_you_feel_today=active_quiz.how_do_you_feel_today,
                    sleep_time=sleep_time,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Так",
                                callback_data="is_going_to_gym_yes",
                            ),
                            InlineKeyboardButton(
                                text="Ні",
                                callback_data="is_going_to_gym_no",
                            ),
                        ]
                    ]
                ),
                parse_mode="HTML",
            )
            await state.set_state(MorningQuizStates.waiting_for_is_going_to_gym)
            return

        if active_quiz.is_going_to_gym and active_quiz.gym_attendance_time is None:
            await state.set_state(MorningQuizStates.waiting_for_gym_attendance_time)
            gym_attendance_time = message.text.strip()
            if not gym_attendance_time:
                await message.answer(await get_template("enter_gym_attendance_time"))
                return

            gym_attendance_time_dt = convert_time_to_datetime(gym_attendance_time)
            if gym_attendance_time_dt is None:
                await message.answer(await get_template("invalid_time"))
                return

            active_quiz.gym_attendance_time = gym_attendance_time_dt
            await active_quiz.save()
            await create_gym_reminder_notification(
                user_id=str(message.from_user.id),
                gym_time=gym_attendance_time_dt,
            )
            await message.answer(
                text=await format_template(
                    "morning_quiz_step41",
                    how_do_you_feel_today=active_quiz.how_do_you_feel_today,
                    sleep_time=active_quiz.how_many_hours_of_sleep,
                    gym_attendance_time=gym_attendance_time_dt.strftime("%H:%M"),
                ),
                reply_markup=None,
                parse_mode="HTML",
            )
            await state.set_state(MorningQuizStates.waiting_for_weight)
            return

        if (
            active_quiz.weight is None
            and active_quiz.is_going_to_gym is not None
            and (
                not active_quiz.is_going_to_gym
                or active_quiz.gym_attendance_time is not None
            )
        ):
            await state.set_state(MorningQuizStates.waiting_for_weight)
            weight_str = message.text.strip()
            try:
                weight = float(weight_str)
            except ValueError:
                await message.answer(await get_template("invalid_weight"))
                return

            if weight > 200 or weight < 40:
                await message.answer(await get_template("invalid_weight"))
                return

            await _finalize_morning_quiz(
                message=message,
                state=state,
                morning_quiz=active_quiz,
                weight_value=weight,
                weight_display=f"{weight}",
            )
            return

    await message.answer(
        text=await get_template("select_option"),
        reply_markup=await _get_main_menu_keyboard_for_user(message.from_user.id),
    )
