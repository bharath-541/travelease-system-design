from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOC_OUTPUT = ROOT / "docs" / "diagrams" / "architecture.png"
APP_OUTPUT = ROOT / "app" / "static" / "img" / "architecture.png"

WIDTH = 1900
HEIGHT = 1120
BG = "#fbfaf6"
INK = "#17201e"
MUTED = "#65706b"
TEAL = "#063f3b"
TEAL_LIGHT = "#0d5c55"
CORAL = "#e65b45"
BRASS = "#b58a3a"
LINE = "#cfc7b9"


def load_font(size, bold=False):
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


TITLE = load_font(45, bold=True)
SECTION = load_font(23, bold=True)
LABEL = load_font(20, bold=True)
SMALL = load_font(16)


def box(draw, xy, title, subtitle, fill, text_color="#ffffff"):
    draw.rounded_rectangle(xy, radius=14, fill=fill, outline=LINE, width=2)
    x1, y1, x2, y2 = xy
    draw.text((x1 + 18, y1 + 15), title, font=LABEL, fill=text_color)
    draw.multiline_text(
        (x1 + 18, y1 + 47),
        subtitle,
        font=SMALL,
        fill=text_color,
        spacing=4,
    )
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def arrow(draw, start, end, color=TEAL_LIGHT, width=4):
    draw.line([start, end], fill=color, width=width)
    x2, y2 = end
    x1, y1 = start
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - 14 * direction, y2 - 8), (x2 - 14 * direction, y2 + 8)]
    else:
        direction = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 8, y2 - 14 * direction), (x2 + 8, y2 - 14 * direction)]
    draw.polygon(points, fill=color)


def section(draw, xy, title):
    draw.rounded_rectangle(xy, radius=18, fill="#f4f0e6", outline=LINE, width=2)
    draw.text((xy[0] + 18, xy[1] + 12), title, font=SECTION, fill=INK)


def main():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 35), "TravelEase Distributed Architecture", font=TITLE, fill=INK)
    draw.text(
        (70, 93),
        "Low-latency search, transactional booking, event-driven synchronization, and failure compensation",
        font=SMALL,
        fill=MUTED,
    )

    section(draw, (55, 145, 345, 1020), "Clients and Edge")
    web = box(draw, (85, 220, 315, 330), "Web Application", "Flask / responsive UI", TEAL)
    mobile = box(draw, (85, 375, 315, 485), "Mobile Apps", "iOS and Android clients", TEAL)
    cdn = box(draw, (85, 565, 315, 675), "CDN + WAF", "TLS, rate limiting,\nstatic content", TEAL_LIGHT)
    api = box(draw, (85, 760, 315, 870), "API Gateway", "Auth, routing,\nrequest tracing", CORAL)
    arrow(draw, (web[0], 330), (cdn[0], 565))
    arrow(draw, (mobile[0], 485), (cdn[0], 565))
    arrow(draw, (cdn[0], 675), (api[0], 760))

    section(draw, (380, 145, 1070, 1020), "Domain Services")
    search = box(draw, (420, 220, 705, 340), "Search Aggregator", "Fan-out, filters, ranking,\ncache-aware responses", TEAL)
    price = box(draw, (745, 220, 1030, 340), "Pricing Service", "Demand multiplier,\nprovider revalidation", BRASS)
    booking = box(draw, (420, 420, 705, 550), "Booking Manager", "Inventory hold, state machine,\nSaga coordination", CORAL)
    payment = box(draw, (745, 420, 1030, 550), "Payment Service", "Idempotent authorization,\nrefund workflow", "#875b75")
    provider = box(draw, (420, 650, 705, 780), "Provider Integration", "Circuit breaker, retries,\nadapters, DLQ", "#426b78")
    recommendation = box(draw, (745, 650, 1030, 780), "Recommendation", "Profiles, popularity,\nranking features", "#56734e")
    notify = box(draw, (580, 850, 870, 965), "Notification Service", "Email, SMS, push,\nconfirmation templates", TEAL_LIGHT)
    arrow(draw, (345, api[1]), (420, search[1]))
    arrow(draw, (345, api[1]), (420, booking[1]))
    arrow(draw, (705, search[1]), (745, price[1]))
    arrow(draw, (705, booking[1]), (745, payment[1]))
    arrow(draw, (562, 550), (562, 650))
    arrow(draw, (887, 340), (705, 475))
    arrow(draw, (705, 715), (745, 715))
    arrow(draw, (562, 780), (675, 850))
    arrow(draw, (887, 780), (775, 850))

    section(draw, (1105, 145, 1515, 1020), "Data and Events")
    redis = box(draw, (1145, 215, 1475, 320), "Redis Cache", "Search, sessions, rate limits", TEAL)
    opensearch = box(draw, (1145, 360, 1475, 465), "OpenSearch", "Listings, facets, geo queries", "#426b78")
    postgres = box(draw, (1145, 505, 1475, 620), "PostgreSQL", "Bookings, inventory,\npayments, outbox", CORAL)
    kafka = box(draw, (1145, 665, 1475, 780), "Kafka / Event Bus", "PriceChanged, BookingConfirmed,\nBookingFailed", BRASS)
    lake = box(draw, (1145, 825, 1475, 930), "NoSQL + Data Lake", "Profiles, analytics, ML features", "#56734e")
    arrow(draw, (1030, search[1]), (1145, redis[1]))
    arrow(draw, (1030, search[1] + 35), (1145, opensearch[1]))
    arrow(draw, (1030, booking[1]), (1145, postgres[1]))
    arrow(draw, (1030, booking[1] + 45), (1145, kafka[1]))
    arrow(draw, (1030, recommendation[1]), (1145, lake[1]))

    section(draw, (1550, 145, 1845, 1020), "External and Reliability")
    suppliers = box(draw, (1580, 220, 1815, 355), "Travel Providers", "Airlines, hotels,\nrail and bus APIs", TEAL)
    gateways = box(draw, (1580, 410, 1815, 525), "Payment Gateways", "Primary + fallback", "#875b75")
    channels = box(draw, (1580, 580, 1815, 695), "Message Channels", "Email, SMS, push", "#56734e")
    observe = box(draw, (1580, 760, 1815, 900), "Reliability Plane", "Metrics, logs, traces,\nconfig, discovery, DLQ", BRASS)
    arrow(draw, (705, provider[1]), (1580, suppliers[1]))
    arrow(draw, (1030, payment[1]), (1580, gateways[1]))
    arrow(draw, (870, notify[1]), (1580, channels[1]))
    arrow(draw, (1515, observe[1]), (1580, observe[1]), color=CORAL)

    draw.text(
        (70, 1050),
        "Consistency boundary: PostgreSQL transaction for inventory and booking state. Synchronization boundary: event bus and idempotent consumers.",
        font=SMALL,
        fill=MUTED,
    )

    DOC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    APP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(DOC_OUTPUT)
    image.save(APP_OUTPUT)
    print(f"Generated {DOC_OUTPUT}")
    print(f"Generated {APP_OUTPUT}")


if __name__ == "__main__":
    main()
