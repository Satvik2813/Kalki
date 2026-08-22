"""Deterministic demo project — a small app with a deliberate auth bug.

This project is used by KALKI's hackathon demo to demonstrate the full
autonomous engineering loop:

    OBJECTIVE → INSPECT → PLAN → READ CODE → MODIFY CODE → RUN TEST →
    FAIL → DIAGNOSE → FIX → TEST AGAIN → DEPLOY → VERIFY → SUCCESS

The bug: ``auth.py`` reads ``AUTH_SECRET_KEY`` instead of ``SECRET_KEY``,
causing all JWT validation to fail with a KeyError.

The test: ``test_app.py`` verifies that authenticated endpoints work.
It fails until the bug is fixed.
"""
