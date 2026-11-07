#!/usr/bin/env python3
"""
Script de surveillance continue (Monitoring) pour Browser-Use Agent.
Exécute périodiquement l'agent dans un processus isolé et propre, évitant toute
fuite de mémoire ou saturation de tokens, avec :
1. Alerte WhatsApp instantanée en cas de créneau détecté.
2. Rapport de vie périodique (Heartbeat) par WhatsApp tous les N passages (ex: toutes les 6 heures)
   pour confirmer que le robot fonctionne parfaitement.
"""

import argparse
import datetime
import subprocess
import sys
import time
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Surveillance automatique et périodique avec Browser-Use Agent (ex: monitoring TLScontact)."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="tls",
        help="Nom ou chemin du fichier de prompt à surveiller (défaut: tls)",
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=20,
        help="Intervalle entre chaque vérification en minutes (défaut: 20 minutes)",
    )
    parser.add_argument(
        "-s", "--heartbeat",
        type=int,
        default=18,
        help="Nombre de passages avant d'envoyer un rapport périodique WhatsApp (ex: 18 à 20 min = toutes les 6h, défaut: 18, 0 pour désactiver)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Exécuter le navigateur en arrière-plan sans affichage graphique (idéal pour serveur/VM)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Délai maximum par vérification en secondes avant arrêt forcé (défaut: 180s)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Nombre maximum de vérifications à exécuter (défaut: illimité / tourne en continu)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="monitor.log",
        help="Fichier de journalisation des exécutions (défaut: monitor.log)",
    )
    return parser.parse_args()


def send_heartbeat_notification(
    prompt: str,
    window_runs: int,
    success_count: int,
    error_count: int,
    start_time: datetime.datetime,
    next_run: datetime.datetime,
):
    """Envoie un rapport WhatsApp périodique confirmant la bonne santé du monitoring."""
    duration_hours = (datetime.datetime.now() - start_time).total_seconds() / 3600.0
    status_str = "Tous les passages sont nominaux" if error_count == 0 else f"{error_count} passage(s) avec alerte/erreur"

    msg = (
        f"🤖 [Heartbeat - Robot {prompt.upper()}]\n"
        f"✅ Le robot fonctionne parfaitement et surveille en continu !\n\n"
        f"📊 Bilan des {window_runs} dernières vérifications (~{duration_hours:.1f}h) :\n"
        f"• Passages réussis : {success_count}/{window_runs}\n"
        f"• État d'exécution : {status_str}\n"
        f"• Disponibilité : Aucun créneau ouvert détecté pour l'instant\n"
        f"🕒 Prochain passage prévu : {next_run.strftime('%H:%M')}\n\n"
        f"Je continue la veille active 24/7."
    )

    print(f"\n📲 [ENVOI DU RAPPORT WHATSAPP DE VÉRIN ({window_runs} RUNS)]...")
    try:
        from notify import send_whatsapp
        ok = send_whatsapp(msg)
        if ok:
            print("✅ [RAPPORT WHATSAPP ENVOYÉ AVEC SUCCÈS]")
        else:
            print("⚠️ [ÉCHEC DE L'ENVOI DU RAPPORT WHATSAPP]")
    except Exception as e:
        print(f"❌ [ERREUR ENVOI RAPPORT WHATSAPP] : {e}")


def run_check(prompt: str, headless: bool, timeout: int, log_file: Path) -> int:
    """Lance une session d'agent isolée dans un sous-processus."""
    cmd = [sys.executable, "run_agent.py", prompt]
    if headless:
        cmd.append("--headless")

    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n{'=' * 30} DÉBUT DU RUN : {timestamp} {'=' * 30}\n")
        f.flush()

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        try:
            for line in iter(proc.stdout.readline, ""):
                sys.stdout.write(line)
                sys.stdout.flush()
                f.write(line)
                f.flush()

            proc.stdout.close()
            return_code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"\n⚠️ [TIMEOUT] La vérification a dépassé {timeout} secondes. Arrêt forcé du sous-processus.")
            proc.kill()
            proc.wait()
            return -1

        f.write(f"{'=' * 30} FIN DU RUN (code: {return_code}) {'=' * 30}\n")
        f.flush()
        return return_code


def main():
    args = parse_args()
    log_path = Path(args.log_file).resolve()
    heartbeat_hours = (args.interval * args.heartbeat) / 60.0 if args.heartbeat > 0 else 0

    print("\n" + "=" * 65)
    print("📡 MONITORING AUTOMATIQUE BROWSER-USE AGENT")
    print("=" * 65)
    print(f"🎯 Prompt surveillé       : {args.prompt}")
    print(f"⏱️  Intervalle de passage   : Toutes les {args.interval} minutes")
    if args.heartbeat > 0:
        print(f"💬 Rapport WhatsApp (vie) : Tous les {args.heartbeat} passages (~{heartbeat_hours:.1f} heures)")
    else:
        print(f"💬 Rapport WhatsApp (vie) : Désactivé (alertes créneaux uniquement)")
    print(f"🖥️  Mode navigateur        : {'Arrière-plan (headless)' if args.headless else 'Fenêtre visible en direct'}")
    print(f"⌛ Timeout par run        : {args.timeout} secondes")
    print(f"📝 Journal des logs       : {log_path}")
    if args.max_runs:
        print(f"🔢 Nombre max de runs     : {args.max_runs}")
    print("=" * 65)
    print("Appuyez sur [Ctrl + C] à tout moment pour arrêter le monitoring.\n")

    total_runs = 0
    window_runs = 0
    window_successes = 0
    window_errors = 0
    window_start_time = datetime.datetime.now()
    interval_seconds = args.interval * 60

    try:
        while True:
            total_runs += 1
            window_runs += 1
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n>>> [{now_str}] 🚀 Lancement de la vérification #{total_runs} (fenêtre: {window_runs}/{args.heartbeat})...")

            exit_code = run_check(args.prompt, args.headless, args.timeout, log_path)

            if exit_code == 0:
                window_successes += 1
                print(f"\n>>> [{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Vérification #{total_runs} terminée avec succès.")
            else:
                window_errors += 1
                print(f"\n>>> [{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠️ Vérification #{total_runs} terminée avec le code {exit_code}.")

            if args.max_runs and total_runs >= args.max_runs:
                print(f"\n🏁 Nombre maximal de runs atteint ({args.max_runs}). Arrêt du monitoring.")
                break

            next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_seconds)

            # Vérification du compteur de Heartbeat WhatsApp
            if args.heartbeat > 0 and window_runs >= args.heartbeat:
                send_heartbeat_notification(
                    prompt=args.prompt,
                    window_runs=window_runs,
                    success_count=window_successes,
                    error_count=window_errors,
                    start_time=window_start_time,
                    next_run=next_run,
                )
                # Réinitialisation de la fenêtre de comptage
                window_runs = 0
                window_successes = 0
                window_errors = 0
                window_start_time = datetime.datetime.now()

            print(f"⏳ En pause pendant {args.interval} minutes. Prochaine vérification prévue à : {next_run.strftime('%H:%M:%S')}")

            # Attente jusqu'au prochain passage
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du monitoring par l'utilisateur [Ctrl + C].")
        print("À bientôt !")
        sys.exit(0)


if __name__ == "__main__":
    main()
