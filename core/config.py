"""
Central Configuration & Environment Management.
Gère le chargement sécurisé des variables d'environnement, les chemins du projet
et les données d'authentification sans risque de fuite dans les logs.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Chargement du fichier .env
load_dotenv(PROJECT_ROOT / ".env")

# Identifiants TLScontact
TLS_EMAIL = os.getenv("TLS_EMAIL", "")
TLS_PASSWORD = os.getenv("TLS_PASSWORD", "")

# Notification WhatsApp (CallMeBot)
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "33748252778")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "1635718")

# LLM Providers (OpenRouter / Gemini)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "true").lower() in ("true", "1", "yes")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Dossiers standards
PROMPTS_DIR = PROJECT_ROOT / "prompts"
PROFILES_DIR = PROJECT_ROOT / "profiles"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
TLS_USER_PROFILE_DIR = PROJECT_ROOT / "tls_user_profile"

# S'assurer de la présence des répertoires
SCREENSHOTS_DIR.mkdir(exist_ok=True)
PROFILES_DIR.mkdir(exist_ok=True)
TLS_USER_PROFILE_DIR.mkdir(exist_ok=True)

# URLs TLScontact
TLS_TUNIS_URL = "https://visas-fr.tlscontact.com/fr-fr/country/tn/vac/tnTUN2fr"
TLS_APPOINTMENT_URL_PATTERN = "/workflow/appointment-booking/tnTUN2fr"


def get_sensitive_data() -> dict:
    """Retourne le dictionnaire des variables masquées pour Browser-Use Agent."""
    secrets = {}
    if TLS_EMAIL:
        secrets["tls_email"] = TLS_EMAIL
    if TLS_PASSWORD:
        secrets["tls_password"] = TLS_PASSWORD
    return secrets
