"""Demo project configuration."""

# Application settings
APP_NAME = "KALKI Demo App"
APP_VERSION = "1.0.0"
DEBUG = True

# Authentication
SECRET_KEY = "kalki-demo-secret-key-2026"
TOKEN_EXPIRY_SECONDS = 3600

# Database (in-memory for demo)
DATABASE_URL = "sqlite:///:memory:"
