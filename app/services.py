import json
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from .db import get_db


class BookingError(Exception):
    pass


class InventoryUnavailable(BookingError):
    pass


class InvalidBookingState(BookingError):
    pass


def _money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _utc_now():
    return datetime.now(timezone.utc)


def _row_to_dict(row):
    if row is None:
        return None
    value = dict(row)
    if "amenities" in value:
        value["amenities"] = json.loads(value["amenities"])
    return value


class PricingService:
    TAX_RATE = Decimal("0.12")
    SERVICE_FEE_RATE = Decimal("0.035")

    @classmethod
    def quote(cls, listing, travellers=1):
        available = max(int(listing["inventory_available"]), 0)
        total = max(int(listing["inventory_total"]), 1)
        scarcity = Decimal(str(1 + ((total - available) / total) * 0.18))
        demand = Decimal(str(listing["demand_multiplier"]))
        unit_price = _money(Decimal(str(listing["base_price"])) * demand * scarcity)
        subtotal = _money(unit_price * int(travellers))
        taxes = _money(subtotal * cls.TAX_RATE)
        service_fee = _money(subtotal * cls.SERVICE_FEE_RATE)
        total_amount = _money(subtotal + taxes + service_fee)
        return {
            "unit_price": float(unit_price),
            "subtotal": float(subtotal),
            "taxes": float(taxes),
            "service_fee": float(service_fee),
            "total_amount": float(total_amount),
            "scarcity_multiplier": float(scarcity),
        }


