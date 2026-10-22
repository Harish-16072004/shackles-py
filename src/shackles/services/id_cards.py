"""ID card composition and A3 PDF generation.

Two responsibilities:
  1. compose_card() — render one card at 300 PPI as a PIL image
  2. build_a3_pdf() — arrange cards 4x4 on A3 pages, return PDF bytes

If `storage/templates/id-card-template.png` exists, it is used as the
background. Otherwise, a clean default card is drawn in code so the
system works without any external assets.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A3
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from shackles.config import settings


# ============================================================
# Card layout constants (pixels at 300 PPI)
# ============================================================

CARD_W_PX = 744
CARD_H_PX = 1004

QR_SIZE_PX = 295
QR_X_PX = (CARD_W_PX - QR_SIZE_PX) // 2
QR_Y_PX = CARD_H_PX - 68 - QR_SIZE_PX

TEXT_Y_PX = 575
TEXT_FONT_SIZE = 44
TEXT_COLOR = "#1a1a2e"


# ============================================================
# A3 layout constants (points)
# ============================================================

A3_W_PT = 841.89
A3_H_PT = 1190.55

CARD_W_PT = (6.3 / 2.54) * 72
CARD_H_PT = (8.5 / 2.54) * 72

COLS = 4
ROWS = 4
CARDS_PER_PAGE = COLS * ROWS

H_GAP_PT = (A3_W_PT - COLS * CARD_W_PT) / (COLS + 1)
V_GAP_PT = (A3_H_PT - ROWS * CARD_H_PT) / (ROWS + 1)


# ============================================================
# Fonts
# ============================================================

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font at the given size, or fall back to PIL default."""
    for name in (
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "Helvetica.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ============================================================
# Template loading
# ============================================================

def _template_path() -> Path:
    return Path(settings.storage_local_root) / "templates" / "id-card-template.png"


def _load_template() -> Image.Image | None:
    """Load the template PNG if present. Returns None otherwise."""
    path = _template_path()
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        return None


# ============================================================
# Default card drawing
# ============================================================

def _draw_default_card() -> Image.Image:
    """Draw a clean default card when no template PNG is available.

    Layout:
      - White background with light border
      - Dark header band with 'SHACKLES SYMPOSIUM'
      - Dark footer band with the year
      - Space in the middle for the ID text and QR (drawn later)
    """
    card = Image.new("RGB", (CARD_W_PX, CARD_H_PX), "white")
    draw = ImageDraw.Draw(card)

    # ---- Header band ----
    header_h = 90
    draw.rectangle([(0, 0), (CARD_W_PX, header_h)], fill="#111827")

    header_font = _load_font(34)
    header_text = "SHACKLES SYMPOSIUM"
    bbox = draw.textbbox((0, 0), header_text, font=header_font)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_W_PX - text_w) // 2, 28),
        header_text,
        fill="white",
        font=header_font,
    )

    # ---- Footer band ----
    footer_h = 70
    footer_y = CARD_H_PX - footer_h
    draw.rectangle([(0, footer_y), (CARD_W_PX, CARD_H_PX)], fill="#111827")

    footer_font = _load_font(24)
    year_text = str(settings.active_year)
    bbox = draw.textbbox((0, 0), year_text, font=footer_font)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_W_PX - text_w) // 2, footer_y + 22),
        year_text,
        fill="white",
        font=footer_font,
    )

    # ---- Subtitle below header ----
    subtitle_font = _load_font(22)
    subtitle_text = "PARTICIPANT ID"
    bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_W_PX - text_w) // 2, header_h + 20),
        subtitle_text,
        fill="#6b7280",
        font=subtitle_font,
    )

    # ---- Border ----
    draw.rectangle(
        [(0, 0), (CARD_W_PX - 1, CARD_H_PX - 1)],
        outline="#e5e7eb",
        width=2,
    )

    return card


# ============================================================
# Card composition
# ============================================================

def compose_card(shackles_id: str, qr_png: bytes | None) -> Image.Image:
    """Compose a single ID card image.

    Uses the template PNG if available, else draws a default card.
    Adds the Shackles ID text and the QR code image.
    """
    template = _load_template()
    if template is not None:
        card = template.resize((CARD_W_PX, CARD_H_PX))
    else:
        card = _draw_default_card()

    draw = ImageDraw.Draw(card)
    font = _load_font(TEXT_FONT_SIZE)

    # ---- Shackles ID text ----
    bbox = draw.textbbox((0, 0), shackles_id, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_W_PX - text_w) // 2, TEXT_Y_PX),
        shackles_id,
        fill=TEXT_COLOR,
        font=font,
    )

    # ---- QR code ----
    if qr_png is not None:
        try:
            qr_img = Image.open(BytesIO(qr_png)).convert("RGB")
            qr_img = qr_img.resize((QR_SIZE_PX, QR_SIZE_PX))
            card.paste(qr_img, (QR_X_PX, QR_Y_PX))
        except Exception:
            # Leave the box blank rather than fail the whole batch
            pass

    return card


# ============================================================
# A3 PDF assembly
# ============================================================

def build_a3_pdf(cards: list[Image.Image], title: str = "ID Cards") -> bytes:
    """Arrange cards on A3 pages (4x4 grid) and return PDF bytes."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A3)
    c.setTitle(f"Shackles Symposium — {title}")
    c.setAuthor("Shackles Symposium")

    for page_start in range(0, len(cards), CARDS_PER_PAGE):
        page_cards = cards[page_start : page_start + CARDS_PER_PAGE]
        for idx, card in enumerate(page_cards):
            col = idx % COLS
            row = idx // COLS

            x = H_GAP_PT + col * (CARD_W_PT + H_GAP_PT)
            y = (
                A3_H_PT
                - V_GAP_PT
                - (row + 1) * CARD_H_PT
                - row * V_GAP_PT
            )

            img_buf = BytesIO()
            card.save(img_buf, format="PNG")
            img_buf.seek(0)

            c.drawImage(
                ImageReader(img_buf),
                x,
                y,
                width=CARD_W_PT,
                height=CARD_H_PT,
            )

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()


def build_a3_pdf_from_cards(
    entries: list[tuple[str, bytes | None]],
    title: str = "ID Cards",
) -> bytes:
    """Convenience wrapper: compose each card from (shackles_id, qr_png)."""
    cards = [compose_card(sid, qr) for sid, qr in entries]
    return build_a3_pdf(cards, title=title)