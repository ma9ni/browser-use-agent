import os
import sys
import urllib.parse
from dotenv import load_dotenv
import requests

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

PHONE_NUMBER = os.getenv("WHATSAPP_PHONE", "33748252778").lstrip("+")
API_KEY = os.getenv("WHATSAPP_API_KEY", "1635718")


def send_whatsapp(message: str, phone: str = PHONE_NUMBER, api_key: str = API_KEY) -> bool:
    """Envoie un message WhatsApp via l'API CallMeBot."""
    clean_phone = phone.lstrip("+")
    text = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={text}&apikey={api_key}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True
        print(f"Erreur HTTP {response.status_code} : {response.text}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Erreur lors de l'envoi WhatsApp : {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "🤖 Notification de test depuis notify.py : Tout fonctionne parfaitement !"
    print(f"Envoi en cours vers {PHONE_NUMBER}...")
    success = send_whatsapp(msg)
    if success:
        print("✅ Message envoyé avec succès ! Regarde ton WhatsApp.")
    else:
        print("❌ Échec de l'envoi du message.")
