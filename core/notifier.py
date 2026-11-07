"""
Notification Module - WhatsApp (CallMeBot) & Diagnostics.
Envoie des alertes immédiates en cas de créneau détecté et des rapports Heartbeat.
"""

import datetime
import urllib.parse
import requests
from core.config import WHATSAPP_PHONE, WHATSAPP_API_KEY


def send_whatsapp(message: str) -> bool:
    """
    Envoie un message WhatsApp via l'API CallMeBot.
    Retourne True en cas de succès, False sinon.
    """
    if not WHATSAPP_PHONE or not WHATSAPP_API_KEY:
        print("[!] WHATSAPP_PHONE ou WHATSAPP_API_KEY non configuré dans .env")
        return False

    encoded_msg = urllib.parse.quote_plus(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text={encoded_msg}&apikey={WHATSAPP_API_KEY}"

    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            print("✅ Notification WhatsApp envoyée avec succès !")
            return True
        else:
            print(f"⚠️ Erreur CallMeBot ({response.status_code}) : {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur réseau lors de l'envoi WhatsApp : {e}")
        return False


def notify_slot_detected(center_name: str, slots_text: str, booking_url: str):
    """Alerte immédiate en cas d'ouverture de créneau."""
    alert_msg = (
        f"🚨 CRÉNEAU DISPONIBLE TLScontact {center_name} !\n\n"
        f"📅 Créneaux ouverts : {slots_text}\n"
        f"🔗 Lien direct : {booking_url}\n\n"
        f"⚡ Connectez-vous immédiatement pour finaliser la réservation !"
    )
    return send_whatsapp(alert_msg)


def send_heartbeat_report(agent_name: str, window_runs: int, success_count: int, error_count: int, start_time: datetime.datetime, next_run: datetime.datetime):
    """Envoie un rapport Heartbeat récapitulatif périodique."""
    duration_hours = (datetime.datetime.now() - start_time).total_seconds() / 3600.0
    status = "100% Nominal" if error_count == 0 else f"{error_count} incident(s)"

    msg = (
        f"🤖 [Heartbeat - {agent_name}]\n"
        f"✅ Surveillance active (0$ LLM, 100% autonome)\n\n"
        f"📊 Bilan des {window_runs} dernières vérifications (~{duration_hours:.1f}h) :\n"
        f"• Exécutions réussies : {success_count}/{window_runs}\n"
        f"• État : {status}\n"
        f"• Disponibilité : Aucun créneau ouvert pour l'instant\n"
        f"🕒 Prochaine vérification : {next_run.strftime('%H:%M')}\n\n"
        f"Veille continue active."
    )
    print("\n📲 Envoi du rapport périodique Heartbeat WhatsApp...")
    return send_whatsapp(msg)
