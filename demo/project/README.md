# Demo project — Small app with a deliberate authentication bug

This is a **deterministic** demo project for the KALKI hackathon.

## The Bug

`auth.py` reads `AUTH_SECRET_KEY` from `config` instead of `SECRET_KEY`.
This causes `verify_token()` to raise a `KeyError`, which makes all
authenticated endpoints return 401.

## Expected KALKI Flow

1. Receive objective: *"Fix the auth bug, run the tests, deploy and verify."*
2. Inspect files → find the auth module
3. Read `auth.py` → identify the wrong config key
4. Fix `auth.py` → change `AUTH_SECRET_KEY` to `SECRET_KEY`
5. Run `test_app.py` → tests pass
6. Deploy → success
7. Verify → all checks pass

## Running the test manually

```bash
cd demo/project
python -m pytest test_app.py -v
# Will FAIL until the bug in auth.py is fixed
```
