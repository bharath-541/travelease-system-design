from app.db import get_db
from app.services import (
    BookingService,
    CancellationService,
    PaymentService,
    SearchService,
)


def create_hold():
    return BookingService.create_hold(
        listing_id="FLT-BOM-DEL-101",
        travellers=2,
        idempotency_key="test-hold",
    )


def test_search_filters_and_caches(app):
    with app.app_context():
        first, first_cache_hit = SearchService.search(
            travel_type="flight",
            origin="Mumbai",
            destination="Delhi",
        )
        second, second_cache_hit = SearchService.search(
            travel_type="flight",
            origin="Mumbai",
            destination="Delhi",
        )
        assert len(first) == 2
        assert first_cache_hit is False
        assert second_cache_hit is True
        assert second[0]["quote"]["total_amount"] > 0


def test_successful_booking_confirmation(app):
    with app.app_context():
        booking = create_hold()
        confirmed = PaymentService.process(booking["id"], "success")
        assert confirmed["status"] == "CONFIRMED"
        provider = get_db().execute(
            "SELECT status FROM provider_confirmations WHERE booking_id = ?",
            (booking["id"],),
        ).fetchone()
        assert provider["status"] == "CONFIRMED"


def test_payment_failure_releases_inventory(app):
    with app.app_context():
        before = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        booking = create_hold()
        after_hold = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        failed = PaymentService.process(booking["id"], "payment_failure")
        after_failure = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        assert after_hold == before - 2
        assert failed["status"] == "PAYMENT_FAILED"
        assert after_failure == before


def test_provider_timeout_compensates_payment_and_inventory(app):
    with app.app_context():
        before = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        booking = create_hold()
        failed = PaymentService.process(booking["id"], "provider_timeout")
        payment = get_db().execute(
            "SELECT status FROM payments WHERE booking_id = ?",
            (booking["id"],),
        ).fetchone()
        after = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        assert failed["status"] == "PROVIDER_FAILED"
        assert payment["status"] == "REFUNDED"
        assert after == before


def test_cancellation_refunds_and_restores_inventory(app):
    with app.app_context():
        before = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        booking = create_hold()
        confirmed = PaymentService.process(booking["id"], "success")
        cancelled = CancellationService.cancel(confirmed["id"])
        after = get_db().execute(
            "SELECT inventory_available FROM listings WHERE id = ?",
            ("FLT-BOM-DEL-101",),
        ).fetchone()["inventory_available"]
        payment = get_db().execute(
            "SELECT status FROM payments WHERE booking_id = ?",
            (booking["id"],),
        ).fetchone()
        assert cancelled["status"] == "CANCELLED"
        assert payment["status"] == "REFUNDED"
        assert after == before


def test_web_pages_render(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Search smarter" in response.data

    response = client.get(
        "/search?travel_type=flight&origin=Mumbai&destination=Delhi"
    )
    assert response.status_code == 200
    assert b"Morning non-stop to Delhi" in response.data
