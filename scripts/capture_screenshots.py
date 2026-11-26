"""Захват реальных скриншотов веб-приложения Streamlit и диалогов Telegram-бота через Playwright."""

import os
import sys
import time
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from src.config import CAR_PRESETS, MODEL_NAMES, APP_NAME, TELEGRAM_BOT_HANDLE
from src.models.service import ModelService
from src.bot.formatting import format_prediction, format_presets_overview
from src.bot.keyboards import main_menu_kb, models_kb, presets_kb

FIGURES_DIR = ROOT / "reports" / "figures"
SCREENSHOTS_DIR = ROOT / "screenshots"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def save_both(src_path: Path, name: str) -> None:
    dst1 = SCREENSHOTS_DIR / name
    dst2 = FIGURES_DIR / name
    if src_path != dst1:
        shutil.copy2(src_path, dst1)
    shutil.copy2(dst1, dst2)


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def launch_browser(pw):
    for ch in ("msedge", "chrome", None):
        try:
            kwargs = {"headless": True}
            if ch:
                kwargs["channel"] = ch
            return pw.chromium.launch(**kwargs)
        except Exception:
            continue
    raise RuntimeError("No Chromium/Edge/Chrome browser available")


def capture_web_ui(pw) -> None:
    port = 8511
    url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "src" / "web" / "app.py"),
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.address", "127.0.0.1",
            "--browser.gatherUsageStats", "false",
            "--theme.base", "light",
            "--theme.primaryColor", "#0F766E",
            "--theme.backgroundColor", "#FFFFFF",
            "--theme.secondaryBackgroundColor", "#F1F5F9",
            "--theme.textColor", "#1E293B",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(ROOT),
    )
    try:
        if not wait_for_server(url, timeout=35.0):
            raise RuntimeError("Streamlit server did not start in time")

        browser = launch_browser(pw)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = context.new_page()

        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("h2, h1", timeout=20000)
        time.sleep(2.5)

        def snap(label: str, filename: str, scroll_y: int = 0) -> None:
            if label:
                radio = page.locator("section[data-testid='stSidebar']").get_by_text(label, exact=True).first
                radio.click()
                time.sleep(2.5)
            if scroll_y:
                page.evaluate(f"window.scrollTo(0, {scroll_y})")
                time.sleep(0.4)
            out = SCREENSHOTS_DIR / filename
            page.screenshot(path=str(out), full_page=False)
            save_both(out, filename)
            print(f"Captured {filename}")

        snap(None, "web_predict.png")
        snap("Пресеты авто", "web_presets.png")
        snap("Аналитика (OLAP)", "web_olap.png")
        snap("История (SQLite)", "web_history.png")
        snap("Справка о проекте", "web_help.png")

        browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def _tg_html_page(title: str, messages_html: str, reply_kb_rows: list[list[str]]) -> str:
    kb_html = ""
    if reply_kb_rows:
        rows_str = ""
        for row in reply_kb_rows:
            btns = "".join(f'<div class="rbtn">{b}</div>' for b in row)
            rows_str += f'<div class="rrow">{btns}</div>'
        kb_html = f'<div class="reply-kb">{rows_str}</div>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }}
  body {{ background: #E2E8F0; display: flex; justify-content: center; align-items: center; padding: 18px; }}
  .phone {{
    width: 560px; background: #F1F5F9; border-radius: 22px; overflow: hidden;
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.22); border: 2px solid #CBD5E1;
  }}
  .header {{
    background: #1E293B; color: #FFFFFF; padding: 14px 20px;
    display: flex; align-items: center; gap: 14px;
  }}
  .avatar {{
    width: 44px; height: 44px; border-radius: 50%; background: #0F766E;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 18px; color: #FFFFFF; flex-shrink: 0;
  }}
  .h-title {{ font-size: 17px; font-weight: 700; }}
  .h-sub {{ font-size: 12.5px; color: #94A3B8; margin-top: 2px; }}
  .chat {{
    padding: 16px 18px; display: flex; flex-direction: column; gap: 10px;
    background: linear-gradient(180deg, #F8FAFC 0%, #EEF2F6 100%);
    min-height: 540px;
  }}
  .msg {{
    max-width: 88%; padding: 11px 14px; border-radius: 14px;
    font-size: 13.5px; line-height: 1.44; white-space: pre-line;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  }}
  .msg.bot {{
    align-self: flex-start; background: #FFFFFF; color: #1E293B;
    border-bottom-left-radius: 4px; border: 1px solid #E2E8F0;
  }}
  .msg.user {{
    align-self: flex-end; background: #0F766E; color: #FFFFFF;
    border-bottom-right-radius: 4px;
  }}
  .ts {{ font-size: 10.5px; opacity: 0.65; text-align: right; margin-top: 4px; }}
  .inline-kb {{ display: flex; flex-direction: column; gap: 5px; margin-top: 6px; max-width: 88%; }}
  .ibtn {{
    background: #F1F5F9; border: 1px solid #CBD5E1; color: #0F766E;
    font-weight: 600; font-size: 12.5px; text-align: center; padding: 8px 10px;
    border-radius: 9px;
  }}
  .ibtn.active {{ background: #CCFBF1; border-color: #0F766E; color: #115E59; }}
  .reply-kb {{
    background: #E2E8F0; padding: 10px 12px; display: flex; flex-direction: column; gap: 7px;
    border-top: 1px solid #CBD5E1;
  }}
  .rrow {{ display: flex; gap: 7px; }}
  .rbtn {{
    flex: 1; background: #FFFFFF; color: #1E293B; font-weight: 600; font-size: 13px;
    text-align: center; padding: 10px 8px; border-radius: 8px;
    border: 1px solid #CBD5E1; box-shadow: 0 1px 1px rgba(0,0,0,0.04);
  }}
</style>
</head>
<body>
  <div class="phone">
    <div class="header">
      <div class="avatar">CP</div>
      <div>
        <div class="h-title">{title}</div>
        <div class="h-sub">{TELEGRAM_BOT_HANDLE} · бот · онлайн</div>
      </div>
    </div>
    <div class="chat">{messages_html}</div>
    {kb_html}
  </div>
</body>
</html>"""


def capture_bot_screens(pw) -> None:
    service = ModelService()
    metrics = service.get_metrics_summary()
    kb_rows = [[b.text for b in row] for row in main_menu_kb().keyboard]

    # Screen 1: Step-by-step prediction + model choice with v2.2 & quality + result card
    porsche_data = CAR_PRESETS["Спорткар / Купе (Porsche)"]
    res_porsche = service.predict(porsche_data, model_selection=MODEL_NAMES[0])
    card_html = format_prediction(res_porsche, porsche_data, title="Расчёт: Porsche (Хардтоп)").replace("\n", "<br/>")
    model_btns = [btn.text for row in models_kb(metrics).inline_keyboard for btn in row]
    models_inline = '<div class="inline-kb">' + "".join(
        f'<div class="ibtn {"active" if i == 0 else ""}">{t}</div>' for i, t in enumerate(model_btns)
    ) + "</div>"

    msgs_1 = f"""
      <div class="msg user">Рассчитать авто<div class="ts">14:32</div></div>
      <div class="msg bot">Шаг 6/6. Выберите модель машинного обучения (в скобках указаны версия и точность на тесте):<div class="ts">14:33</div></div>
      {models_inline}
      <div class="msg bot">{card_html}<div class="ts">14:33</div></div>
    """

    # Screen 2: Presets overview + Help snippet
    presets_html = format_presets_overview(service).replace("\n", "<br/>")
    preset_btns = [btn.text for row in presets_kb().inline_keyboard for btn in row]
    presets_inline = '<div class="inline-kb">' + "".join(
        f'<div class="ibtn">{t}</div>' for t in preset_btns
    ) + "</div>"

    help_text = (
        "<b>Справка о проекте и боте</b><br/>"
        "• <b>Ограничители ввода:</b> мощность 48–288 л.с., объём 61–326 куб. дюймов, масса 1 488–4 066 фунтов.<br/>"
        "• <b>Вероятность цены:</b> шанс попадания рыночной цены в коридор ±15% от прогноза (шкала 5–99%): "
        "80–99% высокая, 60–79% средняя, 5–59% низкая.<br/>"
        "• Все расчёты автоматически логируются в SQLite."
    )
    msgs_2 = f"""
      <div class="msg user">Пресеты авто<div class="ts">14:35</div></div>
      <div class="msg bot">{presets_html}<div class="ts">14:35</div></div>
      {presets_inline}
      <div class="msg user">Справка<div class="ts">14:36</div></div>
      <div class="msg bot">{help_text}<div class="ts">14:36</div></div>
    """

    browser = launch_browser(pw)
    context = browser.new_context(viewport={"width": 640, "height": 960}, device_scale_factor=2)
    page = context.new_page()

    for filename, html in [
        ("bot_predict_dialog.png", _tg_html_page("CarPrice Predictor ML", msgs_1, kb_rows)),
        ("bot_presets_help.png", _tg_html_page("CarPrice Predictor ML", msgs_2, kb_rows)),
    ]:
        page.set_content(html, wait_until="load")
        el = page.locator(".phone")
        out = SCREENSHOTS_DIR / filename
        el.screenshot(path=str(out))
        save_both(out, filename)
        print(f"Captured {filename}")

    browser.close()


def main() -> None:
    with sync_playwright() as pw:
        capture_bot_screens(pw)
        capture_web_ui(pw)
    print("ALL SCREENSHOTS CAPTURED SUCCESSFULLY")


if __name__ == "__main__":
    main()
