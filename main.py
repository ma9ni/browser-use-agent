#!/usr/bin/env python3
"""
Point d'entrée unifié pour la suite d'agents Browser-Use & Playwright.
Permet d'exécuter des agents Playwright déterministes (0$ de coût)
ou des agents IA autonomes (Browser-Use + LLM).
"""

import argparse
import asyncio
import sys
from pathlib import Path

from core.config import PROMPTS_DIR, PROJECT_ROOT
from core.notifier import send_whatsapp
from agents.playwright.tls_watcher import TLSContactWatcher
from agents.llm.browser_agent import LLMBrowserAgent


def cmd_tls(args):
    """Lance l'agent Playwright TLScontact Tunis (0$ LLM)."""
    print("\n" + "=" * 65)
    print("⚡ AGENT PLAYWRIGHT TLSCONTACT TUNIS (100% GRATUIT / 0$ LLM)")
    print("=" * 65)
    print(f"🎯 Centre surveillé       : Tunis (tnTUN2fr)")
    print(f"⏱️  Mode                   : {'Boucle toutes les ' + str(args.interval) + ' min' if args.interval > 0 else 'Vérification unique'}")
    if args.interval > 0 and args.heartbeat > 0:
        hb_h = (args.interval * args.heartbeat) / 60.0
        print(f"💬 Rapport Heartbeat      : Tous les {args.heartbeat} passages (~{hb_h:.1f} heures)")
    print(f"🖥️  Affichage navigateur  : {'Arrière-plan (headless)' if args.headless else 'Fenêtre visible en direct'}")
    print("=" * 65 + "\n")

    watcher = TLSContactWatcher(headless=args.headless, timeout_sec=args.timeout, months_to_check=args.months)

    if args.interval <= 0:
        res = asyncio.run(watcher.check_once())
        sys.exit(0 if res.get("success") else 1)
    else:
        watcher.start_monitoring(interval_minutes=args.interval, heartbeat_frequency=args.heartbeat)


def cmd_agent(args):
    """Lance un agent IA Browser-Use avec un ou plusieurs prompts."""
    # Résolution des prompts
    tasks = []
    if args.task:
        tasks.append({"content": args.task, "label": "Argument direct (--task)"})
    elif args.prompts:
        for p in args.prompts:
            path = Path(p)
            if not path.exists():
                path = PROMPTS_DIR / p
            if not path.suffix and not path.exists():
                path = path.with_suffix(".txt")
            if not path.exists():
                path = PROMPTS_DIR / f"{p}.txt"

            if not path.exists():
                print(f"[!] Fichier prompt introuvable : {p}")
                continue

            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            tasks.append({"content": content, "label": path.name})

    if not tasks:
        print("[!] Aucun prompt spécifié. Utilisez un fichier dans prompts/ ou l'option -t '...'")
        sys.exit(1)

    agent = LLMBrowserAgent(headless=args.headless)
    for t in tasks:
        asyncio.run(agent.run_task(task_prompt=t["content"], job_label=t["label"]))


def cmd_test_notify(args):
    """Envoie un message de test sur WhatsApp."""
    print("📲 Envoi d'un message test via CallMeBot...")
    success = send_whatsapp("🤖 [Test Agent] Connexion WhatsApp établie avec succès depuis le projet !")
    if success:
        print("🎉 Notification WhatsApp reçue avec succès !")
    else:
        print("❌ Échec de la notification. Vérifiez WHATSAPP_PHONE et WHATSAPP_API_KEY dans .env.")


def cmd_list_prompts(args):
    """Liste les prompts disponibles dans prompts/."""
    print(f"\n📂 Prompts disponibles dans {PROMPTS_DIR} :")
    for f in sorted(PROMPTS_DIR.glob("*.txt")):
        print(f"  • {f.name}")
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="Suite d'Agents d'Automatisation Navigateur (Playwright & Browser-Use LLM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # 1. Commande TLS
    p_tls = subparsers.add_parser("tls", help="Lancer l'agent Playwright TLScontact Tunis (0$ LLM)")
    p_tls.add_argument("-i", "--interval", type=int, default=0, help="Intervalle en minutes (0 = exécution unique)")
    p_tls.add_argument("-s", "--heartbeat", type=int, default=24, help="Fréquence du rapport WhatsApp (défaut: 24 passages)")
    p_tls.add_argument("--headless", action="store_true", help="Exécuter en arrière-plan sans affichage")
    p_tls.add_argument("--timeout", type=int, default=60, help="Timeout par page en secondes")
    p_tls.add_argument("--months", type=int, default=3, help="Nombre de mois à inspecter")
    p_tls.set_defaults(func=cmd_tls)

    # 2. Commande Agent LLM
    p_agent = subparsers.add_parser("agent", help="Lancer un agent IA Browser-Use avec un fichier prompt")
    p_agent.add_argument("prompts", nargs="*", help="Nom(s) de fichier(s) de prompt (ex: tls.txt, freework_sre.txt)")
    p_agent.add_argument("-t", "--task", type=str, default=None, help="Texte direct du prompt")
    p_agent.add_argument("--headless", action="store_true", help="Mode arrière-plan")
    p_agent.set_defaults(func=cmd_agent)

    # 3. Test WhatsApp
    p_notify = subparsers.add_parser("test-notify", help="Tester la notification WhatsApp CallMeBot")
    p_notify.set_defaults(func=cmd_test_notify)

    # 4. Liste des prompts
    p_list = subparsers.add_parser("list-prompts", help="Lister tous les prompts disponibles")
    p_list.set_defaults(func=cmd_list_prompts)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
