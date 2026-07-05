"""python-docx styling constants for the DOCX resume render.

Per TECH_SPEC.md §5: visually consistent with the PDF, not pixel-identical.
Calibri (ATS-safe Latin Modern substitute), native Word bullets, no live
page-count check.
"""

from docx.shared import Inches, Pt

FONT_NAME = "Calibri"
BODY_SIZE = Pt(10.5)
NAME_SIZE = Pt(11)
HEADING_SIZE = Pt(11)
SMALL_SIZE = Pt(9)

MARGIN = Inches(0.5)
PAGE_WIDTH = Inches(8.5)
USABLE_WIDTH = PAGE_WIDTH - MARGIN - MARGIN  # 7.5in on Letter with 0.5in margins

HEADING_BORDER_COLOR = "000000"
HEADING_BORDER_SIZE_EMU = 6  # eighths of a point, per OOXML <w:bottom w:sz=.../>

# Accent for the header impact line + its hairline rules (mirrors the PDF's
# `accent` color). Visual only — the same metrics also live in the bullets.
ACCENT_COLOR = "7A2E2E"
