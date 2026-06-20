import json
import sqlite3
from datetime import date, timedelta

from flask import current_app, g


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    travel_type TEXT NOT NULL,
    title TEXT NOT NULL,
    provider TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    duration TEXT NOT NULL,
    base_price REAL NOT NULL CHECK (base_price >= 0),
    inventory_total INTEGER NOT NULL CHECK (inventory_total >= 0),
    inventory_available INTEGER NOT NULL CHECK (inventory_available >= 0),
    demand_multiplier REAL NOT NULL DEFAULT 1.0,
    rating REAL NOT NULL DEFAULT 4.0,
    summary TEXT NOT NULL,
    image_tone TEXT NOT NULL,
    amenities TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_search
ON listings (travel_type, origin, destination, departure_date);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    listing_id TEXT NOT NULL,
    travellers INTEGER NOT NULL CHECK (travellers > 0),
    status TEXT NOT NULL,
    subtotal REAL NOT NULL,
    taxes REAL NOT NULL,
    service_fee REAL NOT NULL,
    total_amount REAL NOT NULL,
    hold_expires_at TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (listing_id) REFERENCES listings(id)
);

CREATE INDEX IF NOT EXISTS idx_bookings_status
ON bookings (status, created_at);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    gateway TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    failure_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS provider_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT NOT NULL,
    provider_reference TEXT,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS transaction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS search_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    travel_type TEXT,
    origin TEXT,
    destination TEXT,
    results_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


SEED_LISTINGS = [
    {
        "id": "FLT-BOM-DEL-101",
        "travel_type": "flight",
        "title": "Morning non-stop to Delhi",
        "provider": "SkyBridge Airlines",
        "origin": "Mumbai",
        "destination": "Delhi",
        "offset": 14,
        "duration": "2h 10m",
        "base_price": 5890,
        "inventory_total": 52,
        "inventory_available": 18,
        "demand_multiplier": 1.16,
        "rating": 4.6,
        "summary": "06:20 BOM to 08:30 DEL. Cabin bag and meal included.",
        "image_tone": "sky",
        "amenities": ["Non-stop", "Meal included", "7 kg cabin bag"],
    },
    {
        "id": "FLT-BOM-DEL-202",
        "travel_type": "flight",
        "title": "Flexible evening flight",
        "provider": "Indus Air",
        "origin": "Mumbai",
        "destination": "Delhi",
        "offset": 14,
        "duration": "2h 20m",
        "base_price": 6250,
        "inventory_total": 46,
        "inventory_available": 29,
        "demand_multiplier": 1.04,
        "rating": 4.4,
        "summary": "18:10 BOM to 20:30 DEL. One free date change.",
        "image_tone": "sunset",
        "amenities": ["Non-stop", "Flexible change", "15 kg check-in"],
    },
    {
        "id": "HTL-GOA-301",
        "travel_type": "hotel",
        "title": "Casa Maris, North Goa",
        "provider": "StaySphere",
        "origin": "Mumbai",
        "destination": "Goa",
        "offset": 21,
        "duration": "3 nights",
        "base_price": 4200,
        "inventory_total": 32,
        "inventory_available": 7,
        "demand_multiplier": 1.23,
        "rating": 4.8,
        "summary": "Sea-facing rooms, breakfast, and flexible cancellation.",
        "image_tone": "coast",
        "amenities": ["Breakfast", "Pool", "Free cancellation"],
    },
    {
        "id": "HTL-JAI-302",
        "travel_type": "hotel",
        "title": "The Amber Courtyard",
        "provider": "Heritage Rooms",
        "origin": "Delhi",
        "destination": "Jaipur",
        "offset": 28,
        "duration": "2 nights",
        "base_price": 5100,
        "inventory_total": 24,
        "inventory_available": 16,
        "demand_multiplier": 1.08,
        "rating": 4.7,
        "summary": "Restored haveli near the old city with breakfast.",
        "image_tone": "heritage",
        "amenities": ["Breakfast", "Old city shuttle", "Courtyard"],
    },
    {
        "id": "BUS-PUN-GOA-401",
        "travel_type": "bus",
        "title": "Sleeper coach to Goa",
        "provider": "CoastLine Coaches",
        "origin": "Pune",
        "destination": "Goa",
        "offset": 10,
        "duration": "10h 30m",
        "base_price": 1450,
        "inventory_total": 36,
        "inventory_available": 12,
        "demand_multiplier": 1.11,
        "rating": 4.3,
        "summary": "21:30 Pune to 08:00 Panaji. AC sleeper with tracking.",
        "image_tone": "road",
        "amenities": ["AC sleeper", "Live tracking", "Charging point"],
    },
    {
        "id": "BUS-BLR-MYS-402",
        "travel_type": "bus",
        "title": "Express coach to Mysuru",
        "provider": "Southern Routes",
        "origin": "Bengaluru",
        "destination": "Mysuru",
        "offset": 7,
        "duration": "3h 20m",
        "base_price": 780,
        "inventory_total": 40,
        "inventory_available": 31,
        "demand_multiplier": 1.02,
        "rating": 4.5,
        "summary": "Frequent morning service with reserved seating.",
        "image_tone": "green",
        "amenities": ["Reserved seat", "Water bottle", "USB charging"],
    },
    {
        "id": "TRN-DEL-JAI-501",
        "travel_type": "train",
        "title": "Ajmer Shatabdi Executive",
        "provider": "RailConnect",
        "origin": "Delhi",
        "destination": "Jaipur",
        "offset": 12,
        "duration": "4h 35m",
        "base_price": 1890,
        "inventory_total": 72,
        "inventory_available": 9,
        "demand_multiplier": 1.19,
        "rating": 4.7,
        "summary": "06:10 NDLS to 10:45 JP. Breakfast included.",
        "image_tone": "rail",
        "amenities": ["Executive chair", "Breakfast", "Fast service"],
    },
    {
        "id": "TRN-MUM-GOA-502",
        "travel_type": "train",
        "title": "Konkan Coastal Express",
        "provider": "RailConnect",
        "origin": "Mumbai",
        "destination": "Goa",
        "offset": 19,
        "duration": "11h 45m",
        "base_price": 2200,
        "inventory_total": 80,
        "inventory_available": 22,
        "demand_multiplier": 1.12,
        "rating": 4.5,
        "summary": "Scenic overnight route with 2A reserved berths.",
        "image_tone": "coast",
        "amenities": ["2A berth", "Bedding", "Pantry service"],
    },
    {
        "id": "PKG-KERALA-601",
        "travel_type": "package",
        "title": "Kerala Backwaters Escape",
        "provider": "WanderCraft Holidays",
        "origin": "Mumbai",
        "destination": "Kochi",
        "offset": 35,
        "duration": "5 days",
        "base_price": 24900,
        "inventory_total": 20,
        "inventory_available": 8,
        "demand_multiplier": 1.14,
        "rating": 4.9,
        "summary": "Flights, boutique stays, houseboat night, and transfers.",
        "image_tone": "green",
        "amenities": ["Flights", "Hotels", "Houseboat"],
    },
    {
        "id": "PKG-LADAKH-602",
        "travel_type": "package",
        "title": "Ladakh High Roads",
        "provider": "Altitude Trails",
        "origin": "Delhi",
        "destination": "Leh",
        "offset": 42,
        "duration": "7 days",
        "base_price": 31900,
        "inventory_total": 18,
        "inventory_available": 5,
        "demand_multiplier": 1.25,
        "rating": 4.8,
        "summary": "Flights, acclimatization stay, lakes, passes, and guide.",
        "image_tone": "mountain",
        "amenities": ["Flights", "Guide", "Breakfast and dinner"],
    },
]


