"""Метаданные проекта и сведения об авторе."""

APP_NAME = "CarPrice Predictor ML"
APP_VERSION = "2.2.0"
MODEL_VERSION = "v2.2"
TRAIN_SPLIT_LABEL = "80% обучение (164 авто) / 20% тест (41 авто)"

STUDENT_NAME = "Груздев Андрей Александрович"
STUDENT_GROUP = "Б.ПИН.ИИ.25.16"
SUPERVISOR_NAME = "Крутских Е.И."
UNIVERSITY_NAME = "ТвГТУ (Тверской государственный технический университет)"
DEPARTMENT_NAME = "Кафедра «Программное обеспечение»"
COURSE_TOPIC = "Разработка приложения на языке программирования Python для прогнозирования цен на автомобили"
COURSE_VARIANT = 2
TELEGRAM_BOT_HANDLE = "@testcursomsskm_bot"

USD_TO_RUB_RATE = 93.5
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5


def format_rub(amount: float) -> str:
    """Форматирует денежную сумму в рублях с пробелами между разрядами."""
    return f"{round(float(amount)):,.0f}".replace(",", " ") + " ₽"
