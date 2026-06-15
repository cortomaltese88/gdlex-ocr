"""Processing profiles for GD LEX OCR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TableMode = Literal["fast", "accurate"]


@dataclass(frozen=True)
class ProcessingProfile:
    name: str
    block_size: int
    num_threads: int
    page_batch_size: int
    enable_ocr: bool
    table_mode: TableMode
    enrich_picture: bool
    enrich_chart: bool
    structure_markdown: bool

    def summary(self) -> str:
        pic = "sì" if self.enrich_picture else "no"
        chart = "sì" if self.enrich_chart else "no"
        structure = "sì" if self.structure_markdown else "no"
        return (
            f"Blocco {self.block_size} pag · "
            f"{self.num_threads} thread · "
            f"batch {self.page_batch_size} · "
            f"tabelle {self.table_mode} · "
            f"immagini {pic} · grafici {chart} · struttura {structure}"
        )


PROFILES: dict[str, ProcessingProfile] = {
    "Veloce": ProcessingProfile(
        name="Veloce",
        block_size=25,
        num_threads=12,
        page_batch_size=8,
        enable_ocr=True,
        table_mode="fast",
        enrich_picture=False,
        enrich_chart=False,
        structure_markdown=False,
    ),
    "Bilanciato": ProcessingProfile(
        name="Bilanciato",
        block_size=15,
        num_threads=10,
        page_batch_size=6,
        enable_ocr=True,
        table_mode="fast",
        enrich_picture=False,
        enrich_chart=False,
        structure_markdown=True,
    ),
    "Accurato testo": ProcessingProfile(
        name="Accurato testo",
        block_size=10,
        num_threads=6,
        page_batch_size=4,
        enable_ocr=True,
        table_mode="accurate",
        enrich_picture=False,
        enrich_chart=False,
        structure_markdown=True,
    ),
    "PDF già ricercabile": ProcessingProfile(
        name="PDF già ricercabile",
        block_size=15,
        num_threads=10,
        page_batch_size=6,
        enable_ocr=False,
        table_mode="accurate",
        enrich_picture=False,
        enrich_chart=False,
        structure_markdown=True,
    ),
    "Accurato": ProcessingProfile(
        name="Accurato",
        block_size=10,
        num_threads=6,
        page_batch_size=4,
        enable_ocr=True,
        table_mode="accurate",
        enrich_picture=True,
        enrich_chart=True,
        structure_markdown=False,
    ),
}

DEFAULT_PROFILE = "Bilanciato"
PROFILE_NAMES = list(PROFILES.keys())
