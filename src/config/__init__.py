"""Пакет конфигурации и констант проекта."""

from src.config.paths import (
    BASE_DIR,
    DATA_DIR,
    MODELS_DIR,
    REPORTS_DIR,
    FIGURES_DIR,
    SCREENSHOTS_DIR,
    STORAGE_DIR,
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    METRICS_PATH,
    METADATA_PATH,
    DB_FILE,
)
from src.config.meta import (
    APP_NAME,
    APP_VERSION,
    STUDENT_NAME,
    STUDENT_GROUP,
    UNIVERSITY_NAME,
    COURSE_TOPIC,
    COURSE_VARIANT,
    USD_TO_RUB_RATE,
    RANDOM_STATE,
    TEST_SIZE,
    CV_FOLDS,
)
from src.config.features import (
    BRAND_CORRECTIONS,
    WORD_NUM_MAP,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET_COL,
    ALLOWED_BRANDS,
    ALLOWED_BODIES,
    ALLOWED_FUELS,
    ALLOWED_ASPIRATIONS,
    ALLOWED_DRIVES,
)
from src.config.presets import (
    CAR_PRESETS,
    FEATURE_DEFAULTS,
    FEATURE_RANGES,
)
from src.config.benchmarks import (
    LOGINOM_BENCHMARKS,
    MODEL_NAMES,
    MODEL_FILE_MAP,
    PREPROCESSOR_FILE,
    MODEL_KEY_MAP,
)
