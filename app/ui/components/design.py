"""Shared presentation helpers for NiceGUI pages."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nicegui import ui


@contextmanager
def page_container() -> Iterator[ui.column]:
    with ui.column().classes("greenhouse-page w-full gap-6") as container:
        yield container


def page_hero(title: str, subtitle: str, *, icon: str | None = None, meta: str | None = None) -> None:
    with ui.card().classes("greenhouse-hero w-full p-6"):
        with ui.row().classes("w-full items-center gap-4 no-wrap"):
            if icon:
                ui.icon(icon, size="2rem").classes("greenhouse-brand-mark p-3")
            with ui.column().classes("gap-1 flex-1"):
                if meta:
                    ui.label(meta).classes("greenhouse-chip w-fit")
                ui.label(title).classes("text-3xl font-bold leading-tight")
                ui.label(subtitle).classes("text-sm opacity-70 max-w-3xl")


@contextmanager
def section_card(
    title: str | None = None,
    subtitle: str | None = None,
    *,
    icon: str | None = None,
    classes: str = "",
) -> Iterator[ui.card]:
    with ui.card().classes(f"greenhouse-section-card w-full p-5 {classes}".strip()) as card:
        if title or subtitle or icon:
            with ui.row().classes("w-full items-start gap-3"):
                if icon:
                    ui.icon(icon, size="1.35rem").classes("opacity-70 mt-1")
                with ui.column().classes("gap-0.5 flex-1"):
                    if title:
                        ui.label(title).classes("text-lg font-semibold")
                    if subtitle:
                        ui.label(subtitle).classes("text-sm opacity-65")
        yield card


def empty_state(title: str, message: str, *, icon: str = "eco") -> None:
    with ui.column().classes("greenhouse-empty w-full items-center gap-3 p-8"):
        ui.icon(icon, size="3.5rem").classes("opacity-35")
        ui.label(title).classes("text-lg font-semibold opacity-70")
        ui.label(message).classes("text-sm opacity-55 text-center max-w-xl")


def status_chip(label: str, *, icon: str | None = None, color: str | None = None) -> None:
    with ui.row().classes("greenhouse-chip"):
        if icon:
            item = ui.icon(icon, size="0.9rem")
            if color:
                item.style(f"color: {color}")
        ui.label(label)
