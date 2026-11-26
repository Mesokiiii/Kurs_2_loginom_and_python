"""Сервис загрузки моделей и выполнения прогноза цен."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
import joblib
import pandas as pd

from src.config import (
    MODELS_DIR,
    METRICS_PATH,
    MODEL_FILE_MAP,
    PREPROCESSOR_FILE,
    MODEL_KEY_MAP,
    MODEL_NAMES,
    MODEL_VERSION,
    USD_TO_RUB_RATE,
    RAW_DATA_PATH,
)
from src.data.transformer import CarDataPreprocessor
from src.data.validator import clamp_car_features
from src.models.confidence import (
    calculate_confidence_interval,
    calculate_price_probability,
    describe_price_probability,
)
from src.models.market_segment import calculate_percentile_and_category, compare_to_market

_KEY_TO_DISPLAY_NAME: Dict[str, str] = {MODEL_KEY_MAP[name]: name for name in MODEL_NAMES}


@dataclass
class PredictionResult:
    """Результат прогноза стоимости автомобиля."""
    model_name: str
    model_key: str
    price_usd: float
    price_rub: float
    ci_lower_usd: float
    ci_upper_usd: float
    ci_lower_rub: float
    ci_upper_rub: float
    market_percentile: float
    market_category: str
    comparison_to_average: str
    price_probability: float = 0.0
    model_version: str = MODEL_VERSION
    probability_band_low_rub: float = 0.0
    probability_band_high_rub: float = 0.0
    probability_level: str = ""
    clamped_warnings: List[str] = field(default_factory=list)


class ModelService:
    """Сервис инференса моделей прогнозирования цен."""

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self.models_dir = models_dir or MODELS_DIR
        self.models: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        self.preprocessor: Optional[CarDataPreprocessor] = None
        self.market_prices: List[float] = []
        self._load_artifacts()

    def _load_artifacts(self) -> None:
        prep_path = self.models_dir / PREPROCESSOR_FILE
        if prep_path.exists():
            self.preprocessor = CarDataPreprocessor.load(prep_path)

        for key, fname in MODEL_FILE_MAP.items():
            m_path = self.models_dir / fname
            if m_path.exists():
                self.models[key] = joblib.load(m_path)

        if METRICS_PATH.exists():
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                self.metrics = json.load(f)

        if RAW_DATA_PATH.exists():
            try:
                df = pd.read_csv(RAW_DATA_PATH)
                self.market_prices = df["price"].dropna().tolist() if "price" in df.columns else []
            except Exception:
                pass

    def get_available_models(self) -> List[str]:
        return list(MODEL_NAMES)

    def get_metrics_summary(self) -> Dict[str, Any]:
        return self.metrics

    def predict(self, car_features: Dict[str, Any], model_selection: Optional[str] = None) -> PredictionResult:
        model_key = MODEL_KEY_MAP.get(model_selection, "random_forest") if model_selection else "random_forest"
        model = self.models.get(model_key) or next(iter(self.models.values()))

        safe_features, clamped_warnings = clamp_car_features(car_features)
        x_trans = self.preprocessor.transform_dict(safe_features)
        price = max(1500.0, float(model.predict(x_trans)[0]))
        price_rub = round(price * USD_TO_RUB_RATE, 2)

        low, high = calculate_confidence_interval(model, x_trans, price, model_key, self.metrics)
        prob = calculate_price_probability(model, x_trans, price, model_key, self.metrics)
        prob_desc = describe_price_probability(prob, price_rub)
        pct, cat = calculate_percentile_and_category(price, self.market_prices)
        cmp_avg = compare_to_market(price, self.market_prices)

        return PredictionResult(
            model_name=_KEY_TO_DISPLAY_NAME.get(model_key, model_key),
            model_key=model_key,
            price_usd=round(price, 2),
            price_rub=price_rub,
            ci_lower_usd=round(low, 2),
            ci_upper_usd=round(high, 2),
            ci_lower_rub=round(low * USD_TO_RUB_RATE, 2),
            ci_upper_rub=round(high * USD_TO_RUB_RATE, 2),
            market_percentile=round(pct, 1),
            market_category=cat,
            comparison_to_average=cmp_avg,
            price_probability=prob,
            model_version=MODEL_VERSION,
            probability_band_low_rub=prob_desc["band_low_rub"],
            probability_band_high_rub=prob_desc["band_high_rub"],
            probability_level=prob_desc["level"],
            clamped_warnings=clamped_warnings,
        )

    def predict_all_models(self, car_features: Dict[str, Any]) -> List[PredictionResult]:
        """Возвращает прогнозы всех доступных моделей для сравнения."""
        return [self.predict(car_features, model_selection=name) for name in MODEL_NAMES]
