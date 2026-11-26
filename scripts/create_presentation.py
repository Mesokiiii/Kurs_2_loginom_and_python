"""Генератор итоговой презентации к защите курсовой работы (16:9, 20 слайдов).

Скрипт динамически подгружает реальные метрики из reports/metrics.json,
статистику датасета из data/CarPrice_Assignment.csv и визуализации из reports/figures/,
формируя единый файл Презентация_Груздев_А_А.pptx.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt


# ---------------------------------------------------------------------------
# Пути и константы
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "reports" / "figures"
METRICS_PATH = ROOT / "reports" / "metrics.json"
DATA_PATH = ROOT / "data" / "CarPrice_Assignment.csv"
OUTPUT_PATH = ROOT / "Презентация_Груздев_А_А.pptx"

RUB_RATE = 93.5
SLIDE_W = 13.333
SLIDE_H = 7.5
TOTAL_SLIDES = 20

# Академическая/инженерная цветовая палитра (графит + изумрудно-бирюзовый + бордовый)
GRAPHITE = RGBColor(0x1E, 0x29, 0x3B)      # #1E293B — заголовки, тёмный фон
GRAPHITE_DARK = RGBColor(0x0F, 0x17, 0x2A) # #0F172A — глубокий акцент на тёмных слайдах
GRAPHITE_CARD = RGBColor(0x28, 0x35, 0x48) # #283548 — карточки на тёмных слайдах
TEAL = RGBColor(0x0F, 0x76, 0x6E)          # #0F766E — основной акцент
TEAL_LIGHT = RGBColor(0x14, 0xB8, 0xA6)    # #14B8A6 — светлый акцент для тёмного фона
BURGUNDY = RGBColor(0x9F, 0x12, 0x39)      # #9F1239 — вторичный акцент (Loginom / риски)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)         # #FFFFFF — чистый фон слайдов
CARD_BG = RGBColor(0xF1, 0xF5, 0xF9)       # #F1F5F9 — мягкая подложка карточек и строк
MINT_BG = RGBColor(0xF0, 0xFD, 0xFA)       # #F0FDFA — выделение лидера / ключевых блоков
ROSE_BG = RGBColor(0xFF, 0xF1, 0xF2)       # #FFF1F2 — мягкое выделение предупреждений
SLATE = RGBColor(0x47, 0x55, 0x69)         # #475569 — вторичный текст и подписи
SLATE_LIGHT = RGBColor(0xCB, 0xD5, 0xE1)   # #CBD5E1 — светлый текст на тёмном фоне / рамки
BORDER = RGBColor(0xCB, 0xD5, 0xE1)        # #CBD5E1 — тонкая рамка

FONT_MAIN = "Calibri"


# ---------------------------------------------------------------------------
# Форматирование чисел в российском стандарте
# ---------------------------------------------------------------------------
def fmt_ru(val: float, decimals: int = 1) -> str:
    """Форматирует число с запятой и пробелом-разделителем тысяч."""
    s = f"{val:,.{decimals}f}"
    return s.replace(",", " ").replace(".", ",")


def to_k_rub(raw_value: float) -> float:
    """Переводит исходное значение цены/ошибки в тыс. рублей."""
    return raw_value * RUB_RATE / 1000.0


# ---------------------------------------------------------------------------
# Вспомогательные функции работы со слайдами
# ---------------------------------------------------------------------------
def set_slide_bg(slide, color: RGBColor) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    fill_color: RGBColor | None = None,
    line_color: RGBColor | None = None,
    line_pt: float = 0.75,
    rounded: bool = False,
):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(
        shape_type, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    if rounded:
        try:
            shape.adjustments[0] = 0.05
        except Exception:
            pass
    if fill_color is not None:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color is not None:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(line_pt)
    else:
        shape.line.fill.background()
    return shape


def add_textbox(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str = "",
    font_size: float = 13,
    bold: bool = False,
    italic: bool = False,
    color: RGBColor = GRAPHITE,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.TOP,
    line_spacing: float = 1.15,
):
    tb = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(0.06)
    tf.margin_right = Inches(0.06)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    if text:
        p = tf.paragraphs[0]
        p.alignment = align
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = text
        run.font.name = FONT_MAIN
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
    return tb


def add_paragraphs(
    tf,
    lines: Sequence[tuple[str, str] | str],
    font_size: float = 12.5,
    color: RGBColor = GRAPHITE,
    bullet_prefix: str = "• ",
    space_after: float = 4,
    line_spacing: float = 1.15,
    bold_color: RGBColor | None = None,
) -> None:
    """Добавляет абзацы в text_frame.

    Элемент может быть строкой или кортежем (жирный_префикс, обычный_текст).
    """
    for idx, item in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        if isinstance(item, tuple):
            lead, body = item
            r1 = p.add_run()
            r1.text = f"{bullet_prefix}{lead}"
            r1.font.name = FONT_MAIN
            r1.font.size = Pt(font_size)
            r1.font.bold = True
            r1.font.color.rgb = bold_color or color
            if body:
                r2 = p.add_run()
                r2.text = body
                r2.font.name = FONT_MAIN
                r2.font.size = Pt(font_size)
                r2.font.bold = False
                r2.font.color.rgb = color
        else:
            r = p.add_run()
            r.text = f"{bullet_prefix}{item}"
            r.font.name = FONT_MAIN
            r.font.size = Pt(font_size)
            r.font.color.rgb = color


def add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    lines: Sequence[tuple[str, str] | str],
    bg_color: RGBColor = CARD_BG,
    accent_color: RGBColor = TEAL,
    border_color: RGBColor = BORDER,
    title_size: float = 13.5,
    body_size: float = 11.8,
    accent_side: str = "top",
    bullet_prefix: str = "• ",
    space_after: float = 3.5,
    badge_text: str | None = None,
    badge_color: RGBColor | None = None,
):
    """Создаёт аккуратную карточку с цветовой полосой, заголовком и списком."""
    add_rect(
        slide,
        left,
        top,
        width,
        height,
        fill_color=bg_color,
        line_color=border_color,
        line_pt=0.75,
        rounded=True,
    )
    if accent_side == "top":
        add_rect(slide, left + 0.04, top, width - 0.08, 0.06, fill_color=accent_color)
        tx_left = left + 0.14
        tx_w = width - 0.28
        title_top = top + 0.11
    else:
        add_rect(slide, left, top + 0.05, 0.07, height - 0.10, fill_color=accent_color)
        tx_left = left + 0.18
        tx_w = width - 0.28
        title_top = top + 0.09

    if badge_text:
        badge_w = min(2.45, max(1.65, len(badge_text) * 0.095))
        badge_h = 0.28
        add_rect(
            slide,
            left + width - badge_w - 0.12,
            title_top,
            badge_w,
            badge_h,
            fill_color=badge_color or accent_color,
            rounded=True,
        )
        add_textbox(
            slide,
            left + width - badge_w - 0.12,
            title_top,
            badge_w,
            badge_h,
            text=badge_text,
            font_size=9.5,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            valign=MSO_ANCHOR.MIDDLE,
        )
        title_w = tx_w - badge_w - 0.12
    else:
        title_w = tx_w

    add_textbox(
        slide,
        tx_left,
        title_top,
        title_w,
        0.34,
        text=title,
        font_size=title_size,
        bold=True,
        color=accent_color if accent_color != BORDER else GRAPHITE,
        valign=MSO_ANCHOR.MIDDLE,
    )
    body_top = title_top + 0.34
    body_h = max(0.3, (top + height) - body_top - 0.06)
    tb = add_textbox(slide, tx_left, body_top, tx_w, body_h)
    add_paragraphs(
        tb.text_frame,
        lines,
        font_size=body_size,
        color=GRAPHITE,
        bullet_prefix=bullet_prefix,
        space_after=space_after,
    )


def add_picture_fit(
    slide,
    img_path: Path,
    left: float,
    top: float,
    max_w: float,
    max_h: float,
    frame: bool = True,
    pad: float = 0.06,
    frame_bg: RGBColor = WHITE,
    frame_border: RGBColor = BORDER,
):
    """Вставляет изображение строго без искажений, вписывая и центрируя в бокс."""
    if not img_path.exists():
        raise FileNotFoundError(f"Не найдено изображение: {img_path}")

    with Image.open(img_path) as im:
        px_w, px_h = im.size

    inner_w = max_w - (2 * pad if frame else 0.0)
    inner_h = max_h - (2 * pad if frame else 0.0)
    scale = min(inner_w / px_w, inner_h / px_h)
    draw_w = px_w * scale
    draw_h = px_h * scale
    draw_left = left + (max_w - draw_w) / 2.0
    draw_top = top + (max_h - draw_h) / 2.0

    if frame:
        add_rect(
            slide,
            draw_left - pad,
            draw_top - pad,
            draw_w + 2 * pad,
            draw_h + 2 * pad,
            fill_color=frame_bg,
            line_color=frame_border,
            line_pt=0.75,
            rounded=False,
        )

    pic = slide.shapes.add_picture(
        str(img_path),
        Inches(draw_left),
        Inches(draw_top),
        width=Inches(draw_w),
        height=Inches(draw_h),
    )
    return pic


def set_cell_border(cell, color_hex: str = "CBD5E1", width_emu: int = 6350) -> None:
    """Устанавливает аккуратные тонкие границы ячейки таблицы."""
    tcPr = cell._tc.get_or_add_tcPr()
    for edge in ("lnL", "lnR", "lnT", "lnB"):
        existing = tcPr.find(qn(f"a:{edge}"))
        if existing is not None:
            tcPr.remove(existing)
        ln = OxmlElement(f"a:{edge}")
        ln.set("w", str(width_emu))
        ln.set("cap", "flat")
        ln.set("cmpd", "sng")
        ln.set("algn", "ctr")
        solidFill = OxmlElement("a:solidFill")
        srgbClr = OxmlElement("a:srgbClr")
        srgbClr.set("val", color_hex)
        solidFill.append(srgbClr)
        ln.append(solidFill)
        tcPr.append(ln)


def add_styled_table(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[float],
    font_size: float = 10.5,
    header_size: float = 10.8,
    header_bg: RGBColor = TEAL,
    highlight_rows: dict[int, RGBColor] | None = None,
    bold_rows: set[int] | None = None,
    col_aligns: Sequence[PP_ALIGN] | None = None,
):
    """Создаёт стилизованную таблицу без стандартной синей темы PowerPoint."""
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table_shape = slide.shapes.add_table(
        n_rows, n_cols, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    table = table_shape.table
    table.first_row = True
    table.horz_banding = False

    total_w = sum(col_widths)
    for c_idx, cw in enumerate(col_widths):
        table.columns[c_idx].width = Inches(width * (cw / total_w))

    highlight_rows = highlight_rows or {}
    bold_rows = bold_rows or set()

    # Заголовок
    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_bg
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.08)
        cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.04)
        cell.margin_bottom = Inches(0.04)
        set_cell_border(cell, "0F766E" if header_bg == TEAL else "1E293B")
        p = cell.text_frame.paragraphs[0]
        p.alignment = col_aligns[c_idx] if col_aligns else PP_ALIGN.LEFT
        run = p.add_run()
        run.text = h_text
        run.font.name = FONT_MAIN
        run.font.size = Pt(header_size)
        run.font.bold = True
        run.font.color.rgb = WHITE

    # Данные
    for r_idx, row_vals in enumerate(rows):
        row_bg = highlight_rows.get(r_idx, WHITE if r_idx % 2 == 0 else CARD_BG)
        is_bold_row = r_idx in bold_rows
        for c_idx, val in enumerate(row_vals):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_bg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            set_cell_border(cell, "CBD5E1")
            p = cell.text_frame.paragraphs[0]
            p.alignment = col_aligns[c_idx] if col_aligns else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(val)
            run.font.name = FONT_MAIN
            run.font.size = Pt(font_size)
            run.font.bold = is_bold_row or (c_idx == 0)
            run.font.color.rgb = GRAPHITE

    return table_shape


def add_header_footer(
    slide,
    slide_num: int,
    title: str,
    section_tag: str,
    tag_color: RGBColor = TEAL,
) -> None:
    """Единый чистый каркас для контентных слайдов (2–18)."""
    set_slide_bg(slide, WHITE)
    # Вертикальная акцентная полоска слева в шапке
    add_rect(slide, 0.45, 0.22, 0.08, 0.50, fill_color=tag_color)
    # Заголовок слайда
    add_textbox(
        slide,
        0.60,
        0.18,
        9.95,
        0.58,
        text=title,
        font_size=22,
        bold=True,
        color=GRAPHITE,
        valign=MSO_ANCHOR.MIDDLE,
    )
    # Плашка раздела справа
    tag_w = 2.25
    add_rect(
        slide,
        SLIDE_W - 0.45 - tag_w,
        0.26,
        tag_w,
        0.38,
        fill_color=MINT_BG if tag_color == TEAL else ROSE_BG,
        line_color=tag_color,
        line_pt=1.0,
        rounded=True,
    )
    add_textbox(
        slide,
        SLIDE_W - 0.45 - tag_w,
        0.26,
        tag_w,
        0.38,
        text=section_tag,
        font_size=10.5,
        bold=True,
        color=tag_color,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )
    # Горизонтальная разделительная линия под шапкой
    add_rect(slide, 0.45, 0.82, SLIDE_W - 0.90, 0.03, fill_color=TEAL)

    # Нижний колонтитул
    add_rect(slide, 0.45, 7.12, SLIDE_W - 0.90, 0.015, fill_color=BORDER)
    add_textbox(
        slide,
        0.45,
        7.15,
        9.60,
        0.28,
        text="ТвГТУ • Груздев А.А. • Прогнозирование цен на автомобили на Python (модели v2.2)",
        font_size=9.5,
        color=SLATE,
        valign=MSO_ANCHOR.MIDDLE,
    )
    add_textbox(
        slide,
        11.20,
        7.15,
        1.68,
        0.28,
        text=f"Слайд {slide_num} / {TOTAL_SLIDES}",
        font_size=9.5,
        bold=True,
        color=TEAL,
        align=PP_ALIGN.RIGHT,
        valign=MSO_ANCHOR.MIDDLE,
    )


# ---------------------------------------------------------------------------
# Сборка всех 19 слайдов
# ---------------------------------------------------------------------------
def build_presentation() -> Path:
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)

    df = pd.read_csv(DATA_PATH)
    price_rub = df["price"] * RUB_RATE
    p_min_k = price_rub.min() / 1000.0
    p_med_k = price_rub.median() / 1000.0
    p_mean_k = price_rub.mean() / 1000.0
    p_q75_m = price_rub.quantile(0.75) / 1_000_000.0
    p_max_m = price_rub.max() / 1_000_000.0
    p_max_k = price_rub.max() / 1000.0

    # Извлечение точных метрик из reports/metrics.json (в тыс. руб.)
    rf = metrics["random_forest"]
    ridge = metrics["linear_regression"]
    mlp = metrics["neural_network"]
    knn = metrics["knn"]

    rf_mae_k, rf_rmse_k = to_k_rub(rf["test"]["mae"]), to_k_rub(rf["test"]["rmse"])
    ri_mae_k, ri_rmse_k = to_k_rub(ridge["test"]["mae"]), to_k_rub(ridge["test"]["rmse"])
    ml_mae_k, ml_rmse_k = to_k_rub(mlp["test"]["mae"]), to_k_rub(mlp["test"]["rmse"])
    kn_mae_k, kn_rmse_k = to_k_rub(knn["test"]["mae"]), to_k_rub(knn["test"]["rmse"])

    log_lin = ridge["loginom_benchmark"]
    log_mlp = mlp["loginom_benchmark"]
    ll_mae_k, ll_rmse_k = to_k_rub(log_lin["mae_test"]), to_k_rub(log_lin["rmse_test"])
    lm_mae_k, lm_rmse_k = to_k_rub(log_mlp["mae_test"]), to_k_rub(log_mlp["rmse_test"])

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # СЛАЙД 1: ТИТУЛЬНЫЙ
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, GRAPHITE)
    # Геометрические акценты без жёлтого/синего
    add_rect(s1, 0.0, 0.0, 0.26, SLIDE_H, fill_color=TEAL)
    add_rect(s1, 0.26, 0.0, 0.06, SLIDE_H, fill_color=BURGUNDY)
    add_rect(s1, 9.80, 0.0, 3.533, SLIDE_H, fill_color=GRAPHITE_DARK)
    add_rect(s1, 9.80, 0.0, 0.04, SLIDE_H, fill_color=TEAL)

    # Шапка вуза
    add_textbox(
        s1,
        0.75,
        0.48,
        8.75,
        0.95,
        text=(
            "Министерство науки и высшего образования Российской Федерации\n"
            "ФГБОУ ВО «Тверской государственный технический университет» (ТвГТУ)\n"
            "Факультет информационных технологий • Кафедра программного обеспечения"
        ),
        font_size=12.5,
        color=SLATE_LIGHT,
        line_spacing=1.25,
    )

    # Плашка «КУРСОВАЯ РАБОТА»
    add_rect(s1, 0.75, 1.65, 3.55, 0.42, fill_color=TEAL, rounded=True)
    add_textbox(
        s1,
        0.75,
        1.65,
        3.55,
        0.42,
        text="КУРСОВАЯ РАБОТА • ВАРИАНТ 2",
        font_size=12.5,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )

    # Основной заголовок
    add_textbox(
        s1,
        0.75,
        2.25,
        8.75,
        1.85,
        text="Разработка приложения на языке программирования Python для прогнозирования цен на автомобили",
        font_size=28.5,
        bold=True,
        color=WHITE,
        line_spacing=1.18,
    )

    # Направление
    add_textbox(
        s1,
        0.75,
        4.20,
        8.75,
        0.65,
        text="Направление 09.03.04 «Программная инженерия»\nПрофиль: «Искусственный интеллект»",
        font_size=14,
        color=TEAL_LIGHT,
        line_spacing=1.25,
    )

    # Нижняя карточка исполнителя и руководителя
    add_rect(
        s1,
        0.75,
        5.12,
        8.70,
        1.78,
        fill_color=GRAPHITE_CARD,
        line_color=TEAL,
        line_pt=1.0,
        rounded=True,
    )
    add_rect(s1, 0.75, 5.18, 0.08, 1.66, fill_color=TEAL)
    tb1 = add_textbox(s1, 1.00, 5.24, 8.30, 1.56)
    add_paragraphs(
        tb1.text_frame,
        [
            ("Выполнил: ", "студент 2 курса, группа Б.ПИН.ИИ.25.16, Груздев Андрей Александрович"),
            ("Научный руководитель: ", "Крутских Е.И., доцент, канд. техн. наук"),
            ("Место и год защиты: ", "г. Тверь — 2026 г."),
        ],
        font_size=13.5,
        color=WHITE,
        bullet_prefix="",
        space_after=8,
        bold_color=TEAL_LIGHT,
    )

    # Правая информационная колонка-сводка ключевых показателей проекта
    add_textbox(
        s1,
        10.10,
        0.65,
        2.95,
        0.45,
        text="КЛЮЧЕВЫЕ ИТОГИ",
        font_size=12,
        bold=True,
        color=TEAL_LIGHT,
    )
    kpis_title = [
        ("R² = 0,958", "Случайный лес v2.2\nсредняя ошибка 9,14%"),
        ("4 модели v2.2", "Random Forest, Ridge,\nнейросеть MLP и KNN"),
        ("2 интерфейса", "Веб (Streamlit) +\nTelegram-бот + SQLite"),
        ("35 автотестов", "100% успешных проверок\nв модульном наборе pytest"),
    ]
    for idx, (val, desc) in enumerate(kpis_title):
        y = 1.25 + idx * 1.42
        add_rect(
            s1,
            10.10,
            y,
            2.90,
            1.22,
            fill_color=GRAPHITE_CARD,
            line_color=TEAL if idx % 2 == 0 else BURGUNDY,
            line_pt=1.0,
            rounded=True,
        )
        add_textbox(
            s1,
            10.25,
            y + 0.10,
            2.60,
            0.42,
            text=val,
            font_size=20,
            bold=True,
            color=TEAL_LIGHT if idx % 2 == 0 else WHITE,
        )
        add_textbox(
            s1,
            10.25,
            y + 0.54,
            2.60,
            0.60,
            text=desc,
            font_size=11,
            color=SLATE_LIGHT,
            line_spacing=1.15,
        )

    # =========================================================================
    # СЛАЙД 2: ПОСТАНОВКА ЗАДАЧИ И ЭТАПЫ РАБОТЫ
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header_footer(s2, 2, "Постановка задачи и основные этапы работы", "Введение")

    # Верхний ряд — 3 карточки: Актуальность, Цель, Объект и предмет
    top_cards = [
        (
            "Актуальность задачи",
            TEAL,
            MINT_BG,
            [
                "Цена автомобиля зависит от десятков технических параметров и бренда.",
                "Ручная оценка субъективна; модели машинного обучения дают быстрый и воспроизводимый расчёт в рублях.",
            ],
        ),
        (
            "Цель курсовой работы",
            BURGUNDY,
            ROSE_BG,
            [
                "Спроектировать и разработать программный комплекс на Python для прогнозирования цены авто.",
                "Объединить обучение моделей v2.2, веб-интерфейс, Telegram-бот и логирование расчётов.",
            ],
        ),
        (
            "Объект и предмет",
            GRAPHITE,
            CARD_BG,
            [
                ("Объект: ", "рынок легковых автомобилей и их технические характеристики."),
                ("Предмет: ", "регрессионные модели ML (Python и Loginom), оценка вероятности цены и программная реализация."),
            ],
        ),
    ]
    for i, (ctitle, cacc, cbg, clines) in enumerate(top_cards):
        add_card(
            s2,
            left=0.45 + i * 4.22,
            top=0.98,
            width=3.99,
            height=1.92,
            title=ctitle,
            lines=clines,
            bg_color=cbg,
            accent_color=cacc,
            title_size=13.5,
            body_size=11.5,
        )

    # Заголовок секции этапов
    add_textbox(
        s2,
        0.45,
        3.04,
        12.43,
        0.38,
        text="Что было выполнено на каждом этапе разработки:",
        font_size=15,
        bold=True,
        color=GRAPHITE,
    )

    stages = [
        (
            "1. Подготовка и очистка данных",
            "Изучены 205 авто и 26 столбцов; исправлены 6 опечаток в марках, цены переведены в рубли (× 93,5), добавлены 2 расчётных признака.",
            TEAL,
        ),
        (
            "2. Разведочный и OLAP-анализ",
            "Исследованы распределение цен, корреляции характеристик с ценой и многомерные срезы по типу кузова, топлива и привода.",
            TEAL,
        ),
        (
            "3. Контрольный сценарий в Loginom",
            "Построен аналитический граф из 9 узлов в Loginom 7.4.2 (70/30): обучены линейная регрессия и двухслойный перцептрон.",
            BURGUNDY,
        ),
        (
            "4. Обучение 4 моделей Python (v2.2)",
            "Разбиение 80% обучение (164 авто) / 20% тест (41 авто), 69 признаков; обучены Random Forest, Ridge, MLP и KNN, сохранены в .joblib.",
            TEAL,
        ),
        (
            "5. Веб-приложение и Telegram-бот",
            "Созданы веб-сайт (Streamlit) и бот @testcursomsskm_bot: ограничители ввода, кнопка Reset, вероятность ±15%, пресеты, Справка и SQLite-лог.",
            GRAPHITE,
        ),
        (
            "6. Автоматизированное тестирование",
            "Разработан набор из 35 модульных тестов (pytest) по 6 компонентам системы — все 35 проверок пройдены без ошибок (100%).",
            TEAL,
        ),
    ]
    for idx, (st_title, st_text, st_acc) in enumerate(stages):
        row = idx // 3
        col = idx % 3
        x = 0.45 + col * 4.22
        y = 3.50 + row * 1.76
        add_card(
            s2,
            left=x,
            top=y,
            width=3.99,
            height=1.62,
            title=st_title,
            lines=[st_text],
            bg_color=CARD_BG,
            accent_color=st_acc,
            accent_side="left",
            title_size=12.5,
            body_size=11.0,
            bullet_prefix="",
        )

    # =========================================================================
    # СЛАЙД 3: ИСХОДНЫЕ ДАННЫЕ — ВЫБОРКА И КАТЕГОРИАЛЬНЫЕ СТОЛБЦЫ
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s3, 3, "Исходные данные: состав выборки и категориальные столбцы", "Данные (1/2)"
    )

    kpis_data = [
        ("205 автомобилей", "Объём исходного датасета CarPrice"),
        ("26 столбцов", "12 категориальных / ID + 14 числовых"),
        ("6 опечаток марок", "Исправлены (maxda → mazda и др.)"),
        ("164 / 41 авто", "Разбиение Python: 80% обучение / 20% тест"),
    ]
    for i, (big, sub) in enumerate(kpis_data):
        x = 0.45 + i * 3.15
        add_rect(s3, x, 0.96, 2.98, 0.88, fill_color=MINT_BG if i == 3 else CARD_BG, line_color=TEAL if i == 3 else BORDER, line_pt=0.9, rounded=True)
        add_textbox(s3, x + 0.10, 1.00, 2.78, 0.42, text=big, font_size=16, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
        add_textbox(s3, x + 0.08, 1.42, 2.82, 0.38, text=sub, font_size=9.8, color=SLATE, align=PP_ALIGN.CENTER)

    cat_rows = [
        ["car_ID", "Идентификатор записи", "Целые числа 1–205", "Служебный (исключён из модели)"],
        ["symboling", "Страховой рейтинг риска", "От −2 (безопасный) до +3 (рисковый)", "Числовой / ординальный признак"],
        ["CarName", "Марка и модель автомобиля", "22 уникальные марки после очистки", "Извлечена марка (brand) → One-Hot"],
        ["fueltype", "Тип топлива двигателя", "Бензин (gas), дизель (diesel)", "Категориальный → One-Hot"],
        ["aspiration", "Тип наддува двигателя", "Атмосферный (std), турбированный (turbo)", "Категориальный → One-Hot"],
        ["doornumber", "Количество дверей кузова", "Две (two), четыре (four)", "Категориальный → One-Hot"],
        ["carbody", "Тип кузова автомобиля", "Седан, хэтчбек, универсал, хардтоп, кабриолет", "Категориальный → One-Hot"],
        ["drivewheel", "Тип привода колёс", "Передний (FWD), задний (RWD), полный (4WD)", "Категориальный → One-Hot"],
        ["enginelocation", "Расположение двигателя", "Спереди (front), сзади (rear)", "Категориальный → One-Hot"],
        ["enginetype", "Конструкция газораспределения", "7 типов (OHC, DOHC, OHCV, OHCF, роторный и др.)", "Категориальный → One-Hot"],
        ["cylindernumber", "Количество цилиндров", "От 2 до 12 (two, three, four, five, six, eight, twelve)", "Категориальный → One-Hot"],
        ["fuelsystem", "Система подачи топлива", "8 типов (распределённый MPFI, 2BBL, дизель IDI и др.)", "Категориальный → One-Hot"],
    ]
    add_styled_table(
        s3,
        left=0.45,
        top=1.98,
        width=12.43,
        height=5.00,
        headers=["Столбец таблицы", "Что означает (по-русски)", "Значения и расшифровка", "Использование в модели"],
        rows=cat_rows,
        col_widths=[1.75, 2.95, 4.70, 3.03],
        font_size=10.0,
        header_size=10.5,
        highlight_rows={2: MINT_BG, 7: MINT_BG},
    )

    # =========================================================================
    # СЛАЙД 4: ЧИСЛОВЫЕ СТОЛБЦЫ ТАБЛИЦЫ ДАННЫХ И НОВЫЕ ПРИЗНАКИ
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s4, 4, "Числовые столбцы таблицы данных и инженерные признаки", "Данные (2/2)"
    )

    num_rows = [
        ["wheelbase", "Колёсная база", "86,6 – 120,9 дюйма"],
        ["carlength", "Длина кузова", "141,1 – 208,1 дюйма"],
        ["carwidth", "Ширина кузова", "60,3 – 72,3 дюйма"],
        ["carheight", "Высота кузова", "47,8 – 59,8 дюйма"],
        ["curbweight", "Снаряжённая масса автомобиля", "1 488 – 4 066 фунтов"],
        ["enginesize", "Рабочий объём двигателя", "61 – 326 куб. дюймов"],
        ["boreratio", "Диаметр цилиндра", "2,54 – 3,94 дюйма"],
        ["stroke", "Ход поршня", "2,07 – 4,17 дюйма"],
        ["compressionratio", "Степень сжатия в цилиндрах", "7,0 – 23,0"],
        ["horsepower", "Мощность двигателя", "48 – 288 л.с."],
        ["peakrpm", "Обороты максимальной мощности", "4 150 – 6 600 об/мин"],
        ["citympg", "Экономичность в городе", "13 – 49 миль/галлон (MPG)"],
        ["highwaympg", "Экономичность на трассе", "16 – 54 миль/галлон (MPG)"],
        [
            "price (целевая)",
            "Рыночная цена авто в рублях (× 93,5)",
            f"{fmt_ru(p_min_k, 1)} тыс. – {fmt_ru(p_max_m, 2)} млн руб.",
        ],
    ]
    add_styled_table(
        s4,
        left=0.45,
        top=0.96,
        width=8.65,
        height=6.04,
        headers=["Столбец", "Русское значение", "Диапазон и единицы измерения"],
        rows=num_rows,
        col_widths=[1.85, 3.65, 3.15],
        font_size=9.7,
        header_size=10.3,
        highlight_rows={13: MINT_BG},
        bold_rows={13},
    )

    # Правая колонка: перевод в рубли, 2 новых признака, итоговая матрица
    add_card(
        s4,
        left=9.30,
        top=0.96,
        width=3.58,
        height=2.05,
        title="Пересчёт цен в рубли",
        lines=[
            ("Методика: ", "исходные значения столбца price пересчитаны по коэффициенту × 93,5."),
            ("Медиана: ", f"{fmt_ru(p_med_k, 1)} тыс. руб."),
            ("Средняя цена: ", f"{fmt_ru(p_mean_k, 1)} тыс. руб."),
            ("Максимум: ", f"{fmt_ru(p_max_k, 1)} тыс. руб."),
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=13,
        body_size=11.0,
    )
    add_card(
        s4,
        left=9.30,
        top=3.16,
        width=3.58,
        height=2.24,
        title="2 новых расчётных признака",
        lines=[
            ("power_to_weight: ", "удельная мощность (л.с. / масса в фунтах) — отражает разгонную динамику."),
            ("engine_to_weight: ", "удельный объём (куб. дюймы / масса) — отражает тяговый запас двигателя."),
        ],
        bg_color=CARD_BG,
        accent_color=BURGUNDY,
        title_size=13,
        body_size=11.0,
    )
    add_card(
        s4,
        left=9.30,
        top=5.55,
        width=3.58,
        height=1.45,
        title="Подготовка к обучению",
        lines=[
            "One-Hot кодирование категорий + стандартизация StandardScaler → итоговая матрица 69 признаков (random_state = 42).",
        ],
        bg_color=CARD_BG,
        accent_color=GRAPHITE,
        title_size=12.5,
        body_size=10.8,
        bullet_prefix="",
    )

    # =========================================================================
    # СЛАЙД 5: РАЗВЕДОЧНЫЙ АНАЛИЗ — РАСПРЕДЕЛЕНИЕ ЦЕН
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s5, 5, "Разведочный анализ: распределение рыночных цен (в рублях)", "Анализ данных"
    )
    add_picture_fit(
        s5,
        FIG_DIR / "price_distribution.png",
        left=0.45,
        top=0.94,
        max_w=12.43,
        max_h=4.34,
        frame=True,
    )
    dist_cards = [
        ("Медиана: 962,6 тыс. руб.", "Ровно половина машин в выборке стоит дешевле 1 млн руб. — это массовый городской сегмент.", TEAL),
        ("Среднее: 1 241,4 тыс. руб.", "Средняя цена выше медианы, потому что премиальные модели тянут распределение вправо.", TEAL),
        ("75% машин до 1,54 млн руб.", "Основная масса предложений сосредоточена от 478,5 тыс. до 1,54 млн руб.", GRAPHITE),
        ("Максимум: 4,24 млн руб.", "Верхний «хвост» образуют редкие люксовые и спортивные авто (Porsche, Jaguar, BMW, Buick).", BURGUNDY),
    ]
    for i, (t, body, acc) in enumerate(dist_cards):
        add_card(
            s5,
            left=0.45 + i * 3.15,
            top=5.42,
            width=2.98,
            height=1.60,
            title=t,
            lines=[body],
            bg_color=MINT_BG if i == 0 else CARD_BG,
            accent_color=acc,
            title_size=12.0,
            body_size=10.5,
            bullet_prefix="",
        )

    # =========================================================================
    # СЛАЙД 6: КОРРЕЛЯЦИЯ ХАРАКТЕРИСТИК С ЦЕНОЙ ПРОСТЫМИ СЛОВАМИ
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s6, 6, "Корреляция характеристик автомобиля с ценой простыми словами", "Анализ данных"
    )
    add_picture_fit(
        s6,
        FIG_DIR / "correlation_heatmap.png",
        left=0.45,
        top=0.95,
        max_w=7.15,
        max_h=6.05,
        frame=True,
    )

    add_card(
        s6,
        left=7.80,
        top=0.95,
        width=5.08,
        height=1.42,
        title="Что означает коэффициент корреляции r?",
        lines=[
            "Число от −1 до +1 показывает, насколько тесно характеристика связана с ценой. Ближе к +1 — растут вместе; ближе к −1 — при росте параметра цена падает.",
        ],
        bg_color=CARD_BG,
        accent_color=GRAPHITE,
        title_size=13.0,
        body_size=11.2,
        bullet_prefix="",
    )
    add_card(
        s6,
        left=7.80,
        top=2.52,
        width=5.08,
        height=2.38,
        title="Сильная прямая связь (больше → дороже)",
        lines=[
            ("Объём двигателя (куб. дюймы): ", "r = +0,87 — самый сильный фактор цены."),
            ("Снаряжённая масса (фунты): ", "r = +0,84 — тяжёлые машины выше классом."),
            ("Мощность двигателя (л.с.): ", "r = +0,81 — мощные моторы стоят заметно дороже."),
            ("Ширина и длина кузова: ", "r = +0,76 и r = +0,68 — габаритный бизнес-класс."),
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=13.0,
        body_size=11.2,
    )
    add_card(
        s6,
        left=7.80,
        top=5.05,
        width=5.08,
        height=1.95,
        title="Обратная связь (экономичнее → дешевле)",
        lines=[
            ("Расход на трассе (миль/галлон, MPG): ", "r = −0,70."),
            ("Расход в городе (миль/галлон, MPG): ", "r = −0,69."),
            ("Простой смысл: ", "большой запас хода на галлоне характерен для компактных бюджетных автомобилей."),
        ],
        bg_color=ROSE_BG,
        accent_color=BURGUNDY,
        title_size=13.0,
        body_size=11.2,
    )

    # =========================================================================
    # СЛАЙД 7: МНОГОМЕРНЫЙ OLAP-АНАЛИЗ — КУЗОВ, ТОПЛИВО И ПРИВОД
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s7, 7, "Многомерный OLAP-анализ: кузов, топливо и тип привода", "OLAP-анализ"
    )
    add_picture_fit(
        s7,
        FIG_DIR / "olap_body_fuel_price.png",
        left=0.45,
        top=0.95,
        max_w=6.68,
        max_h=3.95,
        frame=True,
    )
    add_picture_fit(
        s7,
        FIG_DIR / "olap_drive_price.png",
        left=7.28,
        top=0.95,
        max_w=5.60,
        max_h=3.95,
        frame=True,
    )

    olap_cards = [
        (
            "Тип привода (главный контраст)",
            TEAL,
            MINT_BG,
            [
                ("Задний привод (RWD): ", "в среднем в ~2,1 раза дороже переднего (спорт- и бизнес-класс)."),
                ("Передний привод (FWD): ", "самый массовый и доступный городской сегмент; полный привод (4WD) — посередине."),
            ],
        ),
        (
            "Тип кузова",
            GRAPHITE,
            CARD_BG,
            [
                ("Самые дорогие: ", "хардтоп и кабриолет (премиальные и имиджевые версии)."),
                ("Массовые: ", "хэтчбек и универсал — наиболее бюджетны; седан представлен во всех ценовых категориях."),
            ],
        ),
        (
            "Топливо и тип наддува",
            BURGUNDY,
            ROSE_BG,
            [
                ("Дизель vs бензин: ", "дизельные модели в выборке в среднем дороже бензиновых аналогов."),
                ("Наддув: ", "турбированный двигатель заметно повышает стоимость по сравнению с атмосферным."),
            ],
        ),
    ]
    for i, (ot, oacc, obg, olines) in enumerate(olap_cards):
        add_card(
            s7,
            left=0.45 + i * 4.22,
            top=5.06,
            width=3.99,
            height=1.96,
            title=ot,
            lines=olines,
            bg_color=obg,
            accent_color=oacc,
            title_size=12.8,
            body_size=10.8,
        )

    # =========================================================================
    # СЛАЙД 8: МАТЕМАТИЧЕСКИЕ МОДЕЛИ МАШИННОГО ОБУЧЕНИЯ (ВЕРСИЯ v2.2)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s8, 8, "Математические модели машинного обучения (версия v2.2)", "Модели ML"
    )
    # Верхняя информационная плашка
    add_rect(s8, 0.45, 0.94, 12.43, 0.48, fill_color=GRAPHITE, rounded=True)
    add_textbox(
        s8,
        0.58,
        0.94,
        12.18,
        0.48,
        text="Версионирование: v2.2 • Обучающая выборка: 164 авто (80%) • Тестовая выборка: 41 авто (20%) • Признаков: 69 (One-Hot + StandardScaler)",
        font_size=11.8,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )

    model_cards = [
        (
            "1. Случайный лес (Random Forest v2.2)",
            f"R² = 0,96; ошибка {fmt_ru(rf['test']['mape'], 1)}%",
            MINT_BG,
            TEAL,
            [
                ("Принцип: ", "ансамбль из 120 решающих деревьев; итоговая цена — среднее их прогнозов."),
                ("Плюсы: ", "точно учитывает нелинейные связи объёма двигателя, массы и бренда."),
                ("Результат на тесте: ", f"R² = {fmt_ru(rf['test']['r2'], 3)}, средняя ошибка {fmt_ru(rf_mae_k, 1)} тыс. руб. — лидер проекта."),
            ],
        ),
        (
            "2. Гребневая регрессия (Ridge v2.2)",
            f"R² = 0,90; ошибка {fmt_ru(ridge['test']['mape'], 1)}%",
            CARD_BG,
            TEAL,
            [
                ("На чём обучалась: ", "ровно на 164 авто (80% выборки) по 69 признакам после One-Hot и StandardScaler; тест — 41 авто (20%)."),
                ("Принцип: ", "линейная регрессия с L2-регуляризацией (alpha = 1,5) против разброса весов."),
                ("Результат на тесте: ", f"R² = {fmt_ru(ridge['test']['r2'], 3)}, средняя ошибка {fmt_ru(ri_mae_k, 1)} тыс. руб."),
            ],
        ),
        (
            "3. Двухслойный перцептрон (Нейросеть MLP v2.2)",
            f"R² = 0,85; ошибка {fmt_ru(mlp['test']['mape'], 1)}%",
            CARD_BG,
            GRAPHITE,
            [
                ("Архитектура: ", "два скрытых слоя (64 и 32 нейрона), функция активации ReLU, оптимизатор Adam."),
                ("Особенность: ", "минимальный разрыв между обучением (0,876) и тестом (0,854), без переобучения."),
                ("Результат на тесте: ", f"R² = {fmt_ru(mlp['test']['r2'], 3)}, средняя ошибка {fmt_ru(ml_mae_k, 1)} тыс. руб. (малый объём данных для нейросети)."),
            ],
        ),
        (
            "4. Метод k ближайших соседей (KNN v2.2)",
            f"R² = 0,77; ошибка {fmt_ru(knn['test']['mape'], 1)}%",
            ROSE_BG,
            BURGUNDY,
            [
                ("Принцип: ", "находит 5 самых похожих машин (k = 5) и вычисляет цену с весами по расстоянию."),
                ("Ограничение: ", "сильно переобучается (R² обучение 0,999 → тест 0,770) на редких марках."),
                ("Результат на тесте: ", f"R² = {fmt_ru(knn['test']['r2'], 3)}, средняя ошибка {fmt_ru(kn_mae_k, 1)} тыс. руб."),
            ],
        ),
    ]
    for idx, (mtitle, mbadge, mbg, macc, mlines) in enumerate(model_cards):
        r = idx // 2
        c = idx % 2
        add_card(
            s8,
            left=0.45 + c * 6.35,
            top=1.56 + r * 2.76,
            width=6.08,
            height=2.62,
            title=mtitle,
            lines=mlines,
            bg_color=mbg,
            accent_color=macc,
            title_size=13.2,
            body_size=11.4,
            badge_text=mbadge,
            badge_color=macc,
        )

    # =========================================================================
    # СЛАЙД 9: СЦЕНАРИЙ В АНАЛИТИЧЕСКОЙ ПЛАТФОРМЕ LOGINOM 7.4.2
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s9, 9, "Аналитический сценарий в платформе Loginom 7.4.2", "Loginom 7.4.2", tag_color=BURGUNDY
    )
    add_picture_fit(
        s9,
        FIG_DIR / "loginom_workflow_cropped.png",
        left=0.45,
        top=0.96,
        max_w=12.43,
        max_h=3.68,
        frame=True,
    )

    add_card(
        s9,
        left=0.45,
        top=4.80,
        width=6.08,
        height=2.22,
        title="Структура сценария kursovaya.lgp (9 узлов)",
        lines=[
            ("Вход и очистка: ", "загрузка таблицы CarPrice_Assignment.csv, приведение типов и исключение служебного ID."),
            ("Разбиение выборки: ", "70% данных — на обучение, 30% — на контрольную проверку."),
            ("Обученные модели: ", "Линейная регрессия (аналог гребневой Ridge) и Нейросеть (двухслойный перцептрон)."),
        ],
        bg_color=CARD_BG,
        accent_color=BURGUNDY,
        title_size=13.2,
        body_size=11.3,
    )
    add_card(
        s9,
        left=6.80,
        top=4.80,
        width=6.08,
        height=2.22,
        title="Контрольные результаты Loginom (в рублях)",
        lines=[
            (
                "Линейная регрессия (тест): ",
                f"R² = {fmt_ru(log_lin['r2_test'], 3)}, MAE = {fmt_ru(ll_mae_k, 1)} тыс. руб., RMSE = {fmt_ru(ll_rmse_k, 1)} тыс. руб., MAPE = {fmt_ru(log_lin['mape_test'], 2)}%.",
            ),
            (
                "Нейросеть — двухсл. перцептрон (тест): ",
                f"R² = {fmt_ru(log_mlp['r2_test'], 3)}, MAE = {fmt_ru(lm_mae_k, 1)} тыс. руб., RMSE = {fmt_ru(lm_rmse_k, 1)} тыс. руб., MAPE = {fmt_ru(log_mlp['mape_test'], 2)}%.",
            ),
            ("Зачем нужен Loginom: ", "независимый эталон для проверки точности Python-реализации."),
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=13.2,
        body_size=11.3,
    )

    # =========================================================================
    # СЛАЙД 10: ВНУТРЕННИЕ ДИАГРАММЫ И ОТЧЁТЫ LOGINOM 7.4.2
    # =========================================================================
    s9b = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s9b, 10, "Внутренние визуализаторы и диаграммы Loginom 7.4.2", "Loginom 7.4.2", tag_color=BURGUNDY
    )
    add_textbox(
        s9b,
        0.45,
        0.86,
        12.43,
        0.26,
        text="1. Встроенный «Отчет по регрессии» (метрики модели, F-статистика, коэффициенты, T-статистика и 95% ДИ)",
        font_size=11.0,
        bold=True,
        color=GRAPHITE,
    )
    add_picture_fit(
        s9b,
        FIG_DIR / "loginom_regression_report.png",
        left=0.45,
        top=1.13,
        max_w=12.43,
        max_h=2.70,
        frame=True,
    )
    add_textbox(
        s9b,
        0.45,
        3.92,
        7.55,
        0.26,
        text="2. Встроенный визуализатор «Статистика» (гистограммы и диаграммы размаха нейросети)",
        font_size=11.0,
        bold=True,
        color=GRAPHITE,
    )
    add_picture_fit(
        s9b,
        FIG_DIR / "loginom_statistics_viz.png",
        left=0.45,
        top=4.19,
        max_w=7.55,
        max_h=2.84,
        frame=True,
    )
    add_card(
        s9b,
        left=8.20,
        top=4.19,
        width=4.68,
        height=2.84,
        title="Что показывают отчёты Loginom",
        lines=[
            ("Отчёт по регрессии: ", "автоматический расчёт коэффициентов, стандартных ошибок, T-статистики, P-значений и критериев Акаике / Байеса."),
            ("Статистика и диаграммы: ", "гистограммы распределений и диаграммы размаха (boxplot) для каждого входного фактора и выхода нейросети."),
            ("Контроль качества: ", "все 9 узлов графа выполнены без ошибок (зелёный статус), пропуски = 0."),
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=12.8,
        body_size=10.8,
    )

    # =========================================================================
    # СЛАЙД 11: СРАВНЕНИЕ PYTHON И LOGINOM — RIDGE И НЕЙРОСЕТЬ MLP
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s10, 11, "Сравнение Python и Loginom: Ridge и двухслойный перцептрон", "Сравнение"
    )
    cmp_rows = [
        [
            "Гребневая регрессия Ridge v2.2 (Python)",
            "80% / 20%",
            fmt_ru(ridge["train"]["r2"], 3),
            fmt_ru(ridge["test"]["r2"], 3),
            fmt_ru(ri_mae_k, 1),
            fmt_ru(ri_rmse_k, 1),
            f"{fmt_ru(ridge['test']['mape'], 2)}%",
        ],
        [
            "Линейная регрессия (Loginom 7.4.2)",
            "70% / 30%",
            "—",
            fmt_ru(log_lin["r2_test"], 3),
            fmt_ru(ll_mae_k, 1),
            fmt_ru(ll_rmse_k, 1),
            f"{fmt_ru(log_lin['mape_test'], 2)}%",
        ],
        [
            "Двухслойный перцептрон MLP v2.2 (Python)",
            "80% / 20%",
            fmt_ru(mlp["train"]["r2"], 3),
            fmt_ru(mlp["test"]["r2"], 3),
            fmt_ru(ml_mae_k, 1),
            fmt_ru(ml_rmse_k, 1),
            f"{fmt_ru(mlp['test']['mape'], 2)}%",
        ],
        [
            "Нейросеть — двухсл. перцептрон (Loginom 7.4.2)",
            "70% / 30%",
            "—",
            fmt_ru(log_mlp["r2_test"], 3),
            fmt_ru(lm_mae_k, 1),
            fmt_ru(lm_rmse_k, 1),
            f"{fmt_ru(log_mlp['mape_test'], 2)}%",
        ],
    ]
    add_styled_table(
        s10,
        left=0.45,
        top=0.94,
        width=12.43,
        height=2.45,
        headers=[
            "Модель и платформа",
            "Выборка (обуч./тест)",
            "R² (Обучение)",
            "R² (Тест)",
            "MAE тест (тыс. руб.)",
            "RMSE тест (тыс. руб.)",
            "MAPE тест",
        ],
        rows=cmp_rows,
        col_widths=[4.45, 1.50, 1.25, 1.15, 1.45, 1.50, 1.13],
        font_size=10.3,
        header_size=10.3,
        highlight_rows={0: MINT_BG},
        col_aligns=[
            PP_ALIGN.LEFT,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
        ],
    )

    add_picture_fit(
        s10,
        FIG_DIR / "model_comparison_metrics.png",
        left=0.45,
        top=3.56,
        max_w=8.15,
        max_h=3.46,
        frame=True,
    )
    add_card(
        s10,
        left=8.78,
        top=3.56,
        width=4.10,
        height=3.46,
        title="Вывод сравнения простыми словами",
        lines=[
            ("Полная сопоставимость: ", "обе платформы показывают близкую точность (расхождение R² < 0,02), что подтверждает верность расчётов."),
            ("Преимущество Ridge в Python: ", "благодаря L2-регуляризации и 2 новым признакам R² выше на +0,018 (0,899 против 0,881)."),
            ("Нейросеть MLP: ", "R² = 0,854 совпал до третьего знака в Python и Loginom — на 205 авто нейросеть уступает ансамблю деревьев."),
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=12.8,
        body_size=11.0,
    )

    # =========================================================================
    # СЛАЙД 11: СРАВНЕНИЕ ВСЕХ 4 МОДЕЛЕЙ PYTHON v2.2 — ОБУЧЕНИЕ И ТЕСТ
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s11, 12, "Сравнение всех 4 моделей Python v2.2: Обучение и Тест", "Результаты ML"
    )

    py_rows = [
        [
            f"Случайный лес — Random Forest v2.2 (R² = 0,96; ошибка {fmt_ru(rf['test']['mape'], 1)}%)",
            fmt_ru(rf["train"]["r2"], 3),
            fmt_ru(rf["test"]["r2"], 3),
            fmt_ru(rf["train"]["r2"] - rf["test"]["r2"], 3),
            fmt_ru(rf_mae_k, 1),
            fmt_ru(rf_rmse_k, 1),
            f"{fmt_ru(rf['test']['mape'], 2)}%",
        ],
        [
            f"Гребневая регрессия — Ridge v2.2 (R² = 0,90; ошибка {fmt_ru(ridge['test']['mape'], 1)}%)",
            fmt_ru(ridge["train"]["r2"], 3),
            fmt_ru(ridge["test"]["r2"], 3),
            fmt_ru(ridge["train"]["r2"] - ridge["test"]["r2"], 3),
            fmt_ru(ri_mae_k, 1),
            fmt_ru(ri_rmse_k, 1),
            f"{fmt_ru(ridge['test']['mape'], 2)}%",
        ],
        [
            f"Двухслойный перцептрон — MLP v2.2 (R² = 0,85; ошибка {fmt_ru(mlp['test']['mape'], 1)}%)",
            fmt_ru(mlp["train"]["r2"], 3),
            fmt_ru(mlp["test"]["r2"], 3),
            fmt_ru(mlp["train"]["r2"] - mlp["test"]["r2"], 3),
            fmt_ru(ml_mae_k, 1),
            fmt_ru(ml_rmse_k, 1),
            f"{fmt_ru(mlp['test']['mape'], 2)}%",
        ],
        [
            f"Метод ближайших соседей — KNN v2.2 (R² = 0,77; ошибка {fmt_ru(knn['test']['mape'], 1)}%)",
            fmt_ru(knn["train"]["r2"], 3),
            fmt_ru(knn["test"]["r2"], 3),
            fmt_ru(knn["train"]["r2"] - knn["test"]["r2"], 3),
            fmt_ru(kn_mae_k, 1),
            fmt_ru(kn_rmse_k, 1),
            f"{fmt_ru(knn['test']['mape'], 2)}%",
        ],
    ]
    add_styled_table(
        s11,
        left=0.45,
        top=0.96,
        width=12.43,
        height=3.40,
        headers=[
            "Модель (версия v2.2 и качество на тесте)",
            "R² (Обучение)",
            "R² (Тест)",
            "Разрыв R²",
            "MAE тест (тыс. руб.)",
            "RMSE тест (тыс. руб.)",
            "MAPE тест",
        ],
        rows=py_rows,
        col_widths=[5.05, 1.25, 1.15, 1.10, 1.35, 1.40, 1.13],
        font_size=10.5,
        header_size=10.5,
        highlight_rows={0: MINT_BG, 3: ROSE_BG},
        bold_rows={0},
        col_aligns=[
            PP_ALIGN.LEFT,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
            PP_ALIGN.CENTER,
        ],
    )

    summary_cards = [
        (
            "Победитель: Random Forest v2.2",
            TEAL,
            MINT_BG,
            [
                f"Максимальный R² на тесте ({fmt_ru(rf['test']['r2'], 3)}) и минимальная ошибка {fmt_ru(rf_mae_k, 1)} тыс. руб. ({fmt_ru(rf['test']['mape'], 2)}%).",
                "Малый разрыв между обучением и тестом (0,027) подтверждает отличную обобщающую способность.",
            ],
        ),
        (
            "Переобучение KNN v2.2",
            BURGUNDY,
            ROSE_BG,
            [
                "На обучающей выборке R² = 0,999, но на новых автомобилях падает до 0,770 (разрыв 0,229).",
                "Причина: алгоритм запоминает конкретные машины и ошибается на редких комплектациях (RMSE 398,2 тыс. руб.).",
            ],
        ),
        (
            "Польза всех 4 моделей в системе",
            GRAPHITE,
            CARD_BG,
            [
                "Random Forest v2.2 используется по умолчанию для самого точного прогноза.",
                "Пользователь может переключить модель в веб-приложении или боте и сравнить разброс оценок.",
            ],
        ),
    ]
    for i, (ct, cacc, cbg, clines) in enumerate(summary_cards):
        add_card(
            s11,
            left=0.45 + i * 4.22,
            top=4.60,
            width=3.99,
            height=2.40,
            title=ct,
            lines=clines,
            bg_color=cbg,
            accent_color=cacc,
            title_size=13.0,
            body_size=11.2,
        )

    # =========================================================================
    # СЛАЙД 12: СЛУЧАЙНЫЙ ЛЕС (RANDOM FOREST v2.2) — КРИТЕРИЙ ОШИБОК И ВАЖНОСТЬ
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s12, 13, "Случайный лес (Random Forest v2.2): критерий ошибок и факторы цены", "Лучшая модель"
    )
    add_picture_fit(
        s12,
        FIG_DIR / "feature_importance.png",
        left=0.45,
        top=0.95,
        max_w=5.95,
        max_h=3.65,
        frame=True,
    )
    add_picture_fit(
        s12,
        FIG_DIR / "residual_plots.png",
        left=6.58,
        top=0.95,
        max_w=6.30,
        max_h=3.65,
        frame=True,
    )

    rf_cards = [
        (
            "Критерий ошибок (MSE)",
            TEAL,
            CARD_BG,
            [
                "При построении 120 деревьев алгоритм минимизирует среднеквадратичную ошибку (MSE) в каждом узле.",
                "Усреднение ответов 120 независимых деревьев гасит случайные выбросы и снижает дисперсию прогноза.",
            ],
        ),
        (
            "Реальная точность на тесте (41 авто)",
            TEAL,
            MINT_BG,
            [
                f"R² = {fmt_ru(rf['test']['r2'], 3)} • MAE = {fmt_ru(rf_mae_k, 1)} тыс. руб. • RMSE = {fmt_ru(rf_rmse_k, 1)} тыс. руб. • MAPE = {fmt_ru(rf['test']['mape'], 2)}%.",
                "85,4% тестовых автомобилей укладываются в коридор ±15% от фактической рыночной цены.",
            ],
        ),
        (
            "Что сильнее всего влияет на цену?",
            GRAPHITE,
            CARD_BG,
            [
                "Объём двигателя (54,6%) и снаряжённая масса (27,5%) дают 82,1% суммарного вклада в прогноз.",
                "Дополнительно учитываются расход на трассе (5,2%), мощность (3,8%) и марка автомобиля.",
            ],
        ),
    ]
    for i, (rt, racc, rbg, rlines) in enumerate(rf_cards):
        add_card(
            s12,
            left=0.45 + i * 4.22,
            top=4.74,
            width=3.99,
            height=2.28,
            title=rt,
            lines=rlines,
            bg_color=rbg,
            accent_color=racc,
            title_size=12.8,
            body_size=11.0,
        )

    # =========================================================================
    # СЛАЙД 13: СХЕМА КОМПЛЕКСА — ПРОЕКТИРОВАНИЕ, ОБУЧЕНИЕ И ВЫГРУЗКА
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s13, 14, "Схема комплекса: проектирование, обучение и выгрузка моделей", "Архитектура"
    )
    add_picture_fit(
        s13,
        FIG_DIR / "system_block_diagram.png",
        left=0.45,
        top=0.94,
        max_w=12.43,
        max_h=4.92,
        frame=True,
    )

    arch_pills = [
        ("1. Проектирование и данные", "Очистка 205 авто, перевод цен в рубли (× 93,5), 69 признаков и строгие ограничители ввода.", TEAL),
        ("2. Обучение и выгрузка (v2.2)", "Обучение 4 моделей в scikit-learn, расчёт метрик (metrics.json) и выгрузка артефактов (.joblib).", GRAPHITE),
        ("3. Программные клиенты и лог", "Единый сервис прогнозирования обслуживает веб (Streamlit), Telegram-бот и журнал SQLite.", BURGUNDY),
    ]
    for i, (pt, pb, pacc) in enumerate(arch_pills):
        add_card(
            s13,
            left=0.45 + i * 4.22,
            top=5.96,
            width=3.99,
            height=1.08,
            title=pt,
            lines=[pb],
            bg_color=CARD_BG,
            accent_color=pacc,
            accent_side="left",
            title_size=11.8,
            body_size=10.0,
            bullet_prefix="",
        )

    # =========================================================================
    # СЛАЙД 14: АЛГОРИТМ, ОГРАНИЧИТЕЛЬ ВВОДА И ВЕРОЯТНОСТЬ ЦЕНЫ
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s14, 15, "Алгоритм работы, ограничитель ввода и вероятность цены", "Алгоритм"
    )
    add_picture_fit(
        s14,
        FIG_DIR / "flowchart_algorithm.png",
        left=0.45,
        top=0.95,
        max_w=6.80,
        max_h=6.05,
        frame=True,
    )

    add_card(
        s14,
        left=7.45,
        top=0.95,
        width=5.43,
        height=1.96,
        title="1. Ограничитель ввода и сброс (Reset)",
        lines=[
            ("Жёсткий контроль границ: ", "мощность 48–288 л.с., объём 61–326 куб. дюймов, масса 1 488–4 066 фунтов, расход 13–54 миль/галлон (MPG)."),
            ("Защита от ошибок: ", "некорректные значения блокируются до расчёта; кнопка Reset возвращает базовые параметры."),
        ],
        bg_color=CARD_BG,
        accent_color=TEAL,
        title_size=13.0,
        body_size=11.0,
    )
    add_card(
        s14,
        left=7.45,
        top=3.06,
        width=5.43,
        height=1.82,
        title="2. Вероятность цены (предмет оценки)",
        lines=[
            ("Предмет оценки: ", "вероятность попадания реальной рыночной цены автомобиля в доверительный коридор ±15% от прогноза модели."),
            ("Методика: ", "вычисляется по стандартному отклонению ошибок модели на тесте (σ) через нормальное распределение."),
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=13.0,
        body_size=11.0,
    )
    add_card(
        s14,
        left=7.45,
        top=5.02,
        width=5.43,
        height=1.98,
        title="3. Значения и диапазон (ограничитель 5%–99%)",
        lines=[
            ("Диапазон значений: ", "ограничен от 5% до 99% — исключены нереалистичные оценки 0% и 100%."),
            ("Шкала надёжности: ", "80–99% — высокая (типовое авто); 60–79% — средняя; 5–59% — низкая (редкая/экстремальная комплектация)."),
        ],
        bg_color=ROSE_BG,
        accent_color=BURGUNDY,
        title_size=13.0,
        body_size=11.0,
    )

    # =========================================================================
    # СЛАЙД 15: ВЕБ-ПРИЛОЖЕНИЕ (STREAMLIT) — ПРОГНОЗИРОВАНИЕ И ВВОД ДАННЫХ
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s15, 16, "Веб-приложение (Streamlit): ввод данных и расчёт цены", "Веб-интерфейс"
    )
    add_picture_fit(
        s15,
        FIG_DIR / "web_predict.png",
        left=0.45,
        top=0.95,
        max_w=8.75,
        max_h=6.05,
        frame=True,
    )

    web_callouts = [
        ("Выбор модели v2.2", "В списке сразу указаны версия и точность в скобках: например, «Случайный лес v2.2 (R² = 0,96; ошибка 9,1%)».", TEAL, MINT_BG),
        ("Синхронный ввод + ограничитель", "Слайдер и числовое поле синхронизированы; ввод значений вне допустимых границ заблокирован.", GRAPHITE, CARD_BG),
        ("Сброс параметров (Reset)", "Отдельная кнопка мгновенно возвращает все ползунки и списки к эталонному автомобилю.", BURGUNDY, ROSE_BG),
        ("Итог в рублях и ±15%", "Крупно показаны прогноз в ₽, вероятность попадания в ±15% (5%–99%) и таблица всех 4 моделей.", TEAL, CARD_BG),
    ]
    for i, (wt, wb, wacc, wbg) in enumerate(web_callouts):
        add_card(
            s15,
            left=9.38,
            top=0.95 + i * 1.54,
            width=3.50,
            height=1.42,
            title=wt,
            lines=[wb],
            bg_color=wbg,
            accent_color=wacc,
            accent_side="left",
            title_size=12.0,
            body_size=10.5,
            bullet_prefix="",
        )

    # =========================================================================
    # СЛАЙД 16: ВЕБ-ПРИЛОЖЕНИЕ — ПРЕСЕТЫ И СПРАВКА О ПРОЕКТЕ
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s16, 17, "Веб-приложение: готовые пресеты и раздел «Справка о проекте»", "Веб-интерфейс"
    )
    add_picture_fit(
        s16,
        FIG_DIR / "web_presets.png",
        left=0.45,
        top=0.95,
        max_w=6.08,
        max_h=3.95,
        frame=True,
    )
    add_picture_fit(
        s16,
        FIG_DIR / "web_help.png",
        left=6.80,
        top=0.95,
        max_w=6.08,
        max_h=3.95,
        frame=True,
    )

    add_card(
        s16,
        left=0.45,
        top=5.06,
        width=6.08,
        height=1.96,
        title="Вкладка «Пресеты» — мгновенный тест на типовых авто",
        lines=[
            "Готовые карточки автомобилей разных классов (бюджетный хэтчбек, семейный седан, турбо-универсал, премиум-спорткар).",
            "В один клик загружаются все параметры, рассчитывается цена в рублях, коридор ±15% и вероятность попадания.",
        ],
        bg_color=MINT_BG,
        accent_color=TEAL,
        title_size=12.8,
        body_size=11.0,
    )
    add_card(
        s16,
        left=6.80,
        top=5.06,
        width=6.08,
        height=1.96,
        title="Вкладка «Справка о проекте» — руководство пользователя",
        lines=[
            "Пошаговая инструкция работы с приложением и полная таблица всех характеристик с их ограничителями.",
            "Подробно объяснены методика расчёта вероятности цены (±15%, диапазон 5%–99%) и реестр версий моделей v2.2.",
        ],
        bg_color=CARD_BG,
        accent_color=GRAPHITE,
        title_size=12.8,
        body_size=11.0,
    )

    # =========================================================================
    # СЛАЙД 17: РАЗРАБОТАННЫЙ TELEGRAM-БОТ (@testcursomsskm_bot) И QR-КОД
    # =========================================================================
    s17 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s17, 18, "Разработанный Telegram-бот (@testcursomsskm_bot) и QR-код", "Telegram-бот"
    )
    # Два крупных вертикальных скриншота диалогов
    add_picture_fit(
        s17,
        FIG_DIR / "bot_predict_dialog.png",
        left=0.45,
        top=0.95,
        max_w=3.70,
        max_h=5.68,
        frame=True,
    )
    add_textbox(
        s17,
        0.45,
        6.68,
        3.70,
        0.34,
        text="Пошаговый ввод параметров и прогноз в ₽",
        font_size=10.5,
        bold=True,
        color=SLATE,
        align=PP_ALIGN.CENTER,
    )

    add_picture_fit(
        s17,
        FIG_DIR / "bot_presets_help.png",
        left=4.32,
        top=0.95,
        max_w=3.20,
        max_h=5.68,
        frame=True,
    )
    add_textbox(
        s17,
        4.32,
        6.68,
        3.20,
        0.34,
        text="Пресеты и справка в Telegram",
        font_size=10.5,
        bold=True,
        color=SLATE,
        align=PP_ALIGN.CENTER,
    )

    # Правая колонка: QR-код + возможности бота
    add_rect(s17, 7.72, 0.95, 5.16, 3.22, fill_color=MINT_BG, line_color=TEAL, line_pt=1.2, rounded=True)
    add_picture_fit(
        s17,
        FIG_DIR / "bot_qr_code.png",
        left=7.88,
        top=1.08,
        max_w=2.45,
        max_h=2.96,
        frame=True,
        pad=0.04,
    )
    add_textbox(
        s17,
        10.45,
        1.12,
        2.32,
        0.45,
        text="QR-код для запуска",
        font_size=14,
        bold=True,
        color=TEAL,
    )
    add_textbox(
        s17,
        10.45,
        1.60,
        2.32,
        0.45,
        text="@testcursomsskm_bot",
        font_size=13,
        bold=True,
        color=GRAPHITE,
    )
    add_textbox(
        s17,
        10.45,
        2.10,
        2.32,
        1.90,
        text="Наведите камеру смартфона, чтобы открыть работающего бота и выполнить тестовый расчёт цены автомобиля в рублях прямо на защите.",
        font_size=11.0,
        color=SLATE,
        line_spacing=1.2,
    )

    add_card(
        s17,
        left=7.72,
        top=4.32,
        width=5.16,
        height=2.68,
        title="Функционал Telegram-бота (aiogram 3)",
        lines=[
            ("Пошаговый расчёт: ", "ввод характеристик с теми же ограничителями границ и кнопкой сброса."),
            ("Выбор модели v2.2: ", "переключение всех 4 моделей с отображением точности в скобках."),
            ("Пресеты и справка: ", "быстрые примеры авто и встроенное руководство пользователя."),
            ("Общий лог SQLite: ", "все расчёты из бота сохраняются в единую историю predictions.db."),
        ],
        bg_color=CARD_BG,
        accent_color=GRAPHITE,
        title_size=12.8,
        body_size=10.8,
    )

    # =========================================================================
    # СЛАЙД 18: ЛОГИРОВАНИЕ В SQLITE И МОДУЛЬНОЕ ТЕСТИРОВАНИЕ
    # =========================================================================
    s18 = prs.slides.add_slide(blank_layout)
    add_header_footer(
        s18, 19, "Логирование истории в SQLite и модульное тестирование", "Хранение и тесты"
    )

    # Левая половина: SQLite для логирования + скриншот истории
    add_rect(s18, 0.45, 0.95, 6.10, 0.46, fill_color=TEAL, rounded=True)
    add_textbox(
        s18,
        0.55,
        0.95,
        5.90,
        0.46,
        text="Локальная БД SQLite (predictions.db) — для логирования истории расчётов",
        font_size=11.8,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )

    db_rows = [
        ["id, user_id, timestamp", "Номер записи, клиент (веб / бот) и дата расчёта"],
        ["model_name", "Название и версия модели v2.2"],
        ["predicted_price_rub", "Итоговая прогнозируемая цена (руб.)"],
        ["brand, carbody", "Марка автомобиля и тип кузова"],
        ["horsepower, enginesize, curbweight", "Мощность (л.с.), объём (куб. дюймы), масса (фунты)"],
        ["features_json", "Полный JSON-снимок введённых характеристик"],
    ]
    add_styled_table(
        s18,
        left=0.45,
        top=1.50,
        width=6.10,
        height=2.36,
        headers=["Поля журнала predictions", "Что логируется при каждом расчёте"],
        rows=db_rows,
        col_widths=[2.55, 3.55],
        font_size=9.5,
        header_size=10.0,
        header_bg=GRAPHITE,
    )

    add_picture_fit(
        s18,
        FIG_DIR / "web_history.png",
        left=0.45,
        top=3.98,
        max_w=6.10,
        max_h=3.02,
        frame=True,
    )

    # Правая половина: 35 автотестов pytest
    add_rect(s18, 6.80, 0.95, 6.08, 0.46, fill_color=MINT_BG, line_color=TEAL, line_pt=1.2, rounded=True)
    add_textbox(
        s18,
        6.90,
        0.95,
        5.88,
        0.46,
        text="Модульное тестирование (pytest): 35 автотестов — 100% PASSED",
        font_size=12.0,
        bold=True,
        color=TEAL,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )

    test_rows = [
        ["test_preprocessing.py", "5", "Очистка марок, 2 признака, ограничители ввода"],
        ["test_models.py", "8", "4 модели v2.2, метрики, .joblib и вероятность ±15%"],
        ["test_analytics.py", "5", "Корреляции и многомерные OLAP-срезы"],
        ["test_db.py", "3", "Создание SQLite, запись и чтение лога расчётов"],
        ["test_presets_and_service.py", "6", "Пресеты, единый сервис расчёта и кнопка Reset"],
        ["test_web_and_bot.py", "8", "Сценарии веб-приложения и команд Telegram-бота"],
        ["ИТОГО (6 модулей)", "35", "Все 35 тестов пройдены успешно (0 ошибок)"],
    ]
    add_styled_table(
        s18,
        left=6.80,
        top=1.50,
        width=6.08,
        height=3.40,
        headers=["Модуль тестов", "Кол-во", "Что проверяется"],
        rows=test_rows,
        col_widths=[2.15, 0.72, 3.21],
        font_size=9.7,
        header_size=10.0,
        highlight_rows={6: MINT_BG},
        bold_rows={6},
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
    )

    add_card(
        s18,
        left=6.80,
        top=5.06,
        width=6.08,
        height=1.94,
        title="Практический результат логирования и тестов",
        lines=[
            ("Единый журнал SQLite: ", "веб-приложение и Telegram-бот пишут историю прогнозов в один файл predictions.db без настройки внешнего сервера."),
            ("Надёжность комплекса: ", "35 автотестов гарантируют безотказную работу ограничителей ввода, расчёта вероятности (5%–99%) и всех моделей v2.2."),
        ],
        bg_color=CARD_BG,
        accent_color=TEAL,
        title_size=12.5,
        body_size=10.8,
    )

    # =========================================================================
    # СЛАЙД 19: ЗАКЛЮЧЕНИЕ И ОСНОВНЫЕ РЕЗУЛЬТАТЫ (ТЁМНЫЙ ФИНАЛЬНЫЙ СЛАЙД)
    # =========================================================================
    s19 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s19, GRAPHITE)
    add_rect(s19, 0.0, 0.0, 0.24, SLIDE_H, fill_color=TEAL)
    add_rect(s19, 0.24, 0.0, 0.06, SLIDE_H, fill_color=BURGUNDY)

    add_textbox(
        s19,
        0.65,
        0.32,
        12.00,
        0.60,
        text="Заключение и основные результаты работы",
        font_size=26,
        bold=True,
        color=WHITE,
        valign=MSO_ANCHOR.MIDDLE,
    )
    add_rect(s19, 0.65, 0.96, 12.20, 0.04, fill_color=TEAL)

    conclusions = [
        (
            "1. Подготовлены и изучены данные: ",
            "205 авто и 26 столбцов очищены (6 опечаток марок), цены переведены в рубли (× 93,5), выполнен анализ корреляций и OLAP-срезов.",
        ),
        (
            "2. Проведена проверка в Loginom 7.4.2: ",
            "сценарий из 9 узлов (70/30) подтвердил сопоставимость линейной регрессии (R² = 0,881) и двухслойного перцептрона (R² = 0,854) с Python.",
        ),
        (
            "3. Обучены 4 версионированные модели v2.2: ",
            f"победитель — Случайный лес (Random Forest v2.2) с R² = {fmt_ru(rf['test']['r2'], 3)}, ошибкой {fmt_ru(rf_mae_k, 1)} тыс. руб. ({fmt_ru(rf['test']['mape'], 2)}%) и 85,4% попаданий в ±15%.",
        ),
        (
            "4. Реализована защита ввода и оценка надёжности: ",
            "строгие ограничители параметров, кнопка Reset и расчёт вероятности цены в коридоре ±15% (диапазон 5%–99%).",
        ),
        (
            "5. Разработаны веб-приложение и Telegram-бот: ",
            "интерфейс Streamlit (прогноз, пресеты, Справка, история) и бот @testcursomsskm_bot с общим логированием в SQLite.",
        ),
        (
            "6. Подтверждена стабильность кода: ",
            "созданы и успешно пройдены 35 модульных автотестов (pytest) по всем 6 компонентам программного комплекса.",
        ),
    ]
    for idx, (lead, body) in enumerate(conclusions):
        y = 1.18 + idx * 0.87
        add_rect(
            s19,
            0.65,
            y,
            8.35,
            0.77,
            fill_color=GRAPHITE_CARD,
            line_color=TEAL if idx % 2 == 0 else SLATE,
            line_pt=0.8,
            rounded=True,
        )
        add_rect(s19, 0.65, y + 0.06, 0.08, 0.65, fill_color=TEAL if idx != 1 else BURGUNDY)
        tb = add_textbox(s19, 0.85, y + 0.04, 8.05, 0.69, valign=MSO_ANCHOR.MIDDLE)
        add_paragraphs(
            tb.text_frame,
            [(lead, body)],
            font_size=12.0,
            color=WHITE,
            bullet_prefix="",
            space_after=0,
            bold_color=TEAL_LIGHT,
        )

    # Белая карточка с QR-кодом бота справа
    add_rect(s19, 9.28, 1.18, 3.55, 5.14, fill_color=WHITE, line_color=TEAL, line_pt=1.5, rounded=True)
    add_rect(s19, 9.28, 1.18, 3.55, 0.48, fill_color=TEAL)
    add_textbox(
        s19,
        9.28,
        1.18,
        3.55,
        0.48,
        text="ДЕМОНСТРАЦИЯ БОТА",
        font_size=12,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
    )
    add_picture_fit(
        s19,
        FIG_DIR / "bot_qr_code.png",
        left=9.48,
        top=1.78,
        max_w=3.15,
        max_h=3.45,
        frame=False,
    )
    add_textbox(
        s19,
        9.40,
        5.32,
        3.31,
        0.40,
        text="@testcursomsskm_bot",
        font_size=14,
        bold=True,
        color=TEAL,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        s19,
        9.40,
        5.72,
        3.31,
        0.52,
        text="Наведите камеру смартфона\nдля проверки расчёта цены",
        font_size=10.5,
        color=SLATE,
        align=PP_ALIGN.CENTER,
    )

    # Нижняя финальная полоса
    add_rect(s19, 0.65, 6.52, 12.18, 0.68, fill_color=GRAPHITE_DARK, line_color=TEAL, line_pt=1.0, rounded=True)
    add_textbox(
        s19,
        0.90,
        6.56,
        7.80,
        0.60,
        text="Спасибо за внимание! Готов ответить на ваши вопросы.",
        font_size=18,
        bold=True,
        color=WHITE,
        valign=MSO_ANCHOR.MIDDLE,
    )
    add_textbox(
        s19,
        8.80,
        6.56,
        3.80,
        0.60,
        text="Груздев А.А. • ТвГТУ • 2026 г.",
        font_size=12.5,
        bold=True,
        color=TEAL_LIGHT,
        align=PP_ALIGN.RIGHT,
        valign=MSO_ANCHOR.MIDDLE,
    )

    prs.save(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    out = build_presentation()
    print(f"Презентация успешно создана: {out}")
