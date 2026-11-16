"""Компонент поля со слайдером и синхронизированным текстовым вводом."""

import customtkinter as ctk


def create_slider_field(
    parent: ctk.CTkBaseClass,
    app,
    name: str,
    label: str,
    min_v: float,
    max_v: float,
    def_v: float,
    step: float,
    unit: str = "",
) -> None:
    """Создает строку со слайдером, подписью и двусторонней синхронизацией."""
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.pack(fill="x", padx=10, pady=2)

    header = ctk.CTkFrame(box, fg_color="transparent")
    header.pack(fill="x")
    ctk.CTkLabel(header, text=label, font=ctk.CTkFont(size=11)).pack(side="left")

    var = ctk.DoubleVar(value=def_v)
    app.slider_vars[name] = var

    val_frame = ctk.CTkFrame(header, fg_color="transparent")
    val_frame.pack(side="right")

    entry = ctk.CTkEntry(val_frame, width=65, height=24, font=ctk.CTkFont(size=11, weight="bold"), justify="center")
    entry.insert(0, f"{def_v:.0f}")
    entry.pack(side="left")
    app.entry_widgets[name] = entry

    if unit:
        ctk.CTkLabel(val_frame, text=f" {unit}", font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(side="left")

    def _on_move(val: float):
        entry.delete(0, "end")
        entry.insert(0, f"{round(val):.0f}")

    def _on_submit(_event=None):
        try:
            val = float(entry.get().replace(",", "."))
            val = max(min_v, min(max_v, val))
            var.set(val)
            entry.delete(0, "end")
            entry.insert(0, f"{round(val):.0f}")
        except ValueError:
            entry.delete(0, "end")
            entry.insert(0, f"{round(var.get()):.0f}")

    steps = max(1, int((max_v - min_v) / step))
    slider = ctk.CTkSlider(box, from_=min_v, to=max_v, number_of_steps=steps, variable=var,
                           button_color="#38bdf8", button_hover_color="#0284c7", progress_color="#2563eb",
                           command=_on_move)
    slider.pack(fill="x", pady=(2, 4))
    entry.bind("<Return>", _on_submit)
    entry.bind("<FocusOut>", _on_submit)
