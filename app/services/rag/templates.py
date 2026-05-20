"""Built-in Ukrainian greenhouse research documents for RAG seeding."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class RAGTemplateDocument:
    title: str
    source_url: str
    content: str
    metadata: dict[str, str]


_TEMPLATE_TITLES = {
    "01_microclimate_control.md": "Мікроклімат теплиці: температура, вологість і VPD",
    "02_tomato_cultivation.md": "Вирощування томатів у теплиці",
    "03_cucumber_cultivation.md": "Вирощування огірків у теплиці",
    "04_soil_moisture_irrigation.md": "Вологість ґрунту та стратегія поливу",
    "05_nutrient_deficiency.md": "Діагностика дефіцитів живлення у тепличних культур",
    "06_pest_disease_management.md": "Шкідники та хвороби в теплиці",
    "07_ventilation_co2.md": "Вентиляція, циркуляція повітря та CO2",
    "08_light_photoperiod.md": "Світло та фотоперіод у теплиці",
    "09_growth_stages.md": "Фази росту тепличних культур і управління умовами",
    "10_sensor_troubleshooting.md": "Діагностика показників датчиків у теплиці",
}


def load_ukrainian_greenhouse_templates() -> list[RAGTemplateDocument]:
    package = "app.services.rag.template_documents"
    documents = []
    for filename, title in _TEMPLATE_TITLES.items():
        content = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
        documents.append(
            RAGTemplateDocument(
                title=title,
                source_url=f"builtin://rag/ukrainian-greenhouse-research/{filename}",
                content=content,
                metadata={"language": "uk", "collection": "ukrainian-greenhouse-research"},
            )
        )
    return documents
