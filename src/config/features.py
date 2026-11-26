"""Схемы признаков и словари нормализации данных."""

from typing import Dict, List

BRAND_CORRECTIONS: Dict[str, str] = {
    "vokswagen": "volkswagen",
    "vw": "volkswagen",
    "maxda": "mazda",
    "porcshce": "porsche",
    "toyouta": "toyota",
    "alfa-romero": "alfa-romeo",
}

WORD_NUM_MAP: Dict[str, int] = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "eight": 8,
    "twelve": 12,
}

CATEGORICAL_FEATURES: List[str] = [
    "brand",
    "fueltype",
    "aspiration",
    "carbody",
    "drivewheel",
    "enginelocation",
    "enginetype",
    "fuelsystem",
]

NUMERICAL_FEATURES: List[str] = [
    "wheelbase",
    "carlength",
    "carwidth",
    "curbweight",
    "enginesize",
    "boreratio",
    "horsepower",
    "citympg",
    "highwaympg",
    "doornumber",
    "cylindernumber",
    "power_to_weight",
    "engine_to_weight",
]

TARGET_COL = "price"

ALLOWED_BRANDS: List[str] = [
    "toyota", "nissan", "mazda", "honda", "mitsubishi",
    "subaru", "volkswagen", "volvo", "peugeot", "bmw",
    "dodge", "buick", "audi", "plymouth", "saab",
    "porsche", "isuzu", "jaguar", "chevrolet", "renault",
    "mercury", "alfa-romeo",
]

ALLOWED_BODIES: List[str] = ["sedan", "hatchback", "wagon", "hardtop", "convertible"]
ALLOWED_FUELS: List[str] = ["gas", "diesel"]
ALLOWED_ASPIRATIONS: List[str] = ["std", "turbo"]
ALLOWED_DRIVES: List[str] = ["fwd", "rwd", "4wd"]

DRIVE_LABELS: Dict[str, str] = {
    "fwd": "Передний привод (FWD)",
    "rwd": "Задний привод (RWD)",
    "4wd": "Полный привод (4WD)",
}

BODY_LABELS: Dict[str, str] = {
    "sedan": "Седан",
    "hatchback": "Хэтчбек",
    "wagon": "Универсал",
    "hardtop": "Хардтоп (купе)",
    "convertible": "Кабриолет",
}

FUEL_LABELS: Dict[str, str] = {
    "gas": "Бензин",
    "diesel": "Дизель",
}

ASPIRATION_LABELS: Dict[str, str] = {
    "std": "Атмосферный",
    "turbo": "Турбированный (турбо)",
}
