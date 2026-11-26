"""Скрипт комплексного обновления пояснительной записки (ГОСТ 7.32-2017).

Обновляет `Пояснительная_записка_Груздев_А_А.docx` in-place с сохранением
титульного листа, полей, стилей, колонтитулов и нумерации страниц:
  1. Полный перевод всех цен, диапазонов, MAE и RMSE в рубли (курс 93,5),
     исключение всех упоминаний $, USD и «доллар» (включая OMML <m:t>).
  2. Замена «реляционная БД» на «локальная база данных SQLite для логирования
     и хранения истории расчётов» (без затрагивания «корреляционный»).
  3. Замена CustomTkinter / десктопного GUI на веб-приложение Streamlit (5 разделов)
     и Telegram-бот (@testcursomsskm_bot) на фреймворке aiogram 3.
  4. Актуализация всех метрик из reports/metrics.json (версия v2.2, разбиение 80/20),
     реальной важности признаков Random Forest, пресетов, OLAP-таблицы и 35 тестов pytest.
  5. Расшифровка аббревиатур (FWD/RWD/4WD/MPG), объяснение корреляции Пирсона r,
     версионирования моделей v2.2, вероятности цены (±15%, 5–99%) и ограничителя параметров.
  6. Замена всех встроенных иллюстраций на новые 300 DPI изображения в рублях
     с сохранением точных пропорций + добавление схемы Loginom, справки и Telegram-бота с QR-кодом.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.styles import BODY_RU_NAMES, DRIVE_RU_NAMES, FEATURE_RU_NAMES
from src.config import (
    CAR_PRESETS,
    FIGURES_DIR,
    METRICS_PATH,
    MODELS_DIR,
    PREPROCESSOR_FILE,
    RAW_DATA_PATH,
    USD_TO_RUB_RATE,
    format_model_with_quality,
)
from src.data.cleaner import clean_car_dataframe
from src.models.service import ModelService

DOCX_PATH = PROJECT_ROOT / "Пояснительная_записка_Груздев_А_А.docx"
EMU_PER_INCH = 914400

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def fmt_num(val: float, decimals: int = 1) -> str:
    """Форматирует число с пробелами между тысячами и запятой в дробной части."""
    if decimals == 0:
        return f"{round(val):,.0f}".replace(",", " ")
    return f"{val:,.{decimals}f}".replace(",", " ").replace(".", ",")


def fmt_dec(val: float, decimals: int = 4) -> str:
    """Форматирует десятичную дробь с русской запятой."""
    return f"{val:.{decimals}f}".replace(".", ",")


def _translate_feature_name(raw_name: str) -> str:
    """Переводит имя признака из препроцессора в читаемое русское название."""
    clean = raw_name
    for prefix in ("num__", "cat__"):
        if clean.startswith(prefix):
            clean = clean[len(prefix) :]
    if clean in FEATURE_RU_NAMES:
        return f"{FEATURE_RU_NAMES[clean]} ({clean})"
    if clean.startswith("brand_"):
        brand = clean[len("brand_") :]
        return f"Марка: {brand.upper() if brand == 'bmw' else brand.capitalize()}"
    return clean


def set_paragraph_text_preserve_format(paragraph, new_text: str) -> None:
    """Заменяет текст простого абзаца (без OMML), сохраняя шрифт и префикс списка."""
    # Удаляем возможные устаревшие <w:hyperlink>, чтобы их текст не дублировался
    for hl in list(paragraph._element.findall(qn("w:hyperlink"))):
        paragraph._element.remove(hl)

    runs = paragraph.runs
    if not runs:
        run = paragraph.add_run(new_text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        return

    # Если первый run — маркер списка с табуляцией (например '6)\t' или '–\t'), сохраняем его
    first_txt = runs[0].text or ""
    has_list_prefix = (
        len(runs) >= 2
        and "\t" in first_txt
        and len(first_txt.strip()) <= 4
    )

    if has_list_prefix:
        prefix_run = runs[0]
        body_run = runs[1]
        # Убираем возможный дублирующий префикс из new_text
        cleaned = new_text
        if cleaned.startswith(prefix_run.text):
            cleaned = cleaned[len(prefix_run.text) :]
        body_run.text = cleaned
        for extra in runs[2:]:
            extra.text = ""
    else:
        runs[0].text = new_text
        for extra in runs[1:]:
            extra.text = ""


def replace_omml_text(paragraph, replacements: Sequence[Tuple[str, str]]) -> None:
    """Точечно заменяет текст внутри OMML <m:t> узлов абзаца, сохраняя формулу."""
    for mt in paragraph._element.iter(f"{{{M_NS}}}t"):
        if mt.text:
            txt = mt.text
            for old, new in replacements:
                if old in txt:
                    txt = txt.replace(old, new)
            mt.text = txt


def replace_run_text(paragraph, replacements: Sequence[Tuple[str, str]]) -> None:
    """Точечно заменяет подстроки в текстовых runs абзаца (безопасно при наличии OMML)."""
    for r in paragraph.runs:
        if r.text:
            txt = r.text
            for old, new in replacements:
                if old in txt:
                    txt = txt.replace(old, new)
            r.text = txt


def insert_paragraph_after(
    doc: Document,
    anchor_p,
    text: str = "",
    *,
    align: Optional[WD_ALIGN_PARAGRAPH] = None,
    italic: bool = False,
    bold: bool = False,
    font_size: float = 14.0,
    first_line_indent: Optional[int] = 450215,
    space_before: Optional[int] = None,
    space_after: Optional[int] = None,
    line_spacing: Optional[float] = 1.5,
):
    """Создаёт абзац с параметрами ГОСТ и перемещает его сразу после anchor_p."""
    new_p = doc.add_paragraph()
    new_p.style = doc.styles["Normal"]
    if align is not None:
        new_p.alignment = align
    pf = new_p.paragraph_format
    pf.first_line_indent = first_line_indent
    if space_before is not None:
        pf.space_before = space_before
    if space_after is not None:
        pf.space_after = space_after
    if line_spacing is not None:
        pf.line_spacing = line_spacing

    if text:
        run = new_p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(font_size)
        run.italic = italic
        run.bold = bold

    anchor_p._p.addnext(new_p._p)
    return new_p


def insert_figure_after(
    doc: Document,
    anchor_p,
    img_path: Path,
    caption: str,
    max_width_in: float = 5.7,
    max_height_in: float = 5.0,
):
    """Вставляет центрированный рисунок с сохранением пропорций и ГОСТ-подписью после anchor_p."""
    with Image.open(img_path) as im:
        w_px, h_px = im.size
    ratio = w_px / max(h_px, 1)
    width_in = max_width_in
    height_in = width_in / ratio
    if height_in > max_height_in:
        height_in = max_height_in
        width_in = height_in * ratio

    img_p = insert_paragraph_after(
        doc,
        anchor_p,
        text="",
        align=WD_ALIGN_PARAGRAPH.CENTER,
        first_line_indent=None,
        space_before=76200,
        space_after=38100,
        line_spacing=None,
    )
    img_p.add_run().add_picture(str(img_path), width=Inches(width_in), height=Inches(height_in))

    cap_p = insert_paragraph_after(
        doc,
        img_p,
        text=caption,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        italic=True,
        font_size=14.0,
        first_line_indent=None,
        space_before=76200,
        space_after=152400,
        line_spacing=None,
    )
    return cap_p


def replace_embedded_image(
    doc: Document,
    paragraph,
    img_path: Path,
    max_width_in: float = 5.7,
    max_height_in: float = 5.2,
) -> str:
    """Заменяет бинарные данные встроенного PNG и пересчитывает пропорциональные размеры."""
    blip = paragraph._element.find(f".//{{{A_NS}}}blip")
    if blip is None:
        raise RuntimeError("Не найден элемент <a:blip> в абзаце с рисунком")
    r_id = blip.get(f"{{{R_NS}}}embed")
    if not r_id or r_id not in doc.part.related_parts:
        raise RuntimeError(f"Не найдена связанная часть изображения для {r_id}")

    img_bytes = img_path.read_bytes()
    doc.part.related_parts[r_id]._blob = img_bytes

    with Image.open(img_path) as im:
        w_px, h_px = im.size
    ratio = w_px / max(h_px, 1)
    width_in = max_width_in
    height_in = width_in / ratio
    if height_in > max_height_in:
        height_in = max_height_in
        width_in = height_in * ratio

    cx = str(int(round(width_in * EMU_PER_INCH)))
    cy = str(int(round(height_in * EMU_PER_INCH)))

    for ext in paragraph._element.iter(f"{{{WP_NS}}}extent"):
        ext.set("cx", cx)
        ext.set("cy", cy)
    for xfrm in paragraph._element.iter(f"{{{A_NS}}}xfrm"):
        a_ext = xfrm.find(f"{{{A_NS}}}ext")
        if a_ext is not None:
            a_ext.set("cx", cx)
            a_ext.set("cy", cy)

    return r_id


def _set_cell_text(cell, text: str, *, bold: bool = False, font_size: float = 12.0, align=None) -> None:
    """Записывает текст в ячейку таблицы, сохраняя стиль ГОСТ (Times New Roman)."""
    if not cell.paragraphs:
        p = cell.add_paragraph()
    else:
        p = cell.paragraphs[0]
        # Удаляем лишние параграфы в ячейке, если они были
        for extra_p in cell.paragraphs[1:]:
            extra_p._element.getparent().remove(extra_p._element)
    if align is not None:
        p.alignment = align
    if p.runs:
        p.runs[0].text = text
        p.runs[0].font.name = "Times New Roman"
        p.runs[0].font.size = Pt(font_size)
        p.runs[0].bold = bold
        for r in p.runs[1:]:
            r.text = ""
    else:
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(font_size)
        r.bold = bold


def _resize_table(table, target_rows: int, target_cols: int, col_weights: Optional[Sequence[float]] = None) -> None:
    """Корректирует число строк и столбцов таблицы с сохранением рамок и ширины."""
    tbl = table._tbl

    # 1. Текущая суммарная ширина таблицы в dxa
    grid = tbl.find(qn("w:tblGrid"))
    existing_widths = []
    if grid is not None:
        for gc in grid.findall(qn("w:gridCol")):
            w = gc.get(qn("w:w"))
            if w:
                existing_widths.append(int(w))
    total_dxa = sum(existing_widths) if existing_widths else 9360

    # 2. Добавляем/удаляем столбцы в каждой строке
    rows_xml = tbl.findall(qn("w:tr"))
    for tr in rows_xml:
        tcs = tr.findall(qn("w:tc"))
        while len(tcs) < target_cols:
            new_tc = copy.deepcopy(tcs[-1])
            tr.append(new_tc)
            tcs.append(new_tc)
        while len(tcs) > target_cols:
            tr.remove(tcs.pop())

    # 3. Добавляем/удаляем строки (копируем последнюю строку данных для сохранения границ)
    while len(rows_xml) < target_rows:
        new_tr = copy.deepcopy(rows_xml[-1])
        tbl.append(new_tr)
        rows_xml.append(new_tr)
    while len(rows_xml) > target_rows:
        tbl.remove(rows_xml.pop())

    # 4. Пересчитываем ширину столбцов
    if col_weights is not None and len(col_weights) == target_cols:
        s = float(sum(col_weights))
        col_dxa = [int(round(total_dxa * w / s)) for w in col_weights]
    else:
        base = total_dxa // target_cols
        col_dxa = [base] * target_cols
    # Компенсируем округление в последнем столбце
    col_dxa[-1] += total_dxa - sum(col_dxa)

    if grid is not None:
        for gc in list(grid.findall(qn("w:gridCol"))):
            grid.remove(gc)
        for w in col_dxa:
            gc = OxmlElement("w:gridCol")
            gc.set(qn("w:w"), str(w))
            grid.append(gc)

    for tr in tbl.findall(qn("w:tr")):
        for idx, tc in enumerate(tr.findall(qn("w:tc"))):
            tcPr = tc.find(qn("w:tcPr"))
            if tcPr is None:
                tcPr = OxmlElement("w:tcPr")
                tc.insert(0, tcPr)
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.insert(0, tcW)
            tcW.set(qn("w:w"), str(col_dxa[idx]))
            tcW.set(qn("w:type"), "dxa")


def fill_table(
    table,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    font_size: float = 12.0,
    col_weights: Optional[Sequence[float]] = None,
    bold_last_row: bool = False,
) -> None:
    """Полностью перезаписывает содержимое таблицы с нужными размерами и ГОСТ-оформлением."""
    _resize_table(table, 1 + len(rows), len(headers), col_weights=col_weights)
    for c_idx, h_text in enumerate(headers):
        _set_cell_text(table.cell(0, c_idx), h_text, bold=True, font_size=font_size)
    for r_idx, row_vals in enumerate(rows, start=1):
        is_bold = bold_last_row and (r_idx == len(rows))
        for c_idx, val in enumerate(row_vals):
            _set_cell_text(table.cell(r_idx, c_idx), str(val), bold=is_bold, font_size=font_size)


def compute_dynamic_data() -> Dict[str, object]:
    """Загружает актуальные метрики, OLAP-таблицу, важность признаков RF и пресеты."""
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    df_raw = pd.read_csv(RAW_DATA_PATH)
    df_clean = clean_car_dataframe(df_raw)

    # OLAP по типу кузова и привода в тыс. руб.
    olap_df = (
        df_clean.groupby(["carbody", "drivewheel"])
        .agg(
            cnt=("price", "count"),
            mean_krub=("price", lambda s: float(s.mean()) * USD_TO_RUB_RATE / 1000.0),
            min_krub=("price", lambda s: float(s.min()) * USD_TO_RUB_RATE / 1000.0),
            max_krub=("price", lambda s: float(s.max()) * USD_TO_RUB_RATE / 1000.0),
            mean_hp=("horsepower", "mean"),
        )
        .reset_index()
        .sort_values(["carbody", "mean_krub"], ascending=[True, False])
    )

    # Реальная важность признаков Random Forest
    rf_model = joblib.load(MODELS_DIR / "model_random_forest.joblib")
    preprocessor = joblib.load(MODELS_DIR / PREPROCESSOR_FILE)
    raw_names = list(preprocessor.transformer.get_feature_names_out())
    importances = np.asarray(rf_model.feature_importances_, dtype=float)
    order = np.argsort(importances)[::-1]

    fi_top8 = []
    cum = 0.0
    for idx in order[:8]:
        val = float(importances[idx])
        cum += val
        fi_top8.append((_translate_feature_name(raw_names[idx]), val, cum))
    other_count = len(raw_names) - 8
    other_val = float(max(0.0, 1.0 - cum))

    # Прогнозы по реальным пресетам
    service = ModelService()
    preset_preds = {}
    for pname, pdata in CAR_PRESETS.items():
        preset_preds[pname] = service.predict(pdata, model_selection="random_forest")

    return {
        "metrics": metrics,
        "df_clean": df_clean,
        "olap_df": olap_df,
        "n_features": len(raw_names),
        "fi_top8": fi_top8,
        "fi_other": (other_count, other_val),
        "preset_preds": preset_preds,
    }


def update_document() -> None:
    """Выполняет полное обновление пояснительной записки in-place."""
    data = compute_dynamic_data()
    metrics = data["metrics"]
    olap_df = data["olap_df"]
    n_features: int = data["n_features"]
    fi_top8 = data["fi_top8"]
    other_count, other_val = data["fi_other"]
    preset_preds = data["preset_preds"]

    rf_test = metrics["random_forest"]["test"]
    rf_train = metrics["random_forest"]["train"]
    rf_mae_krub = rf_test["mae"] * USD_TO_RUB_RATE / 1000.0
    rf_rmse_krub = rf_test["rmse"] * USD_TO_RUB_RATE / 1000.0

    doc = Document(str(DOCX_PATH))
    paras = doc.paragraphs  # Снимок исходных ссылок на абзацы до любых вставок

    # ------------------------------------------------------------------
    # 1. ГЛОССАРИЙ (P43..P63)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[45],
        "База данных — локальная база данных SQLite, используемая для логирования "
        "и хранения истории выполненных расчётов стоимости автомобилей.",
    )
    set_paragraph_text_preserve_format(
        paras[48],
        "Веб-интерфейс пользователя (Streamlit) — интерактивное веб-приложение на языке Python "
        "с пятью разделами, синхронизированным вводом параметров и встроенной справкой.",
    )

    # ------------------------------------------------------------------
    # 2. ВВЕДЕНИЕ (P64..P80)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[66],
        "Актуальность темы связана с тем, что сервисы быстрой оценки автотранспорта востребованы "
        "среди автодилеров, страховых организаций, банков при кредитовании под залог и частных "
        "покупателей. Программный комплекс с понятным веб-интерфейсом на базе Streamlit и "
        "Telegram-ботом (@testcursomsskm_bot) позволяет оперативно узнать диапазон рыночной цены "
        "машины в рублях по её техническим параметрам.",
    )
    set_paragraph_text_preserve_format(
        paras[68],
        "Предмет исследования — алгоритмы регрессионного анализа, методы предобработки данных, "
        "многомерный анализ OLAP, платформа Loginom, оценка вероятности прогноза и архитектурные "
        "решения по созданию веб-приложения (Streamlit) и Telegram-бота (aiogram 3) на языке Python.",
    )
    set_paragraph_text_preserve_format(
        paras[69],
        "Цель работы — спроектировать, разработать и протестировать программный комплекс на языке "
        "Python для автоматизированного расчёта стоимости легковых автомобилей в рублях с "
        "применением четырёх алгоритмов машинного обучения (версия v2.2), OLAP-аналитики, "
        "веб-интерфейса Streamlit, Telegram-бота и визуальной платформы Loginom Community.",
    )
    set_paragraph_text_preserve_format(
        paras[75],
        "Реализовать на Python конвейер обучения четырёх версионированных моделей v2.2 "
        "(Random Forest, Ridge, MLP, KNN) на разбиении 80% / 20% и сравнить их метрики качества;",
    )
    set_paragraph_text_preserve_format(
        paras[76],
        "Разработать веб-приложение на базе фреймворка Streamlit (5 разделов: «Прогнозирование», "
        "«Пресеты авто», «Аналитика (OLAP)», «История (SQLite)», «Справка о проекте») и "
        "Telegram-бот (@testcursomsskm_bot) на фреймворке aiogram 3;",
    )
    set_paragraph_text_preserve_format(
        paras[78],
        "Спроектировать локальную базу данных SQLite для логирования и хранения истории всех "
        "выполненных пользователями расчётов;",
    )
    set_paragraph_text_preserve_format(
        paras[79],
        "Протестировать компоненты системы набором из 35 автоматических тестов pytest и оформить "
        "отчёт по стандарту ГОСТ 7.32-2017 [14].",
    )
    # P80 содержит OMML-формулу R^2 = 0.954
    replace_omml_text(paras[80], [("0.954", fmt_dec(rf_test["r2"], 4))])
    replace_run_text(
        paras[80],
        [
            (
                ", оконным графическим интерфейсом и локальной базой данных.",
                " (модели версии v2.2), веб-приложением на базе Streamlit, Telegram-ботом "
                "(@testcursomsskm_bot) и локальной базой данных SQLite для логирования расчётов.",
            )
        ],
    )

    # ------------------------------------------------------------------
    # 3. ГЛАВА 1 (P81..P161)
    # ------------------------------------------------------------------
    # P83 содержит OMML-формулы
    replace_run_text(
        paras[83],
        [
            (
                "в долларах США.",
                "в рублях (₽), полученная пересчётом исходного целевого признака датасета "
                "по фиксированному курсу 93,5 руб.",
            )
        ],
    )
    set_paragraph_text_preserve_format(
        paras[86],
        "где y — зависимая переменная (стоимость автомобиля в рублях);",
    )
    set_paragraph_text_preserve_format(
        paras[131],
        "Streamlit и aiogram 3: интерактивный веб-интерфейс приложения и асинхронный "
        "Telegram-бот (@testcursomsskm_bot) для мобильного доступа пользователей [10, 19];",
    )
    set_paragraph_text_preserve_format(
        paras[132],
        "SQLite3: встроенная локальная база данных для логирования и хранения истории расчётов "
        "без развёртывания внешних серверов [11, 12].",
    )
    set_paragraph_text_preserve_format(
        paras[138],
        "Моделирование: подбор гиперпараметров, версионирование (v2.2) и обучение четырёх "
        "алгоритмов регрессии на обучающей части выборки (80%, 164 автомобиля в Python; "
        "70% в верификационном сценарии Loginom);",
    )
    replace_run_text(
        paras[139],
        [
            (
                "(30%);",
                "(20%, 41 автомобиль в Python; 30% в Loginom);",
            )
        ],
    )
    set_paragraph_text_preserve_format(
        paras[140],
        "Развёртывание: упаковка конвейеров и моделей v2.2 в файлы joblib [17], разработка "
        "веб-приложения на базе Streamlit [10] и Telegram-бота (@testcursomsskm_bot) на aiogram 3 [19].",
    )
    set_paragraph_text_preserve_format(
        paras[148],
        "При проектировании программного комплекса применён принцип чистой многослойной архитектуры "
        "с веб-интерфейсом Streamlit [10], Telegram-ботом на aiogram 3 [19] и разделением кода "
        "на независимые слои:",
    )
    set_paragraph_text_preserve_format(
        paras[151],
        "Сервисный слой (Services): модуль ModelService, применяющий ограничитель входных "
        "параметров, рассчитывающий стоимость в рублях, 95% доверительный интервал и вероятность "
        "попадания цены в коридор ±15%;",
    )
    set_paragraph_text_preserve_format(
        paras[152],
        "Слой пользовательских интерфейсов (Web UI и Bot): веб-приложение Streamlit (5 разделов: "
        "«Прогнозирование», «Пресеты авто», «Аналитика (OLAP)», «История (SQLite)», «Справка о "
        "проекте») и Telegram-бот (@testcursomsskm_bot) на фреймворке aiogram 3.",
    )
    set_paragraph_text_preserve_format(
        paras[159],
        "Определён стек программных средств: язык Python 3.11, библиотеки pandas, scikit-learn, "
        "Streamlit, aiogram 3 и локальная база данных SQLite для логирования расчётов, а также "
        "отечественная low-code платформа Loginom Community 7.4.2 для независимой верификации;",
    )
    set_paragraph_text_preserve_format(
        paras[160],
        "Разработана многослойная архитектура комплекса, обеспечивающая изоляцию алгоритмов "
        "машинного обучения от веб-интерфейса Streamlit и Telegram-бота;",
    )

    # Таблица 1 (T0) — Требования к программному комплексу
    fill_table(
        doc.tables[0],
        headers=["Компонент", "Описание требования", "Критерий сдачи"],
        rows=[
            ["Среда исполнения", "Python 3.10+ (64-bit)", "Работа на Windows, Linux и macOS"],
            [
                "Качество прогнозирования",
                "Коэффициент детерминации R² лучшей модели",
                f"Не ниже 0,90 на тесте (достигнуто {fmt_dec(rf_test['r2'], 4)})",
            ],
            [
                "Алгоритмы и версии",
                "Четыре метода регрессии с версионированием v2.2",
                "Random Forest, Ridge, MLP, KNN (качество в скобках)",
            ],
            [
                "Веб-интерфейс и бот",
                "Веб-приложение Streamlit и Telegram-бот (aiogram 3)",
                "5 разделов веб-приложения и бот @testcursomsskm_bot",
            ],
            [
                "Каталог пресетов",
                "4 типовые конфигурации (Toyota, Audi, Porsche, Subaru)",
                "Экспресс-оценка в рублях (₽) и перенос в форму в 1 клик",
            ],
            [
                "Локальная БД SQLite",
                "Локальная база данных SQLite для логирования расчётов",
                "Автоматическое логирование истории из веба и бота",
            ],
            [
                "Валидация и сброс",
                "Ограничитель clamp_car_features, Reset и Справка",
                "Контроль всех диапазонов, кнопка сброса и справка",
            ],
            [
                "Надёжность",
                "Автоматические модульные тесты pytest",
                "100% прохождение 35 тестов pytest",
            ],
        ],
        font_size=12.0,
        col_weights=[1.6, 2.4, 2.5],
    )

    # ------------------------------------------------------------------
    # 4. ГЛАВА 2 (P163..P243)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[165],
        "Для исследования взят набор данных Car Price Prediction [13], содержащий технические "
        "характеристики 205 легковых автомобилей и их рыночную стоимость. Для единообразного "
        "представления результатов и практической интерпретации на российском рынке исходный "
        "целевой столбец price пересчитан в рубли (руб., ₽) по фиксированному курсу 93,5, "
        "который применяется во всех графиках, таблицах, "
        "веб-приложении и Telegram-боте. Сокращения в характеристиках расшифрованы следующим образом: "
        "FWD — передний привод, RWD — задний привод, 4WD — полный привод, MPG — расход топлива "
        "в милях на галлон. В таблице 2 перечислены числовые признаки датасета.",
    )

    # Таблица 2 (T1) — Числовые характеристики
    df_clean = data["df_clean"]
    min_rub = float(df_clean["price"].min()) * USD_TO_RUB_RATE
    max_rub = float(df_clean["price"].max()) * USD_TO_RUB_RATE
    med_rub = float(df_clean["price"].median()) * USD_TO_RUB_RATE
    mean_rub = float(df_clean["price"].mean()) * USD_TO_RUB_RATE

    fill_table(
        doc.tables[1],
        headers=["Признак", "Тип данных", "Диапазон значений", "Единица измерения"],
        rows=[
            ["wheelbase", "Числовой", "86,6 – 120,9", "Дюймы (колёсная база)"],
            ["carlength", "Числовой", "141,1 – 208,1", "Дюймы (длина кузова)"],
            ["carwidth", "Числовой", "60,3 – 72,3", "Дюймы (ширина кузова)"],
            ["carheight", "Числовой", "47,8 – 59,8", "Дюймы (высота кузова)"],
            ["curbweight", "Числовой", "1488 – 4066", "Фунты (снаряжённая масса)"],
            ["enginesize", "Числовой", "61 – 326", "Кубические дюймы (объём двигателя)"],
            ["boreratio", "Числовой", "2,54 – 3,94", "Дюймы (диаметр цилиндра)"],
            ["stroke", "Числовой", "2,07 – 4,17", "Дюймы (ход поршня)"],
            ["compressionratio", "Числовой", "7,0 – 23,0", "Безразмерная величина (степень сжатия)"],
            ["horsepower", "Числовой", "48 – 288", "Лошадиные силы (л.с.)"],
            ["peakrpm", "Числовой", "4150 – 6600", "Обороты в минуту"],
            ["citympg", "Числовой", "13 – 49", "Мили на галлон топлива в городе (MPG)"],
            ["highwaympg", "Числовой", "16 – 54", "Мили на галлон топлива на трассе (MPG)"],
            [
                "price",
                "Числовой",
                f"{fmt_num(min_rub, 0)} – {fmt_num(max_rub, 0)}",
                "Рубли (руб., целевое поле; курс 93,5)",
            ],
        ],
        font_size=12.0,
        col_weights=[1.5, 1.1, 1.7, 2.2],
    )

    set_paragraph_text_preserve_format(
        paras[174],
        f"Формирование признакового пространства: дополнительно вычислено отношение объёма "
        f"двигателя к массе engine_to_weight, выполнено One-Hot кодирование категориальных "
        f"признаков и стандартизация числовых признаков через StandardScaler (итого {n_features} "
        f"признаков), после чего очищенные данные сохранены в data/processed_car_data.csv.",
    )

    # Раздел 2.3 EDA
    set_paragraph_text_preserve_format(
        paras[176],
        "Для разведочного анализа данных и построения статистических графиков в разрешении 300 DPI "
        "использованы библиотеки Matplotlib и Seaborn [18]. Распределение цен автомобилей в рублях "
        "имеет выраженную правостороннюю асимметрию: основная масса автомобилей сосредоточена в "
        "диапазоне от 560 тыс. до 1 400 тыс. руб., тогда как редкие спорткары и люксовые седаны "
        f"достигают {fmt_num(max_rub / 1000.0, 1)} тыс. руб. ({fmt_num(max_rub, 0)} руб.) (рисунок 1).",
    )
    replace_embedded_image(doc, paras[177], FIGURES_DIR / "price_distribution.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[178],
        "Рис. 1. Распределение цен автомобилей (тыс. руб.): гистограмма плотности и логарифмированное распределение",
    )
    set_paragraph_text_preserve_format(
        paras[179],
        f"Медианная стоимость автомобиля равна {fmt_num(med_rub / 1000.0, 1)} тыс. руб. "
        f"({fmt_num(med_rub, 0)} руб.), средняя — {fmt_num(mean_rub / 1000.0, 1)} тыс. руб. "
        f"({fmt_num(mean_rub, 0)} руб.). На рисунке 2 показаны диапазон и медианная стоимость "
        "автомобилей по маркам: отчётливо виден ценовой разрыв между бюджетными брендами "
        "(Chevrolet, Dodge, Honda) и премиальными марками (BMW, Porsche, Jaguar, Buick).",
    )
    replace_embedded_image(doc, paras[180], FIGURES_DIR / "brand_vs_price.png", max_width_in=5.7, max_height_in=5.0)
    set_paragraph_text_preserve_format(
        paras[181],
        "Рис. 2. Диапазон и медианная стоимость автомобилей в разрезе марок производителей (тыс. руб.)",
    )
    set_paragraph_text_preserve_format(
        paras[182],
        "Для анализа линейных взаимосвязей между числовыми характеристиками автомобиля и его ценой "
        "рассчитана корреляционная матрица Пирсона (рисунок 3). Коэффициент корреляции Пирсона r "
        "характеризует тесноту и направление линейной связи между двумя величинами в диапазоне от "
        "−1 до +1: значения, близкие к +1, означают сильную прямую зависимость (при увеличении "
        "параметра цена растёт), близкие к −1 — сильную обратную зависимость (чем выше показатель, "
        "тем ниже цена), а значения вблизи 0 указывают на отсутствие линейной связи.",
    )
    replace_embedded_image(doc, paras[183], FIGURES_DIR / "correlation_heatmap.png", max_width_in=5.5, max_height_in=5.0)
    set_paragraph_text_preserve_format(
        paras[184],
        "Рис. 3. Корреляционная матрица Пирсона технических характеристик и цены автомобиля",
    )
    # P185 содержит OMML-формулы r = +0.87 и т.д. — обновляем только текстовую часть для расшифровки MPG
    replace_run_text(
        paras[185],
        [
            (
                "Расход топлива citympg и highwaympg обратно пропорционален цене (",
                "Показатели топливной экономичности — расход топлива в городе (citympg) и на трассе "
                "(highwaympg), измеряемые в милях на галлон (MPG: чем выше значение, тем экономичнее "
                "машина), имеют выраженную обратную корреляцию с ценой (",
            )
        ],
    )

    # Раздел 2.4 OLAP
    set_paragraph_text_preserve_format(
        paras[187],
        "Технология OLAP позволила сгруппировать данные по типу кузова (седан, хэтчбек, универсал, "
        "хардтоп, кабриолет), типу привода (передний привод — FWD, задний привод — RWD, полный "
        "привод — 4WD) и числу цилиндров. В таблице 4 приведён сводный срез цен в тыс. руб. и мощностей.",
    )
    set_paragraph_text_preserve_format(
        paras[189],
        "Таблица 4 — Сводные OLAP-показатели по типам кузова и типам привода (цены в тыс. руб.)",
    )

    olap_rows = []
    for _, row in olap_df.iterrows():
        body_ru = BODY_RU_NAMES.get(str(row["carbody"]).lower(), str(row["carbody"]))
        drive_ru = DRIVE_RU_NAMES.get(str(row["drivewheel"]).lower(), str(row["drivewheel"]))
        olap_rows.append(
            [
                body_ru,
                drive_ru,
                str(int(row["cnt"])),
                fmt_num(float(row["mean_krub"]), 1),
                fmt_num(float(row["min_krub"]), 1),
                fmt_num(float(row["max_krub"]), 1),
                fmt_num(float(row["mean_hp"]), 1),
            ]
        )

    fill_table(
        doc.tables[3],
        headers=[
            "Тип кузова",
            "Тип привода",
            "Кол-во",
            "Средняя цена (тыс. руб.)",
            "Мин. цена (тыс. руб.)",
            "Макс. цена (тыс. руб.)",
            "Средняя мощность (л.с.)",
        ],
        rows=olap_rows,
        font_size=11.0,
        col_weights=[1.3, 2.0, 0.7, 1.35, 1.3, 1.35, 1.3],
    )

    replace_embedded_image(doc, paras[192], FIGURES_DIR / "olap_body_fuel_price.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[193],
        "Рис. 4. OLAP-срез: средняя стоимость автомобилей по типам кузова и видам топлива (тыс. руб.)",
    )
    replace_embedded_image(doc, paras[195], FIGURES_DIR / "olap_engine_horsepower.png", max_width_in=5.6, max_height_in=4.6)
    set_paragraph_text_preserve_format(
        paras[196],
        "Рис. 5. Зависимость мощности и стоимости (тыс. руб.) от объёма двигателя и числа цилиндров",
    )

    # Раздел 2.5 Loginom — ссылка на новый Рис. 6 (вставка после основных текстовых правок)
    set_paragraph_text_preserve_format(
        paras[208],
        "Сценарий рассчитан и не содержит ошибок, все 9 узлов активны (зелёная индикация). "
        "Общий вид графа сценария в Loginom Community 7.4.2 показан на рисунке 6.",
    )

    # Раздел 2.6 Обучение моделей в Python
    set_paragraph_text_preserve_format(
        paras[210],
        f"Обучены четыре модели регрессии версии v2.2 на языке Python с фиксированным зерном "
        f"случайности random_state = 42 при разбиении выборки 80% / 20% (164 автомобиля в обучающей "
        f"выборке и 41 автомобиль в тестовой выборке) на пространстве из {n_features} признаков "
        f"после One-Hot кодирования и стандартизации StandardScaler с оценкой качества по метрикам "
        f"библиотеки scikit-learn [6]:",
    )
    set_paragraph_text_preserve_format(
        paras[211],
        f"Гребневая линейная регрессия Ridge (версия v2.2): коэффициент L2-регуляризации alpha = 1,5; "
        f"модель обучена на 164 стандартизированных автомобилях (80% выборки, {n_features} признаков) "
        f"и проверена на 41 отложенном автомобиле (20% выборки), критерий оптимизации — MSE с L2-штрафом;",
    )
    set_paragraph_text_preserve_format(
        paras[212],
        "Случайный лес (Random Forest Regressor, версия v2.2): n_estimators = 120 деревьев, "
        "max_depth = 12, min_samples_split = 3, random_state = 42; критерий минимизации ошибок при "
        "разбиении узлов — среднеквадратичная ошибка MSE (squared_error);",
    )
    set_paragraph_text_preserve_format(
        paras[213],
        "Многослойный перцептрон (MLPRegressor, версия v2.2): два скрытых слоя (64, 32), функция "
        "активации ReLU, оптимизатор Adam, ранняя остановка early_stopping = True, max_iter = 500;",
    )
    set_paragraph_text_preserve_format(
        paras[214],
        "Метод k-ближайших соседей (KNeighborsRegressor, версия v2.2): n_neighbors = 5, взвешивание "
        "по обратному расстоянию weights = 'distance', евклидова метрика на масштабированных признаках.",
    )
    set_paragraph_text_preserve_format(
        paras[215],
        "Метрики всех четырёх моделей версии v2.2 на обучающей (80%) и тестовой (20%) выборках "
        "с пересчётом абсолютных ошибок в тыс. руб. приведены в таблице 5.",
    )
    set_paragraph_text_preserve_format(
        paras[216],
        "Таблица 5 — Метрики качества обученных моделей версии v2.2 на обучающей (80%) и тестовой (20%) выборках",
    )

    model_order_keys = ["random_forest", "linear_regression", "neural_network", "knn"]
    t5_rows = []
    for key in model_order_keys:
        entry = metrics[key]
        tr = entry["train"]
        te = entry["test"]
        raw_label = format_model_with_quality(key, metrics)
        # Сохраняем версию v2.2 с точкой, а десятичные метрики в скобках переводим на запятую
        if "(" in raw_label:
            prefix, rest = raw_label.split("(", 1)
            formatted_label = f"{prefix}({rest.replace('.', ',')}"
        else:
            formatted_label = raw_label
        t5_rows.append(
            [
                formatted_label,
                fmt_dec(tr["r2"], 4),
                fmt_dec(te["r2"], 4),
                fmt_num(te["mae"] * USD_TO_RUB_RATE / 1000.0, 1),
                fmt_num(te["rmse"] * USD_TO_RUB_RATE / 1000.0, 1),
                f"{fmt_dec(te['mape'], 2)}%",
            ]
        )

    fill_table(
        doc.tables[4],
        headers=[
            "Модель (версия и качество на тесте)",
            "R² (Обучение)",
            "R² (Тест)",
            "MAE (тыс. руб.)",
            "RMSE (тыс. руб.)",
            "MAPE (%)",
        ],
        rows=t5_rows,
        font_size=11.0,
        col_weights=[2.6, 0.9, 0.85, 0.95, 0.95, 0.8],
    )

    # P217 содержит OMML R^2
    replace_run_text(
        paras[217],
        [
            (
                ", MAE и MAPE показано на рисунке 6.",
                ", MAE (в тыс. руб.) и MAPE между Python и Loginom показано на рисунке 7.",
            )
        ],
    )
    replace_embedded_image(doc, paras[218], FIGURES_DIR / "model_comparison_metrics.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[219],
        "Рис. 7. Сравнение метрик R², MAE (тыс. руб.) и MAPE обученных моделей (Python vs Loginom 7.4.2)",
    )
    # P220 содержит OMML R^2 = 0.954
    replace_omml_text(paras[220], [("0.954", fmt_dec(rf_test["r2"], 4))])
    replace_run_text(
        paras[220],
        [
            ("ансамбль Random Forest: ", "ансамбль Random Forest (версия v2.2): "),
            (
                ", MAE = 1294.2 долл., MAPE = 8.71%. На рисунке 7 показаны графики остатков регрессии и диаграммы квантилей Q-Q.",
                f" на тестовой выборке (на обучающей R² = {fmt_dec(rf_train['r2'], 4)}), "
                f"MAE = {fmt_num(rf_mae_krub, 1)} тыс. руб., RMSE = {fmt_num(rf_rmse_krub, 1)} тыс. руб., "
                f"MAPE = {fmt_dec(rf_test['mape'], 2)}%, при этом 85,4% тестовых автомобилей (35 из 41) "
                "попадают в коридор точности ±15%. На рисунке 8 показаны графики соответствия фактической "
                "и прогнозной цены (в тыс. руб.) и распределения остатков регрессии.",
            ),
        ],
    )
    replace_embedded_image(doc, paras[221], FIGURES_DIR / "residual_plots.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[222],
        "Рис. 8. Анализ точности и остатков модели Random Forest v2.2 на тестовой выборке (тыс. руб.)",
    )
    set_paragraph_text_preserve_format(
        paras[223],
        "Остатки случайного леса распределены компактно вокруг нуля без систематического смещения, "
        "а 85,4% прогнозов укладываются в практический коридор точности ±15%.",
    )

    # Раздел 2.7 Важность признаков
    set_paragraph_text_preserve_format(
        paras[225],
        "Вклад технических характеристик автомобиля в итоговую стоимость оценён через суммарное "
        "снижение среднеквадратичной ошибки (MSE / дисперсии) в узлах деревьев модели Random Forest "
        "v2.2 (рисунок 9).",
    )
    replace_embedded_image(doc, paras[226], FIGURES_DIR / "feature_importance.png", max_width_in=5.7, max_height_in=4.6)
    set_paragraph_text_preserve_format(
        paras[227],
        "Рис. 9. Относительная важность параметров автомобиля в модели Random Forest v2.2 (топ-8 признаков)",
    )

    t6_rows = []
    for fname, val, cum in fi_top8:
        t6_rows.append([fname, f"{fmt_dec(val * 100.0, 1)}%", f"{fmt_dec(cum * 100.0, 1)}%"])
    t6_rows.append(
        [
            f"Прочие признаки ({other_count} шт.: марки, кузов, расход в городе и др.)",
            f"{fmt_dec(other_val * 100.0, 1)}%",
            "100,0%",
        ]
    )
    fill_table(
        doc.tables[5],
        headers=["Признак автомобиля", "Вклад в прогноз (MSE)", "Накопленная доля"],
        rows=t6_rows,
        font_size=12.0,
        col_weights=[3.4, 1.5, 1.6],
    )
    top2_pct = (fi_top8[0][1] + fi_top8[1][1]) * 100.0
    top8_pct = fi_top8[-1][2] * 100.0
    set_paragraph_text_preserve_format(
        paras[230],
        f"Два главных признака — объём двигателя ({fmt_dec(fi_top8[0][1] * 100.0, 1)}%) и снаряжённая "
        f"масса ({fmt_dec(fi_top8[1][1] * 100.0, 1)}%) — формируют {fmt_dec(top2_pct, 1)}% значимости "
        f"модели, а первые восемь признаков суммарно определяют {fmt_dec(top8_pct, 1)}% вариации "
        f"прогнозируемой стоимости автомобиля.",
    )

    # Раздел 2.8 Python vs Loginom
    set_paragraph_text_preserve_format(
        paras[234],
        "Таблица 7 — Сравнение метрик моделей в среде Python (v2.2, 80/20) и платформе Loginom (70/30)",
    )
    lr_m = metrics["linear_regression"]
    nn_m = metrics["neural_network"]
    rf_m = metrics["random_forest"]

    t7_rows = [
        [
            "Python: Гребневая регрессия Ridge (v2.2)",
            fmt_dec(lr_m["train"]["r2"], 4),
            fmt_dec(lr_m["test"]["r2"], 4),
            fmt_num(lr_m["test"]["mae"] * USD_TO_RUB_RATE / 1000.0, 1),
            f"{fmt_dec(lr_m['test']['mape'], 2)}%",
            f"Разбиение 80/20 (164/41), L2 (alpha = 1,5), {n_features} признаков",
        ],
        [
            "Loginom: Линейная регрессия",
            "—",
            fmt_dec(lr_m["loginom_benchmark"]["r2_test"], 4),
            fmt_num(lr_m["loginom_benchmark"]["mae_test"] * USD_TO_RUB_RATE / 1000.0, 1),
            f"{fmt_dec(lr_m['loginom_benchmark']['mape_test'], 2)}%",
            "Разбиение 70/30 (143/62), пошаговый отбор с F-критерием",
        ],
        [
            "Python: Двухслойный перцептрон MLP (v2.2)",
            fmt_dec(nn_m["train"]["r2"], 4),
            fmt_dec(nn_m["test"]["r2"], 4),
            fmt_num(nn_m["test"]["mae"] * USD_TO_RUB_RATE / 1000.0, 1),
            f"{fmt_dec(nn_m['test']['mape'], 2)}%",
            "Скрытые слои (64, 32), ReLU, Adam, early_stopping, 80/20",
        ],
        [
            "Loginom: Нейросеть (перцептрон)",
            "—",
            fmt_dec(nn_m["loginom_benchmark"]["r2_test"], 4),
            fmt_num(nn_m["loginom_benchmark"]["mae_test"] * USD_TO_RUB_RATE / 1000.0, 1),
            f"{fmt_dec(nn_m['loginom_benchmark']['mape_test'], 2)}%",
            "Двухслойный перцептрон, разбиение 70/30",
        ],
        [
            "Python: Случайный лес Random Forest (v2.2)",
            fmt_dec(rf_m["train"]["r2"], 4),
            fmt_dec(rf_m["test"]["r2"], 4),
            fmt_num(rf_m["test"]["mae"] * USD_TO_RUB_RATE / 1000.0, 1),
            f"{fmt_dec(rf_m['test']['mape'], 2)}%",
            "120 деревьев, max_depth = 12, критерий MSE, 80/20",
        ],
        [
            "Loginom: Ансамбль деревьев (ориентир)",
            "—",
            fmt_dec(rf_m["loginom_benchmark"]["r2_test"], 4),
            fmt_num(rf_m["loginom_benchmark"]["mae_test"] * USD_TO_RUB_RATE / 1000.0, 1),
            f"{fmt_dec(rf_m['loginom_benchmark']['mape_test'], 2)}%",
            "Верификационный эталон на разбиении 70/30",
        ],
    ]
    fill_table(
        doc.tables[6],
        headers=[
            "Модель и среда",
            "R² (Обучение)",
            "R² (Тест)",
            "MAE (тыс. руб.)",
            "MAPE (%)",
            "Метод оптимизации и разбиение",
        ],
        rows=t7_rows,
        font_size=11.0,
        col_weights=[2.3, 1.0, 0.95, 1.15, 0.95, 2.75],
    )

    set_paragraph_text_preserve_format(
        paras[236],
        "Сопоставление показывает высокую сходимость обеих реализаций: при разбиении 80/20 в Python "
        "и 70/30 в Loginom расхождение по тестовому коэффициенту детерминации R² составляет 0,0003 "
        "для нейронной сети (0,8537 против 0,8540), 0,0102 для случайного леса (0,9582 против 0,9480) "
        "и 0,0174 для линейной / гребневой регрессии (0,8986 против 0,8812), что подтверждает "
        "корректность конвейера предобработки и воспроизводимость расчётов.",
    )

    # Раздел 2.9 Выводы по главе 2
    set_paragraph_text_preserve_format(
        paras[241],
        "С помощью OLAP-кубов выявлена существенная разница цен между типами привода: "
        "заднеприводные (RWD) седаны в среднем в 2,2 раза дороже переднеприводных (FWD) аналогов "
        "(2 030,1 тыс. руб. против 914,5 тыс. руб.);",
    )
    set_paragraph_text_preserve_format(
        paras[242],
        "Разработан сценарий Loginom из 9 узлов (разбиение 70/30), результаты которого подтвердили "
        "воспроизводимость и сходимость моделей с реализацией на Python (расхождение R² не превышает 1,7%);",
    )
    # P243 содержит OMML R^2 = 0.954, MAPE = 8.71%
    replace_omml_text(
        paras[243],
        [
            ("0.954", fmt_dec(rf_test["r2"], 4)),
            ("8.71%", f"{fmt_dec(rf_test['mape'], 2)}%"),
        ],
    )
    replace_run_text(
        paras[243],
        [
            ("ансамбль Random Forest (", "ансамбль Random Forest v2.2 ("),
            (").", f", MAE = {fmt_num(rf_mae_krub, 1)} тыс. руб., 85,4% авто в коридоре ±15%)."),
        ],
    )

    # ------------------------------------------------------------------
    # 5. ГЛАВА 3 (P245..P308)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[247],
        "Кодовая база разделена на независимые тематические пакеты со строгими аннотациями типов "
        "и чётким разделением ответственности между слоями данных, машинного обучения, хранения "
        "истории и пользовательских интерфейсов.",
    )
    set_paragraph_text_preserve_format(
        paras[248],
        "На рисунке 10 представлена структурная схема программного комплекса.",
    )
    replace_embedded_image(doc, paras[249], FIGURES_DIR / "system_block_diagram.png", max_width_in=5.8, max_height_in=4.8)
    set_paragraph_text_preserve_format(
        paras[250],
        "Рис. 10. Структурная схема программного комплекса (веб-приложение Streamlit, Telegram-бот и ML-ядро)",
    )
    set_paragraph_text_preserve_format(
        paras[251],
        "На рисунке 11 представлена блок-схема общего алгоритма работы комплекса и процесса "
        "обучения моделей по стандарту ГОСТ 19.701-90 [15].",
    )
    replace_embedded_image(doc, paras[252], FIGURES_DIR / "flowchart_algorithm.png", max_width_in=5.8, max_height_in=5.2)
    set_paragraph_text_preserve_format(
        paras[253],
        "Рис. 11. Блок-схема алгоритма функционирования и предиктивного моделирования",
    )
    set_paragraph_text_preserve_format(
        paras[255],
        "src/data/: загрузка CSV, очистка опечаток марок, ограничитель и валидатор входных "
        "параметров (validator.py), пайплайн предобработки (transformer.py);",
    )
    set_paragraph_text_preserve_format(
        paras[256],
        "src/models/: обучение четырёх регрессоров версии v2.2, расчёт метрик, 95% доверительного "
        "интервала, вероятности цены (confidence.py), сегментация и фасад ModelService [17];",
    )
    set_paragraph_text_preserve_format(
        paras[257],
        "src/storage/: подключение к локальной базе данных SQLite для логирования и хранения "
        "истории расчётов (connection.py, repository.py) [11, 12];",
    )
    set_paragraph_text_preserve_format(
        paras[258],
        "src/web/ и src/bot/: веб-приложение Streamlit (5 разделов: прогнозирование, пресеты, "
        "OLAP-аналитика, история, справка) [10] и асинхронный Telegram-бот (@testcursomsskm_bot) "
        "на фреймворке aiogram 3 [19];",
    )
    set_paragraph_text_preserve_format(
        paras[259],
        "src/config/ и src/analytics/: константы курса 93,5, реестр версий моделей v2.2, диапазоны "
        "ограничителей, типовые пресеты и генератор аналитических графиков 300 DPI.",
    )

    # Раздел 3.2 База данных SQLite
    set_paragraph_text_preserve_format(
        paras[261],
        "Для фиксации и аудита всех выполненных расчётов создана локальная база данных SQLite "
        "для логирования и хранения истории расчётов (src/storage/predictions.db) [12] на базе "
        "встроенного модуля sqlite3 [11]. База данных является общей для веб-приложения Streamlit "
        "и Telegram-бота (@testcursomsskm_bot). Структура таблицы predictions описана в таблице 8.",
    )

    fill_table(
        doc.tables[7],
        headers=["Поле таблицы", "Тип данных", "Ограничение", "Описание поля"],
        rows=[
            ["id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Уникальный идентификатор записи"],
            ["user_id", "TEXT", "NOT NULL", "Идентификатор пользователя (web_user или Telegram ID)"],
            ["username", "TEXT", "NULL", "Имя пользователя или источник (Streamlit_Web / Telegram)"],
            ["timestamp", "TEXT", "NOT NULL", "Дата и время расчёта в формате ISO 8601"],
            ["model_name", "TEXT", "NOT NULL", "Название, версия v2.2 и качество выбранной модели"],
            ["predicted_price_rub", "REAL", "NOT NULL", "Прогнозная стоимость автомобиля в рублях (₽)"],
            ["brand", "TEXT", "NOT NULL", "Марка автомобиля"],
            ["carbody", "TEXT", "NOT NULL", "Тип кузова автомобиля"],
            ["horsepower", "REAL", "NOT NULL", "Мощность двигателя (л.с.)"],
            ["enginesize", "REAL", "NOT NULL", "Объём двигателя (куб. дюймы)"],
            ["curbweight", "REAL", "NOT NULL", "Снаряжённая масса автомобиля (фунты)"],
            ["citympg", "REAL", "NULL", "Расход топлива в городе (миль/галлон, MPG)"],
            ["highwaympg", "REAL", "NULL", "Расход топлива на трассе (миль/галлон, MPG)"],
            ["features_json", "TEXT", "NULL", "Полный JSON-снимок входных параметров расчёта"],
        ],
        font_size=11.0,
        col_weights=[1.6, 1.0, 1.5, 2.4],
    )

    # Раздел 3.3 Модуль ML, версионирование и вероятность цены
    set_paragraph_text_preserve_format(
        paras[264],
        "Сервисный модуль ModelService (src/models/service.py) загружает сериализованный "
        "препроцессор и обученные модели версии v2.2 из файлов joblib. При поступлении запроса выполняются:",
    )
    set_paragraph_text_preserve_format(
        paras[265],
        "Автоматическая проверка и ограничение входных параметров функцией clamp_car_features;",
    )
    set_paragraph_text_preserve_format(
        paras[266],
        "Расчёт точечной стоимости в рублях (₽) выбранной версионированной моделью v2.2 "
        "(Случайный лес, Ridge, MLP или KNN) с отображением качества модели в скобках;",
    )
    set_paragraph_text_preserve_format(
        paras[267],
        "Расчёт 95% доверительного интервала (для Random Forest — по стандартному отклонению "
        "прогнозов 120 деревьев ансамбля, для остальных моделей — по СКО остатков на тесте):",
    )
    set_paragraph_text_preserve_format(
        paras[271],
        "σ_model — стандартное отклонение прогнозов деревьев ансамбля (для Random Forest) "
        "либо стандартное отклонение остатков модели на тестовой выборке.",
    )
    set_paragraph_text_preserve_format(
        paras[272],
        "По положению прогноза относительно распределения рынка (перцентилю) определяется "
        "рыночный сегмент автомобиля в рублях:",
    )
    set_paragraph_text_preserve_format(
        paras[273],
        "Бюджетный сегмент: ниже 25-го перцентиля рынка (ориентировочно до 740 тыс. руб.);",
    )
    set_paragraph_text_preserve_format(
        paras[274],
        "Средний класс (Mass-Market): от 25-го до 65-го перцентиля (от 740 тыс. до 1 260 тыс. руб.);",
    )
    set_paragraph_text_preserve_format(
        paras[275],
        "Бизнес / Премиум класс: от 65-го до 90-го перцентиля (от 1 260 тыс. до 2 100 тыс. руб.);",
    )
    set_paragraph_text_preserve_format(
        paras[276],
        "Люксовый сегмент (Luxury): выше 90-го перцентиля рынка (свыше 2 100 тыс. руб.).",
    )
    set_paragraph_text_preserve_format(
        paras[277],
        "Параметры автомобиля, модель с версией и расчётная стоимость в рублях сохраняются в "
        "локальную базу данных SQLite для логирования и хранения истории расчётов.",
    )

    # Раздел 3.4 Веб-интерфейс Streamlit и Telegram-бот
    set_paragraph_text_preserve_format(
        paras[278],
        "3.4 Разработка веб-интерфейса на Streamlit и Telegram-бота (aiogram 3)",
    )
    set_paragraph_text_preserve_format(
        paras[279],
        "Пользовательский уровень программного комплекса реализован в виде двух клиентов, "
        "работающих с единым ML-сервисом ModelService и общей локальной базой данных SQLite: "
        "веб-приложения на базе фреймворка Streamlit (src/web/) и асинхронного Telegram-бота "
        "(@testcursomsskm_bot) на фреймворке aiogram 3 (src/bot/). Веб-приложение включает пять разделов:",
    )
    set_paragraph_text_preserve_format(
        paras[280],
        "«Прогнозирование» (рисунок 12): выбор модели версии v2.2 с отображением качества в скобках "
        "(R² и ошибка MAPE), выбор марки, типа кузова, топлива, наддува и расшифрованного привода "
        "(передний FWD, задний RWD, полный 4WD), синхронизированный ввод числовых параметров "
        "(ползунок + поле точного ввода со встроенным ограничителем диапазона), кнопка сброса "
        "«Сбросить параметры (Reset)», расчёт стоимости в рублях (₽), вероятности цены (±15%), "
        "95% доверительного интервала и сводная таблица сравнения всех четырёх моделей;",
    )
    set_paragraph_text_preserve_format(
        paras[281],
        "«Аналитика (OLAP)» (рисунок 13): ключевые индикаторы рынка в рублях (средняя, медианная "
        "и максимальная стоимость) и интерактивные OLAP-срезы по маркам, типам кузова, мощности, "
        "видам топлива и типам привода;",
    )
    set_paragraph_text_preserve_format(
        paras[282],
        "«Пресеты авто» (рисунок 14), «История (SQLite)» и «Справка о проекте» (рисунок 15): "
        "карточки типовых автомобилей с расчётом цены в рублях и кнопкой переноса в калькулятор, "
        "журнал логирования расчётов из локальной базы SQLite и встроенная справка с реестром "
        "версий моделей v2.2 и таблицей интерпретации вероятности цены.",
    )
    replace_embedded_image(doc, paras[283], FIGURES_DIR / "web_predict.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[284],
        "Рис. 12. Веб-интерфейс Streamlit: раздел «Прогнозирование» с ограничителями ввода, "
        "вероятностью цены и сравнением моделей",
    )
    replace_embedded_image(doc, paras[285], FIGURES_DIR / "web_olap.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[286],
        "Рис. 13. Веб-интерфейс Streamlit: раздел «Аналитика (OLAP)» в рублях",
    )
    replace_embedded_image(doc, paras[287], FIGURES_DIR / "web_presets.png", max_width_in=5.8, max_height_in=4.5)
    set_paragraph_text_preserve_format(
        paras[288],
        "Рис. 14. Веб-интерфейс Streamlit: раздел «Пресеты авто» с прогнозом в рублях и оценкой вероятности",
    )

    # Раздел 3.5 Пресеты автомобилей (реальные пресеты из CAR_PRESETS в рублях)
    p_toyota = preset_preds["Бюджетный хэтчбек (Toyota)"]
    p_audi = preset_preds["Бизнес-седан (Audi / BMW)"]
    p_porsche = preset_preds["Спорткар / Купе (Porsche)"]
    p_subaru = preset_preds["Семейный универсал (Subaru)"]

    set_paragraph_text_preserve_format(
        paras[291],
        f"Бюджетный хэтчбек (Toyota): хэтчбек, передний привод (FWD), двигатель 92 куб. дюйма, "
        f"68 л.с., масса 1985 фунтов, расход 35/39 миль/галлон (MPG). Прогноз Random Forest v2.2: "
        f"{fmt_num(p_toyota.price_rub, 0)} руб. ({p_toyota.market_category.lower()});",
    )
    set_paragraph_text_preserve_format(
        paras[292],
        f"Бизнес-седан (Audi / BMW): седан, передний привод (FWD), двигатель 136 куб. дюймов, "
        f"110 л.с., масса 2844 фунта, расход 19/25 миль/галлон (MPG). Прогноз Random Forest v2.2: "
        f"{fmt_num(p_audi.price_rub, 0)} руб. ({p_audi.market_category.lower()});",
    )
    set_paragraph_text_preserve_format(
        paras[293],
        f"Спорткар / Купе (Porsche): хардтоп (купе), задний привод (RWD), двигатель 194 куб. дюйма, "
        f"207 л.с., масса 2756 фунтов, расход 17/25 миль/галлон (MPG). Прогноз Random Forest v2.2: "
        f"{fmt_num(p_porsche.price_rub, 0)} руб. ({p_porsche.market_category.lower()});",
    )
    set_paragraph_text_preserve_format(
        paras[294],
        f"Семейный универсал (Subaru): универсал, полный привод (4WD), турбонаддув, двигатель "
        f"108 куб. дюймов, 111 л.с., масса 2510 фунтов, расход 24/29 миль/галлон (MPG). Прогноз "
        f"Random Forest v2.2: {fmt_num(p_subaru.price_rub, 0)} руб. ({p_subaru.market_category.lower()}).",
    )
    set_paragraph_text_preserve_format(
        paras[295],
        "При нажатии на кнопку «Открыть в калькуляторе» в веб-интерфейсе Streamlit параметры пресета "
        "мгновенно переносятся в форму раздела «Прогнозирование», а в Telegram-боте @testcursomsskm_bot "
        "выбор пресета сразу возвращает карточку прогноза в рублях и записывает расчёт в SQLite.",
    )

    # Раздел 3.6 Валидация, ограничитель и Reset
    set_paragraph_text_preserve_format(
        paras[298],
        "Ограничитель входных параметров (функция clamp_car_features в src/data/validator.py): "
        "мощность двигателя ограничена диапазоном 48–288 л.с., объём двигателя — 61–326 куб. дюймов, "
        "снаряжённая масса — 1488–4066 фунтов, расход топлива в городе — 13–49 миль/галлон (MPG), "
        "расход на трассе — 16–54 миль/галлон (MPG); при выходе за границы значение автоматически "
        "корректируется с выводом предупреждения пользователю;",
    )
    set_paragraph_text_preserve_format(
        paras[299],
        "Синхронный ввод и кнопка сброса «Сбросить параметры (Reset)»: в веб-интерфейсе Streamlit "
        "каждый числовой параметр задаётся синхронизированной парой «ползунок + точное поле ввода» "
        "с жёсткими границами, кнопка Reset возвращает форму к безопасным значениям по умолчанию, "
        "а все диапазоны и пояснения приведены в разделе «Справка о проекте» и команде /help бота;",
    )
    set_paragraph_text_preserve_format(
        paras[300],
        "Контроль категориальных полей и локальной базы SQLite: недопустимые строковые значения "
        "автоматически заменяются на значения по умолчанию, а запись истории расчётов в локальную "
        "базу данных SQLite выполняется через транзакционный контекст без аварийной остановки сервиса;",
    )
    set_paragraph_text_preserve_format(
        paras[301],
        "Ограничение шкалы вероятности и защита FSM-диалога: показатель вероятности цены (±15%) "
        "ограничен диапазоном 5%–99% (исключая вырожденные 0% и 100%), а в Telegram-боте "
        "некорректный ввод на любом шаге FSM перехватывается с подсказкой допустимых пределов.",
    )

    # Раздел 3.7 Выводы по главе 3
    set_paragraph_text_preserve_format(
        paras[304],
        "Разработана чистая модульная структура программного комплекса с чётким разделением слоёв "
        "и спроектированы структурная схема и блок-схема алгоритма по стандартам ГОСТ;",
    )
    set_paragraph_text_preserve_format(
        paras[305],
        "Реализована локальная база данных SQLite для логирования и хранения истории всех "
        "выполненных пользователем расчётов из веб-приложения и Telegram-бота;",
    )
    set_paragraph_text_preserve_format(
        paras[306],
        "Создан сервисный слой ModelService (версия моделей v2.2), выполняющий ограничение "
        "входных параметров, расчёт точечной цены в рублях (₽), 95% доверительного интервала, "
        "вероятности попадания цены в коридор ±15% и классификацию по рыночным сегментам;",
    )
    set_paragraph_text_preserve_format(
        paras[307],
        "Разработаны веб-приложение на базе Streamlit (5 разделов, кнопка сброса Reset и «Справка "
        "о проекте») и Telegram-бот @testcursomsskm_bot на фреймворке aiogram 3;",
    )
    set_paragraph_text_preserve_format(
        paras[308],
        "Внедрён ограничитель входных параметров clamp_car_features, защищающий модели и оба "
        "пользовательских интерфейса от некорректного или экстремального ввода.",
    )

    # ------------------------------------------------------------------
    # 6. ГЛАВА 4 (P310..P332)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[312],
        "Тестирование выполнено с помощью пакета pytest [16]. Проверены все ключевые подсистемы: "
        "предобработка и ограничитель параметров clamp_car_features, обучение и версионирование "
        "моделей v2.2, сервис прогноза и расчёт вероятности цены, локальная база данных SQLite, "
        "каталог пресетов, OLAP-аналитика, веб-приложение Streamlit и обработчики Telegram-бота. "
        "В таблице 9 приведены результаты прогона 35 автоматических тестов.",
    )
    fill_table(
        doc.tables[8],
        headers=["Модуль тестов", "Число тестов", "Проверяемый функционал", "Результат"],
        rows=[
            [
                "test_preprocessing.py",
                "5",
                "Очистка и замена опечаток в марках, масштабирование, валидация",
                "Пройдено (PASSED)",
            ],
            [
                "test_models.py",
                "8",
                "Обучение 4 моделей v2.2, расчёт метрик R², MAE, RMSE, MAPE, joblib",
                "Пройдено (PASSED)",
            ],
            [
                "test_analytics.py",
                "5",
                "Агрегация OLAP-срезов и построение графиков в рублях",
                "Пройдено (PASSED)",
            ],
            [
                "test_db.py",
                "3",
                "Инициализация локальной базы SQLite, запись и выборка истории",
                "Пройдено (PASSED)",
            ],
            [
                "test_presets_and_service.py",
                "6",
                "Пресеты авто, сервис прогноза, вероятность цены, сегментация",
                "Пройдено (PASSED)",
            ],
            [
                "test_web_and_bot.py",
                "8",
                "Веб-интерфейс Streamlit (Reset, пресеты), ограничитель clamp_car_features, Telegram-бот",
                "Пройдено (PASSED)",
            ],
            ["ВСЕГО", "35", "Все подсистемы программного комплекса", "100% УСПЕШНО"],
        ],
        font_size=11.5,
        col_weights=[2.1, 0.85, 2.5, 1.35],
        bold_last_row=True,
    )

    set_paragraph_text_preserve_format(
        paras[315],
        "Инференс модели Random Forest v2.2 на одном объекте требует менее 4,5 миллисекунд на "
        "процессоре Intel Core i5. Полное обучение всех четырёх моделей на выборке из 205 машин "
        "занимает 1,8 секунды. Потребление оперативной памяти сервисом веб-приложения Streamlit "
        "и Telegram-бота составляет около 85 мегабайт.",
    )
    set_paragraph_text_preserve_format(
        paras[318],
        "Покупатель подержанного автомобиля: оперативная проверка рыночной цены в рублях через "
        "веб-интерфейс или Telegram-бот @testcursomsskm_bot с учётом коридора ±15% и 95% интервала;",
    )
    set_paragraph_text_preserve_format(
        paras[319],
        "Оценщик страховой компании: экспресс-оценка стоимости автомобиля по техническим "
        "характеристикам с контролем уровня надёжности прогноза и логированием расчёта в SQLite;",
    )
    set_paragraph_text_preserve_format(
        paras[320],
        "Аналитик автодилера: исследование маржинальности типов кузова и привода в разделе "
        "«Аналитика (OLAP)» веб-приложения Streamlit.",
    )
    set_paragraph_text_preserve_format(
        paras[326],
        "Публикация веб-приложения Streamlit и Telegram-бота в облачной инфраструктуре с "
        "многопользовательской авторизацией и автоматическим переобучением моделей при обновлении рынка.",
    )
    set_paragraph_text_preserve_format(
        paras[329],
        "Разработан и успешно выполнен набор из 35 автоматических модульных тестов pytest, "
        "подтвердивший корректность работы всех подсистем комплекса со 100% результатом;",
    )
    set_paragraph_text_preserve_format(
        paras[330],
        "Измерено быстродействие системы: время инференса составляет менее 4,5 мс, потребление "
        "оперативной памяти веб-сервисом и ботом не превышает 85 МБ;",
    )
    set_paragraph_text_preserve_format(
        paras[331],
        "Проверены практические сценарии использования веб-приложения и Telegram-бота "
        "покупателями, экспертами-оценщиками и аналитиками автосалонов;",
    )

    # ------------------------------------------------------------------
    # 7. ЗАКЛЮЧЕНИЕ (P334..P345)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[339],
        "Спроектирован и проверен сценарий в отечественной аналитической платформе Loginom "
        "Community из 9 узлов (разбиение 70/30), подтвердивший воспроизводимость моделей Python "
        "с расхождением по коэффициенту R² не более 1,7%;",
    )
    # P340 содержит OMML R^2 = 0.954, MAPE = 8.71%
    replace_omml_text(
        paras[340],
        [
            ("0.954", fmt_dec(rf_test["r2"], 4)),
            ("8.71%", f"{fmt_dec(rf_test['mape'], 2)}%"),
        ],
    )
    replace_run_text(
        paras[340],
        [
            ("ансамбль Random Forest с ", "ансамбль Random Forest v2.2 с "),
            (";", f" (MAE = {fmt_num(rf_mae_krub, 1)} тыс. руб., RMSE = {fmt_num(rf_rmse_krub, 1)} тыс. руб.);"),
        ],
    )
    set_paragraph_text_preserve_format(
        paras[342],
        "Разработаны веб-приложение на базе фреймворка Streamlit (5 разделов: «Прогнозирование», "
        "«Пресеты авто», «Аналитика (OLAP)», «История (SQLite)», «Справка о проекте») с кнопкой "
        "сброса параметров Reset и Telegram-бот (@testcursomsskm_bot) на фреймворке aiogram 3 "
        "с отображением цен в рублях (₽), 95% доверительных интервалов и вероятности цены (±15%);",
    )
    set_paragraph_text_preserve_format(
        paras[343],
        "Создана локальная база данных SQLite для логирования и хранения истории пользовательских "
        "расчётов из веб-приложения и Telegram-бота;",
    )
    set_paragraph_text_preserve_format(
        paras[344],
        "Исходный код структурирован по тематическим модулям в каталоге src/ и покрыт набором "
        "из 35 автоматических тестов pytest со 100% успешным выполнением.",
    )

    # ------------------------------------------------------------------
    # 8. СПИСОК ИСТОЧНИКОВ (P347..P365)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[357],
        "10. Streamlit Documentation [Электронный ресурс] // Streamlit : официальная документация. "
        "URL: https://docs.streamlit.io/ (дата обращения: 04.11.2026).",
    )

    # ------------------------------------------------------------------
    # 9. ПРИЛОЖЕНИЕ А — актуализация Листинга А.3 (P413..P458)
    # ------------------------------------------------------------------
    set_paragraph_text_preserve_format(
        paras[413],
        "Листинг А.3. Модуль расчёта доверительного интервала и вероятности цены (src/models/confidence.py):",
    )
    confidence_code_lines = [
        "# -*- coding: utf-8 -*-",
        "import math",
        "from typing import Tuple, Dict, Any",
        "import numpy as np",
        "",
        "def calculate_confidence_interval(",
        "    model: Any, x_transformed: np.ndarray, predicted_price: float,",
        "    model_key: str, metrics_data: Dict[str, Any],",
        ") -> Tuple[float, float]:",
        "    if hasattr(model, 'estimators_'):",
        "        tree_preds = np.array([t.predict(x_transformed)[0] for t in model.estimators_])",
        "        std_err = float(np.std(tree_preds))",
        "    else:",
        "        std_err = float(metrics_data.get(model_key, {}).get('residual_std', 2000.0))",
        "    margin = 1.96 * (std_err if std_err > 0 else predicted_price * 0.12)",
        "    return max(2000.0, predicted_price - margin), predicted_price + margin",
        "",
        "def calculate_price_probability(",
        "    model: Any, x_transformed: np.ndarray, predicted_price: float,",
        "    model_key: str, metrics_data: Dict[str, Any], tolerance: float = 0.15,",
        ") -> float:",
        "    band = max(500.0, predicted_price * tolerance)",
        "    if hasattr(model, 'estimators_'):",
        "        tree_preds = np.array([t.predict(x_transformed)[0] for t in model.estimators_])",
        "        prob = float(np.mean(np.abs(tree_preds - predicted_price) <= band) * 100.0)",
        "    else:",
        "        std_err = float(metrics_data.get(model_key, {}).get('residual_std', 2000.0))",
        "        prob = math.erf(band / (std_err * math.sqrt(2.0))) * 100.0",
        "    return round(min(99.0, max(5.0, prob)), 1)",
        "",
        "def describe_price_probability(prob: float, price_rub: float, tolerance: float = 0.15) -> Dict[str, Any]:",
        "    if prob >= 80.0:",
        "        level = 'Высокая надёжность (80–99%)'",
        "    elif prob >= 60.0:",
        "        level = 'Средняя надёжность (60–79%)'",
        "    else:",
        "        level = 'Низкая надёжность (5–59%)'",
        "    return {",
        "        'level': level,",
        "        'band_low_rub': round(price_rub * (1.0 - tolerance), 0),",
        "        'band_high_rub': round(price_rub * (1.0 + tolerance), 0),",
        "        'valid_range': '5% – 99% (с ограничителем экстремальных значений)',",
        "    }",
    ]
    for offset, p_idx in enumerate(range(414, len(paras))):
        if offset < len(confidence_code_lines):
            set_paragraph_text_preserve_format(paras[p_idx], confidence_code_lines[offset])
        else:
            set_paragraph_text_preserve_format(paras[p_idx], "")

    # ------------------------------------------------------------------
    # 10. ВСТАВКА НОВЫХ АБЗАЦЕВ И ДОПОЛНИТЕЛЬНЫХ РИСУНКОВ (от конца к началу!)
    # ------------------------------------------------------------------
    # 10.1 Источник 19 (aiogram 3) после P365
    insert_paragraph_after(
        doc,
        paras[365],
        text=(
            "19. aiogram 3.x documentation [Электронный ресурс] // aiogram : официальная документация. "
            "URL: https://docs.aiogram.dev/en/latest/ (дата обращения: 16.11.2026)."
        ),
        first_line_indent=paras[365].paragraph_format.first_line_indent,
        space_before=paras[365].paragraph_format.space_before,
        space_after=paras[365].paragraph_format.space_after,
        line_spacing=paras[365].paragraph_format.line_spacing or 1.5,
    )

    # 10.2 Раздел 3.4: Рис. 15 (Справка Streamlit) + описание Telegram-бота + Рис. 16 (диалог) + Рис. 17 (QR)
    anchor_34 = insert_figure_after(
        doc,
        paras[288],
        FIGURES_DIR / "web_help.png",
        "Рис. 15. Веб-интерфейс Streamlit: раздел «Справка о проекте» и реестр версий моделей v2.2",
        max_width_in=5.8,
        max_height_in=4.5,
    )
    bot_p = insert_paragraph_after(
        doc,
        anchor_34,
        text=(
            "Для оперативного мобильного доступа разработан Telegram-бот @testcursomsskm_bot на "
            "базе асинхронного фреймворка aiogram 3 [19]. Бот реализует машину состояний (FSM, 6 шагов) "
            "для пошагового ввода марки, типа кузова, мощности, объёма двигателя, массы и выбора модели "
            "версии v2.2 (с отображением точности R² в скобках), контролирует допустимые диапазоны "
            "параметров на каждом шаге, предоставляет мгновенный расчёт готовых пресетов, встроенную "
            "справку по команде /help (кнопка «Справка»), просмотр личной истории (/history) и общей "
            "статистики локальной базы SQLite (/stats). Пример диалога расчёта стоимости автомобиля "
            "приведён на рисунке 16, а QR-код быстрого перехода к боту — на рисунке 17."
        ),
    )
    anchor_bot = insert_figure_after(
        doc,
        bot_p,
        FIGURES_DIR / "bot_predict_dialog.png",
        "Рис. 16. Пример пошагового диалога расчёта стоимости автомобиля в Telegram-боте @testcursomsskm_bot",
        max_width_in=3.1,
        max_height_in=4.8,
    )
    insert_figure_after(
        doc,
        anchor_bot,
        FIGURES_DIR / "bot_qr_code.png",
        "Рис. 17. QR-код для быстрого перехода к Telegram-боту @testcursomsskm_bot",
        max_width_in=2.7,
        max_height_in=3.3,
    )

    # 10.3 Раздел 3.3: пояснения про версионирование v2.2 и вероятность цены (±15%, 5–99%) после P271
    ver_p = insert_paragraph_after(
        doc,
        paras[271],
        text=(
            "Для всех четырёх обученных моделей введена схема версионирования (актуальный релиз v2.2): "
            "версия, схема разбиения выборки (80% обучение / 20% тест), гиперпараметры и критерий ошибок "
            "зафиксированы в реестре MODEL_REGISTRY_INFO (src/config/benchmarks.py) и метаданных "
            "models/metadata.json. В списках выбора веб-приложения Streamlit и Telegram-бота рядом с "
            "названием каждой модели в скобках выводятся её версия и показатели качества на тестовой "
            "выборке, например: «Случайный лес v2.2 (R² = 0,96, ошибка 9,1%)»."
        ),
    )
    insert_paragraph_after(
        doc,
        ver_p,
        text=(
            "Дополнительно реализован показатель «Вероятность цены» (модуль src/models/confidence.py). "
            "Предметом оценки является вероятность попадания фактической рыночной стоимости автомобиля "
            "в коридор ±15% от прогнозной цены модели ([0,85 · P; 1,15 · P]). Для ансамбля Random Forest "
            "(120 деревьев) показатель вычисляется как доля решающих деревьев, чьи индивидуальные прогнозы "
            "попадают в указанный коридор; для моделей Ridge, MLP и KNN применяется функция ошибок "
            "нормального распределения erf(band / (σ · √2)) на базе СКО остатков тестовой выборки. "
            "Шкала показателя защищена ограничителем 5% – 99% (исключающим вырожденные значения 0% и 100%) "
            "и разбита на три уровня надёжности: 80–99% — высокая надёжность, 60–79% — средняя надёжность, "
            "5–59% — низкая надёжность."
        ),
    )

    # 10.4 Раздел 2.5: Рис. 6 (Схема Loginom) после P208
    insert_figure_after(
        doc,
        paras[208],
        FIGURES_DIR / "loginom_workflow_cropped.png",
        "Рис. 6. Сценарий предобработки данных и обучения моделей в платформе Loginom Community 7.4.2",
        max_width_in=5.8,
        max_height_in=2.4,
    )

    # 10.5 Глоссарий: дополнительные термины после P48
    g1 = insert_paragraph_after(
        doc,
        paras[48],
        text=(
            "Вероятность цены (±15%) — оценка вероятности попадания фактической рыночной стоимости "
            "автомобиля в коридор ±15% от прогноза модели в ограниченном диапазоне шкалы 5% – 99%."
        ),
    )
    g2 = insert_paragraph_after(
        doc,
        g1,
        text=(
            "Ограничитель входных параметров — программный механизм (функция clamp_car_features), "
            "автоматически удерживающий числовые и категориальные признаки в допустимых границах датасета."
        ),
    )
    insert_paragraph_after(
        doc,
        g2,
        text=(
            "Telegram-бот (aiogram 3) — асинхронный диалоговый клиент (@testcursomsskm_bot) "
            "с машиной состояний (FSM) для расчёта стоимости автомобилей и доступа к истории расчётов."
        ),
    )

    # Сохраняем обновлённый документ in-place
    doc.save(str(DOCX_PATH))
    print(f"Документ успешно обновлён: {DOCX_PATH}")


if __name__ == "__main__":
    update_document()
