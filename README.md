# TravelEase

TravelEase is a Flask-based academic system design project for a scalable travel booking platform similar to MakeMyTrip and Booking.com. It demonstrates travel search, dynamic pricing, transactional inventory holds, payment simulation, external provider confirmation, cancellation, refund compensation, and auditable workflow events.

**Student:** Perni Bharath Raghavendra  
**Roll number:** 150096724139  
**Programme:** B.Tech CSE, Semester 4  
**Cohort:** Mark Zuckerberg Cohort  
**University:** ITM Skills University  
**Course:** System Design  
**GitHub repository:** [bharath-541/travelease-system-design](https://github.com/bharath-541/travelease-system-design)<br>
**Live application:** [travelease-system-design.onrender.com](https://travelease-system-design.onrender.com/)

## Project Deliverables

- Flask website with search, results, booking review, payment simulation, confirmation, cancellation, and failure states
- SQLite schema and seeded inventory for flights, hotels, buses, trains, and packages
- Python service layer for search, pricing, booking, payment, provider integration, and cancellation
- Editable Mermaid architecture, booking sequence, and database diagrams
- Exported PNG architecture diagrams
- Consolidated PDF project documentation
- pytest workflow tests
- Browser screenshots used in the final report

No ZIP file is created by the project scripts. For final submission, the folder can be renamed to `Perni_Bharath_Raghavendra_TravelEase_150096724139` and compressed only when explicitly requested.

## Project Structure

```text
.
├── app/
│   ├── db.py
│   ├── routes.py
│   ├── services.py
│   ├── templates/
│   └── static/
├── docs/
│   ├── PROJECT_DOCUMENTATION.md
│   ├── diagrams/
│   └── screenshots/
├── output/pdf/
├── scripts/
├── tests/
├── requirements.txt
└── run.py
```

## Requirements

- Python 3.10 or newer
- pip

Dependencies:

- Flask
- Pillow
- ReportLab
- pytest

## Setup Instructions

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Run the Website

Generate the diagram images:

```bash
python3 scripts/generate_architecture.py
python3 scripts/generate_sequence.py
```

Start Flask:

```bash
python3 run.py
```

Open:

```text
http://127.0.0.1:5000
```

The SQLite database is created automatically at `instance/travelease.sqlite3`.

## Deployment on Render

TravelEase includes a Render Blueprint for a free Python web service in the Singapore region.

Live deployment: [https://travelease-system-design.onrender.com/](https://travelease-system-design.onrender.com/)

1. Open the [TravelEase Render Blueprint](https://dashboard.render.com/blueprint/new?repo=https://github.com/bharath-541/travelease-system-design).
2. Sign in to Render and connect the `bharath-541/travelease-system-design` GitHub repository when prompted.
3. Keep the Blueprint defaults and click **Apply**.
4. Wait for the build and health check to complete, then open the generated `onrender.com` URL.

Render automatically deploys future pushes to `main`. Free services can take about a minute to wake after being idle. This academic demo uses SQLite, so booking and search-history changes can reset after a restart or redeploy; provider inventory is seeded automatically when the app starts.

## Demonstration Workflow

1. Search the default Mumbai-to-Delhi flight route.
2. Select **Review booking** on a result.
3. Observe the ten-minute transactional inventory hold.
4. Choose one of the payment simulations:
   - Successful booking
   - Payment decline
   - Provider timeout
   - Provider rejection
5. Confirm payment and inspect the resulting confirmation or compensated failure state.
6. On a successful booking, cancel it to demonstrate inventory release and refund state.
7. Open **System View** to inspect architecture and recent transaction events.

## Run Tests

```bash
python3 -m pytest -q
```

The tests cover:

- Search filtering and cache hits
- Successful booking confirmation
- Payment failure with inventory release
- Provider timeout with payment refund compensation
- Cancellation with inventory restoration
- Core Flask page rendering

## Generate the PDF Report

First generate the diagrams and capture website screenshots:

```bash
python3 scripts/generate_architecture.py
python3 scripts/generate_sequence.py
python3 scripts/generate_report.py
```

The final PDF is written to:

```text
output/pdf/TravelEase_Project_Documentation.pdf
```

The report covers:

- Problem statement and proposed solution
- Functional and non-functional requirements
- Detailed architecture
- Search, pricing, booking, payment, confirmation, and cancellation workflows
- Database design and synchronization
- Python algorithm and implementation
- Scalability and fault tolerance
- Technology stack, module description, screenshots, comparison, and future scope

## Architecture Decisions

- Search uses an eventually consistent read model because discovery traffic is large and can tolerate brief staleness.
- Inventory holds and booking state use a strongly consistent transaction to prevent overbooking.
- Payment operations use idempotency keys to prevent duplicate charges.
- Provider failures trigger Saga compensation: inventory release and payment refund.
- Production synchronization uses an event bus and transactional outbox rather than distributed two-phase commit.
- Redis and OpenSearch scale popular searches independently from PostgreSQL booking writes.

## Academic Simulation Notes

This implementation uses local SQLite and simulated external providers so it runs without API keys or paid services. The report explains the production equivalents: PostgreSQL, Redis, OpenSearch, Kafka, multiple payment gateways, supplier adapters, observability, retries, circuit breakers, and reconciliation.

## Final Submission

Use `Perni_Bharath_Raghavendra_TravelEase_150096724139` as the final folder name. Create the ZIP only when the project owner explicitly requests it.
