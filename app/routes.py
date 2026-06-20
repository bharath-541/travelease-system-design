import uuid
from datetime import date, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db
from .services import (
    BookingError,
    BookingService,
    CancellationService,
    PaymentService,
    SearchService,
)


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        recommendations=SearchService.recommendations(),
        default_date=(date.today() + timedelta(days=14)).isoformat(),
    )


@bp.get("/search")
def search():
    filters = {
        "travel_type": request.args.get("travel_type", "flight"),
        "origin": request.args.get("origin", ""),
        "destination": request.args.get("destination", ""),
        "departure_date": request.args.get("departure_date", ""),
        "max_price": request.args.get("max_price") or None,
        "sort_by": request.args.get("sort_by", "recommended"),
    }
    results, cache_hit = SearchService.search(**filters)
    return render_template(
        "results.html",
        results=results,
        filters=filters,
        cache_hit=cache_hit,
    )


@bp.post("/book/<listing_id>")
def create_booking(listing_id):
    try:
        booking = BookingService.create_hold(
            listing_id=listing_id,
            travellers=request.form.get("travellers", 1),
            idempotency_key=request.form.get("idempotency_key")
            or uuid.uuid4().hex,
        )
        return redirect(url_for("main.booking_review", booking_id=booking["id"]))
    except BookingError as error:
        return render_template(
            "failure.html",
            title="Inventory changed",
            message=str(error),
            booking=None,
        ), 409


@bp.get("/booking/<booking_id>")
def booking_review(booking_id):
    booking = BookingService.get_booking(booking_id)
    if not booking:
        abort(404)
    booking = BookingService.expire_if_needed(booking)
    return render_template("booking.html", booking=booking)


@bp.post("/payment/<booking_id>")
def process_payment(booking_id):
    scenario = request.form.get("scenario", "success")
    try:
        booking = PaymentService.process(booking_id, scenario)
    except BookingError as error:
        booking = BookingService.get_booking(booking_id)
        return render_template(
            "failure.html",
            title="Payment could not continue",
            message=str(error),
            booking=booking,
        ), 409

    if booking["status"] == "CONFIRMED":
        return redirect(url_for("main.confirmation", booking_id=booking_id))

    messages = {
        "PAYMENT_FAILED": "The payment gateway declined the transaction. Your inventory hold was released.",
        "PROVIDER_FAILED": "Payment was reversed because the external provider did not confirm the reservation.",
        "EXPIRED": "The inventory hold expired before payment was completed.",
    }
    return render_template(
        "failure.html",
        title="Booking was not confirmed",
        message=messages.get(
            booking["status"], "The booking could not be completed."
        ),
        booking=booking,
    ), 409


@bp.get("/confirmation/<booking_id>")
def confirmation(booking_id):
    booking = BookingService.get_booking(booking_id)
    if not booking:
        abort(404)
    provider = get_db().execute(
        """
        SELECT * FROM provider_confirmations
        WHERE booking_id = ?
        ORDER BY id DESC LIMIT 1
        """,
        (booking_id,),
    ).fetchone()
    return render_template(
        "confirmation.html",
        booking=booking,
        provider=dict(provider) if provider else None,
    )


@bp.post("/cancel/<booking_id>")
def cancel_booking(booking_id):
    try:
        booking = CancellationService.cancel(booking_id)
        flash("Cancellation recorded and refund workflow started.", "success")
        return render_template("cancelled.html", booking=booking)
    except BookingError as error:
        booking = BookingService.get_booking(booking_id)
        return render_template(
            "failure.html",
            title="Cancellation unavailable",
            message=str(error),
            booking=booking,
        ), 409


@bp.get("/system")
def system_overview():
    stats = {
        "listings": get_db()
        .execute("SELECT COUNT(*) AS count FROM listings")
        .fetchone()["count"],
        "bookings": get_db()
        .execute("SELECT COUNT(*) AS count FROM bookings")
        .fetchone()["count"],
        "confirmed": get_db()
        .execute(
            "SELECT COUNT(*) AS count FROM bookings WHERE status = 'CONFIRMED'"
        )
        .fetchone()["count"],
        "searches": get_db()
        .execute("SELECT COUNT(*) AS count FROM search_events")
        .fetchone()["count"],
    }
    events = get_db().execute(
        """
        SELECT booking_id, event_type, created_at
        FROM transaction_history
        ORDER BY id DESC LIMIT 8
        """
    ).fetchall()
    return render_template("system.html", stats=stats, events=events)