def get_db():
    if "db" not in g:
        db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        g.db = db
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(reset=False):
    db = get_db()
    if reset:
        db.executescript(
            """
            DROP TABLE IF EXISTS search_events;
            DROP TABLE IF EXISTS transaction_history;
            DROP TABLE IF EXISTS provider_confirmations;
            DROP TABLE IF EXISTS payments;
            DROP TABLE IF EXISTS bookings;
            DROP TABLE IF EXISTS listings;
            DROP TABLE IF EXISTS users;
            """
        )
    db.executescript(SCHEMA)

    user_count = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if not user_count:
        db.execute(
            "INSERT INTO users (full_name, email, phone) VALUES (?, ?, ?)",
            ("Aarav Mehta", "aarav@example.com", "+91 98765 43210"),
        )

    listing_count = db.execute(
        "SELECT COUNT(*) AS count FROM listings"
    ).fetchone()["count"]
    if listing_count:
        return

    today = date.today()
    for item in SEED_LISTINGS:
        db.execute(
            """
            INSERT INTO listings (
                id, travel_type, title, provider, origin, destination,
                departure_date, duration, base_price, inventory_total,
                inventory_available, demand_multiplier, rating, summary,
                image_tone, amenities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["travel_type"],
                item["title"],
                item["provider"],
                item["origin"],
                item["destination"],
                (today + timedelta(days=item["offset"])).isoformat(),
                item["duration"],
                item["base_price"],
                item["inventory_total"],
                item["inventory_available"],
                item["demand_multiplier"],
                item["rating"],
                item["summary"],
                item["image_tone"],
                json.dumps(item["amenities"]),
            ),
        )
