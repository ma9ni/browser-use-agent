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


def notify_slot_detected(center_name: str, slots_text: str, booking_url: str) -> bool:
    """Alerte immédiate en cas d'ouverture de créneau."""
    alert_msg = (
        f"🚨 CRÉNEAU DISPONIBLE TLScontact {center_name} !\n\n"
        f"📅 Créneaux ouverts : {slots_text}\n"
        f"🔗 Lien direct : {booking_url}\n\n"
        f"⚡ Connectez-vous immédiatement pour finaliser la réservation !"
    )
    return send_whatsapp(alert_msg)


def notify_critical_error(title: str, error_details: str, current_url: str = "", action_required: str = "") -> bool:
    """Alerte immédiate WhatsApp en cas d'anomalie critique (dossier supprimé, blocage répété, etc.)."""
    lines = [
        f"🚨 [ALERTE CRITIQUE - TLScontact]",
        f"⚠️ {title}",
        "",
        f"🔍 Détails : {error_details}",
    ]
    if current_url:
        lines.append(f"🔗 Page : {current_url}")
    if action_required:
        lines.extend(["", f"👉 Action requise : {action_required}"])
    return send_whatsapp("\n".join(lines))


def notify_recovery(agent_name: str, previous_errors: int, details: str = "") -> bool:
    """Notifie le rétablissement du service après une série d'échecs."""
    msg = (
        f"✅ [RÉTABLISSEMENT - {agent_name}]\n"
        f"La surveillance du calendrier TLScontact est de nouveau opérationnelle après {previous_errors} échec(s) consécutif(s).\n"
    )
    if details:
        msg += f"ℹ️ {details}\n"
    return send_whatsapp(msg)


def send_heartbeat_report(
    agent_name: str,
    window_runs: int,
    success_count: int,
    error_count: int,
    start_time: datetime.datetime,
    next_run: datetime.datetime,
    last_error: str = "",
    consecutive_errors: int = 0,
) -> bool:
    """Envoie un rapport Heartbeat récapitulatif périodique fidèle à l'état réel."""
    duration_hours = (datetime.datetime.now() - start_time).total_seconds() / 3600.0

    if success_count == 0 and error_count > 0:
        header_status = "🚨 ALERTE : Échec de toutes les vérifications sur la période !"
        availability_line = "• Disponibilité : INCONNUE (le calendrier n'a pas pu être atteint)"
    elif error_count > 0:
        header_status = f"⚠️ Surveillance dégradée ({error_count} incident(s) sur {window_runs})"
        availability_line = f"• Disponibilité : Aucun créneau sur les {success_count} passage(s) réussi(s)"
    else:
        header_status = "✅ Surveillance 100% nominale (0$ LLM, autonome)"
        availability_line = "• Disponibilité : Aucun créneau ouvert (calendrier bien inspecté)"

    status = "100% Nominal" if error_count == 0 else f"{error_count} incident(s)"
    if consecutive_errors > 0:
        status += f" ({consecutive_errors} en cours)"

    lines = [
        f"🤖 [Heartbeat - {agent_name}]",
        header_status,
        "",
        f"📊 Bilan des {window_runs} dernières vérifications (~{duration_hours:.1f}h) :",
        f"• Exécutions réussies : {success_count}/{window_runs}",
        f"• État : {status}",
        availability_line,
    ]
    if last_error and error_count > 0:
        lines.append(f"• Dernière anomalie : {last_error[:180]}")
    lines.extend([
        f"🕒 Prochaine vérification : {next_run.strftime('%H:%M')}",
        "",
        "Veille continue active.",
    ])

    print("\n📲 Envoi du rapport périodique Heartbeat WhatsApp...")
    return send_whatsapp("\n".join(lines))
