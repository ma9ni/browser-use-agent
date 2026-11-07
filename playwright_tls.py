#!/usr/bin/env python3
"""
Wrapper de rétrocompatibilité pour lancer l'agent Playwright TLScontact Tunis.
Délègue l'exécution à agents.playwright.tls_watcher.TLSContactWatcher.
"""

import argparse
import asyncio
import sys
from agents.playwright.tls_watcher import TLSContactWatcher


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérificateur 100% autonome de créneaux TLScontact Tunis via Playwright (0$ de coût)."
    )
    parser.add_argument("-i", "--interval", type=int, default=0, help="Intervalle en minutes (0 = unique)")
    parser.add_argument("-s", "--heartbeat", type=int, default=24, help="Fréquence du rapport WhatsApp")
    parser.add_argument("--headless", action="store_true", help="Arrière-plan sans affichage")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout par page")
    parser.add_argument("--months", type=int, default=3, help="Nombre de mois à inspecter")
    return parser.parse_args()


def main():
    args = parse_args()
    watcher = TLSContactWatcher(headless=args.headless, timeout_sec=args.timeout, months_to_check=args.months)

    if args.interval <= 0:
        res = asyncio.run(watcher.check_once())
        sys.exit(0 if res.get("success") else 1)
    else:
        watcher.start_monitoring(interval_minutes=args.interval, heartbeat_frequency=args.heartbeat)


if __name__ == "__main__":
    main()
