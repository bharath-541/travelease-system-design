from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "diagrams" / "booking_sequence.png"

WIDTH = 1750
HEIGHT = 1350
BG = "#fbfaf6"
INK = "#17201e"
MUTED = "#65706b"
TEAL = "#063f3b"
CORAL = "#e65b45"
BRASS = "#b58a3a"
LINE = "#cfc7b9"


def font(size, bold=False):
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


TITLE = font(40, True)
LABEL = font(18, True)
BODY = font(16)
SMALL = font(14)


def draw_arrow(draw, y, start_x, end_x, label, color=TEAL, dashed=False):
    if dashed:
        segment = 14
        x = min(start_x, end_x)
        limit = max(start_x, end_x)
        while x < limit:
            draw.line((x, y, min(x + segment, limit), y), fill=color, width=3)
            x += segment * 2
    else:
        draw.line((start_x, y, end_x, y), fill=color, width=3)
    direction = 1 if end_x > start_x else -1
    draw.polygon(
        [
            (end_x, y),
            (end_x - direction * 12, y - 7),
            (end_x - direction * 12, y + 7),
        ],
        fill=color,
    )
    bbox = draw.textbbox((0, 0), label, font=SMALL)
    label_width = bbox[2] - bbox[0]
    draw.rectangle(
        (
            (start_x + end_x - label_width) / 2 - 7,
            y - 25,
            (start_x + end_x + label_width) / 2 + 7,
            y - 5,
        ),
        fill=BG,
    )
    draw.text(
        ((start_x + end_x - label_width) / 2, y - 24),
        label,
        fill=INK,
        font=SMALL,
    )


def main():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((60, 35), "TravelEase Booking Sequence", fill=INK, font=TITLE)
    draw.text(
        (60, 88),
        "Idempotent payment, provider revalidation, and Saga compensation",
        fill=MUTED,
        font=BODY,
    )

    actors = [
        ("User", 105),
        ("Web App", 340),
        ("Search", 575),
        ("Booking", 825),
        ("Database", 1075),
        ("Payment", 1325),
        ("Provider", 1570),
    ]
    top = 155
    bottom = 1265
    for name, x in actors:
        draw.rounded_rectangle(
            (x - 78, top, x + 78, top + 58),
            radius=10,
            fill=TEAL if name not in {"Payment", "Provider"} else CORAL,
        )
        bbox = draw.textbbox((0, 0), name, font=LABEL)
        draw.text(
            (x - (bbox[2] - bbox[0]) / 2, top + 18),
            name,
            fill="#ffffff",
            font=LABEL,
        )
        draw.line((x, top + 58, x, bottom), fill=LINE, width=2)

    events = [
        (265, 105, 340, "Search route and date", TEAL, False),
        (340, 340, 575, "Query indexed inventory", TEAL, False),
        (415, 575, 340, "Ranked results", TEAL, True),
        (490, 105, 340, "Select listing", TEAL, False),
        (565, 340, 825, "Create idempotent hold", CORAL, False),
        (640, 825, 1075, "Atomic check and decrement", CORAL, False),
        (715, 1075, 825, "HELD with expiry", CORAL, True),
        (790, 340, 1325, "Authorize payment", TEAL, False),
        (865, 1325, 825, "Approved", TEAL, True),
        (940, 825, 1570, "Revalidate and reserve", BRASS, False),
        (1015, 1570, 825, "Provider reference", BRASS, True),
        (1090, 825, 1075, "Mark CONFIRMED", TEAL, False),
        (1165, 825, 340, "Return confirmation", TEAL, True),
    ]
    for y, start_x, end_x, label, color, dashed in events:
        draw_arrow(draw, y, start_x, end_x, label, color, dashed)

    draw.rounded_rectangle(
        (745, 1220, 1650, 1315),
        radius=12,
        outline=CORAL,
        width=3,
        fill="#fff3ed",
    )
    draw.text(
        (765, 1240),
        "Failure path:",
        fill=CORAL,
        font=LABEL,
    )
    draw.multiline_text(
        (895, 1238),
        "payment decline -> release hold | provider timeout/rejection -> release inventory + compensating refund",
        fill=INK,
        font=SMALL,
        spacing=4,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
