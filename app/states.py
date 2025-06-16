from aiogram.fsm.state import State, StatesGroup


class NotificationsState(StatesGroup):
    creating_notification_request_text = State()
    creating_notification_request_frequency = State()
    creating_notification_request_weekdays = State()
    creating_notification_request_monthdays = State()
    creating_notification_request_time = State()
    creating_notification_finalize = State()
    viewing_notifications = State()


class TrainingState(StatesGroup):
    how_do_you_feel_before = State()
    training_started = State()
    how_hard_was_training = State()
    do_you_have_any_pain = State()


class AfterTrainingState(StatesGroup):
    start_training_quiz = State()
    do_you_have_soreness = State()
    stress_level = State()


class MorningQuizStates(StatesGroup):
    waiting_for_how_do_you_feel_today = State()
    waiting_for_how_many_hours_of_sleep = State()
    waiting_for_weight = State()
    waiting_for_is_going_to_gym = State()
    waiting_for_gym_attendance_time = State()
