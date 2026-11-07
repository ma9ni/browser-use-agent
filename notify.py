#!/usr/bin/env python3
"""
Wrapper de rétrocompatibilité pour l'envoi de notifications WhatsApp.
Délègue l'exécution à core.notifier.send_whatsapp.
"""

import sys
from core.notifier import send_whatsapp

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = "🚨 Test de notification WhatsApp depuis le module notify.py"

    print(f"Message à envoyer : {message}")
    send_whatsapp(message)