class SearchService:
    _cache = {}
    _cache_lock = threading.Lock()
    CACHE_TTL_SECONDS = 30

    @classmethod
    def search(
        cls,
        travel_type="flight",
        origin="",
        destination="",
        departure_date="",
        max_price=None,
        sort_by="recommended",
    ):
        key = (
            travel_type.lower(),
            origin.lower().strip(),
            destination.lower().strip(),
            departure_date,
            str(max_price or ""),
            sort_by,
        )
        now = time.monotonic()
        with cls._cache_lock:
            cached = cls._cache.get(key)
            if cached and now - cached["created_at"] < cls.CACHE_TTL_SECONDS:
                return cached["results"], True

        db = get_db()
        clauses = ["travel_type = ?"]
        params = [travel_type.lower()]
        if origin:
            clauses.append("LOWER(origin) LIKE ?")
            params.append(f"%{origin.lower().strip()}%")
        if destination:
            clauses.append("LOWER(destination) LIKE ?")
            params.append(f"%{destination.lower().strip()}%")
        if departure_date:
            clauses.append("departure_date >= ?")
            params.append(departure_date)

        rows = db.execute(
            f"SELECT * FROM listings WHERE {' AND '.join(clauses)}",
            params,
        ).fetchall()

        results = []
        for row in rows:
            listing = _row_to_dict(row)
            listing["quote"] = PricingService.quote(listing)
            if max_price and listing["quote"]["total_amount"] > float(max_price):
                continue
            listing["inventory_label"] = (
                f"Only {listing['inventory_available']} left"
                if listing["inventory_available"] <= 10
                else "Good availability"
            )
            results.append(listing)

        if sort_by == "price":
            results.sort(key=lambda item: item["quote"]["total_amount"])
        elif sort_by == "rating":
            results.sort(key=lambda item: item["rating"], reverse=True)
        else:
            results.sort(
                key=lambda item: (
                    item["rating"] * 10
                    + item["inventory_available"] / max(item["inventory_total"], 1)
                    - item["quote"]["total_amount"] / 100000
                ),
                reverse=True,
            )

        db.execute(
            """
            INSERT INTO search_events (
                travel_type, origin, destination, results_count
            ) VALUES (?, ?, ?, ?)
            """,
            (travel_type, origin, destination, len(results)),
        )

        with cls._cache_lock:
            cls._cache[key] = {"created_at": now, "results": results}
        return results, False

    @staticmethod
    def recommendations(limit=4):
        rows = get_db().execute(
            """
            SELECT * FROM listings
            ORDER BY rating DESC, demand_multiplier DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        recommendations = []
        for row in rows:
            listing = _row_to_dict(row)
            listing["quote"] = PricingService.quote(listing)
            recommendations.append(listing)
        return recommendations


class BookingService:
    HOLD_MINUTES = 10

    @staticmethod
    def get_booking(booking_id):
        row = get_db().execute(
            """
            SELECT
                b.*,
                u.full_name,
                u.email,
                u.phone,
                l.title,
                l.provider,
                l.travel_type,
                l.origin,
                l.destination,
                l.departure_date,
                l.duration,
                l.summary,
                l.amenities
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            JOIN listings l ON l.id = b.listing_id
            WHERE b.id = ?
            """,
            (booking_id,),
        ).fetchone()
        return _row_to_dict(row)

    @classmethod
    def create_hold(cls, listing_id, travellers, idempotency_key):
        db = get_db()
        existing = db.execute(
            "SELECT id FROM bookings WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return cls.get_booking(existing["id"])

        travellers = max(int(travellers), 1)
        booking_id = f"TLE-{uuid.uuid4().hex[:8].upper()}"
        expires_at = _utc_now() + timedelta(minutes=cls.HOLD_MINUTES)

        try:
            db.execute("BEGIN IMMEDIATE")
            listing_row = db.execute(
                "SELECT * FROM listings WHERE id = ?",
                (listing_id,),
            ).fetchone()
            if not listing_row:
                raise BookingError("The selected listing does not exist.")
            listing = _row_to_dict(listing_row)
            if listing["inventory_available"] < travellers:
                raise InventoryUnavailable(
                    "The requested inventory is no longer available."
                )

            quote = PricingService.quote(listing, travellers)
            db.execute(
                """
                UPDATE listings
                SET inventory_available = inventory_available - ?
                WHERE id = ? AND inventory_available >= ?
                """,
                (travellers, listing_id, travellers),
            )
            if db.execute("SELECT changes() AS count").fetchone()["count"] != 1:
                raise InventoryUnavailable(
                    "Another booking used the last available inventory."
                )

            db.execute(
                """
                INSERT INTO bookings (
                    id, user_id, listing_id, travellers, status, subtotal,
                    taxes, service_fee, total_amount, hold_expires_at,
                    idempotency_key
                ) VALUES (?, 1, ?, ?, 'HELD', ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    listing_id,
                    travellers,
                    quote["subtotal"],
                    quote["taxes"],
                    quote["service_fee"],
                    quote["total_amount"],
                    expires_at.isoformat(),
                    idempotency_key,
                ),
            )
            db.execute(
                """
                INSERT INTO transaction_history (
                    booking_id, event_type, details
                ) VALUES (?, 'INVENTORY_HELD', ?)
                """,
                (
                    booking_id,
                    json.dumps(
                        {
                            "listing_id": listing_id,
                            "travellers": travellers,
                            "expires_at": expires_at.isoformat(),
                        }
                    ),
                ),
            )
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise

        return cls.get_booking(booking_id)

    @classmethod
    def release_inventory(cls, db, booking):
        db.execute(
            """
            UPDATE listings
            SET inventory_available = MIN(
                inventory_total,
                inventory_available + ?
            )
            WHERE id = ?
            """,
            (booking["travellers"], booking["listing_id"]),
        )

    @classmethod
    def expire_if_needed(cls, booking):
        if booking["status"] != "HELD" or not booking["hold_expires_at"]:
            return booking
        expires_at = datetime.fromisoformat(booking["hold_expires_at"])
        if expires_at > _utc_now():
            return booking

        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking["id"],),
            ).fetchone()
            if current and current["status"] == "HELD":
                cls.release_inventory(db, current)
                db.execute(
                    """
                    UPDATE bookings
                    SET status = 'EXPIRED', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (booking["id"],),
                )
                db.execute(
                    """
                    INSERT INTO transaction_history (
                        booking_id, event_type, details
                    ) VALUES (?, 'HOLD_EXPIRED', '{}')
                    """,
                    (booking["id"],),
                )
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        return cls.get_booking(booking["id"])


class ProviderIntegrationSimulator:
    @staticmethod
    def confirm(booking_id, outcome="success"):
        if outcome == "timeout":
            return {
                "status": "TIMEOUT",
                "reference": None,
                "message": "Provider API timed out before confirmation.",
            }
        if outcome == "reject":
            return {
                "status": "REJECTED",
                "reference": None,
                "message": "Provider rejected the reservation after revalidation.",
            }
        return {
            "status": "CONFIRMED",
            "reference": f"PV-{uuid.uuid4().hex[:10].upper()}",
            "message": "Inventory confirmed by the external provider.",
        }


class PaymentService:
    @classmethod
    def process(cls, booking_id, scenario="success"):
        booking = BookingService.get_booking(booking_id)
        if not booking:
            raise BookingError("Booking not found.")
        booking = BookingService.expire_if_needed(booking)
        if booking["status"] == "CONFIRMED":
            return booking
        if booking["status"] != "HELD":
            raise InvalidBookingState(
                f"Payment cannot be processed for a {booking['status']} booking."
            )

        payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"
        payment_key = f"{booking_id}:payment-v1"
        db = get_db()
        existing = db.execute(
            "SELECT status FROM payments WHERE idempotency_key = ?",
            (payment_key,),
        ).fetchone()
        if existing:
            return BookingService.get_booking(booking_id)

        payment_failed = scenario == "payment_failure"
        try:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            if not current or current["status"] != "HELD":
                raise InvalidBookingState("The booking hold is no longer payable.")

            db.execute(
                """
                INSERT INTO payments (
                    id, booking_id, amount, status, gateway,
                    idempotency_key, failure_reason
                ) VALUES (?, ?, ?, ?, 'TravelEase PaySim', ?, ?)
                """,
                (
                    payment_id,
                    booking_id,
                    current["total_amount"],
                    "DECLINED" if payment_failed else "APPROVED",
                    payment_key,
                    "Simulated payment gateway decline"
                    if payment_failed
                    else None,
                ),
            )

            if payment_failed:
                BookingService.release_inventory(db, current)
                db.execute(
                    """
                    UPDATE bookings
                    SET status = 'PAYMENT_FAILED', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (booking_id,),
                )
                db.execute(
                    """
                    INSERT INTO transaction_history (
                        booking_id, event_type, details
                    ) VALUES (?, 'PAYMENT_DECLINED', ?)
                    """,
                    (
                        booking_id,
                        json.dumps({"payment_id": payment_id}),
                    ),
                )
                db.execute("COMMIT")
                return BookingService.get_booking(booking_id)

            db.execute(
                """
                UPDATE bookings
                SET status = 'PAYMENT_APPROVED', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (booking_id,),
            )
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise

        provider_outcome = {
            "provider_timeout": "timeout",
            "provider_reject": "reject",
        }.get(scenario, "success")
        provider_result = ProviderIntegrationSimulator.confirm(
            booking_id, provider_outcome
        )

        try:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            db.execute(
                """
                INSERT INTO provider_confirmations (
                    booking_id, provider_reference, status, message
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    booking_id,
                    provider_result["reference"],
                    provider_result["status"],
                    provider_result["message"],
                ),
            )

            if provider_result["status"] == "CONFIRMED":
                db.execute(
                    """
                    UPDATE bookings
                    SET status = 'CONFIRMED', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (booking_id,),
                )
                event_type = "BOOKING_CONFIRMED"
            else:
                BookingService.release_inventory(db, current)
                db.execute(
                    """
                    UPDATE bookings
                    SET status = 'PROVIDER_FAILED', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (booking_id,),
                )
                db.execute(
                    """
                    UPDATE payments
                    SET status = 'REFUNDED',
                        failure_reason = 'Provider confirmation failed'
                    WHERE booking_id = ?
                    """,
                    (booking_id,),
                )
                event_type = "COMPENSATING_REFUND"

            db.execute(
                """
                INSERT INTO transaction_history (
                    booking_id, event_type, details
                ) VALUES (?, ?, ?)
                """,
                (
                    booking_id,
                    event_type,
                    json.dumps(provider_result),
                ),
            )
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise

        return BookingService.get_booking(booking_id)


class CancellationService:
    @staticmethod
    def cancel(booking_id):
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            booking = db.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            if not booking:
                raise BookingError("Booking not found.")
            if booking["status"] not in {
                "HELD",
                "PAYMENT_APPROVED",
                "CONFIRMED",
            }:
                raise InvalidBookingState(
                    f"A {booking['status']} booking cannot be cancelled."
                )

            BookingService.release_inventory(db, booking)
            db.execute(
                """
                UPDATE bookings
                SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (booking_id,),
            )
            db.execute(
                """
                UPDATE payments
                SET status = 'REFUNDED'
                WHERE booking_id = ? AND status = 'APPROVED'
                """,
                (booking_id,),
            )
            db.execute(
                """
                INSERT INTO transaction_history (
                    booking_id, event_type, details
                ) VALUES (?, 'BOOKING_CANCELLED', ?)
                """,
                (
                    booking_id,
                    json.dumps(
                        {
                            "refund": "initiated",
                            "inventory_released": booking["travellers"],
                        }
                    ),
                ),
            )
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        return BookingService.get_booking(booking_id)
