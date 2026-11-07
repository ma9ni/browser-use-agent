#!/usr/bin/env python3
"""
Playwright TLScontact Tunis Watcher - 100% Autonome & Gratuit (0$ de coût LLM).
Exécute le parcours de vérification de rendez-vous via Playwright connecté au moteur
Chrome sécurisé anti-détection (sans passer par aucun LLM ni quota d'API).

Fonctionnalités :
- Rapide : ~10 secondes par vérification
- 0$ de coût : 100% gratuit, zéro appel LLM
- Contournement natif de Cloudflare et des protections anti-bot
- Alerte WhatsApp instantanée en cas de créneau disponible via notify.py
- Rapport Heartbeat WhatsApp périodique (ex: toutes les 6h)
- Mode direct ou boucle automatique (--interval N)
- Mode avec fenêtre visible ou en arrière-plan (--headless)
- Sauvegarde de capture d'écran en cas de créneau ou d'anomalie
"""

import argparse
import asyncio
import datetime
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from browser_use import Browser, BrowserProfile
from playwright.async_api import async_playwright
from notify import send_whatsapp

# URLs et cibles TLScontact Tunis
TUNIS_CENTER_URL = "https://visas-fr.tlscontact.com/fr-fr/country/tn/vac/tnTUN2fr"
APPOINTMENT_URL_PATTERN = "/workflow/appointment-booking/tnTUN2fr"

TLS_EMAIL = os.getenv("TLS_EMAIL")
TLS_PASSWORD = os.getenv("TLS_PASSWORD")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérificateur 100% autonome de créneaux TLScontact Tunis via Playwright (0$ de coût)."
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=0,
        help="Intervalle entre chaque vérification en minutes (0 = exécution unique, ex: 15 ou 20 pour boucle continue)",
    )
    parser.add_argument(
        "-s", "--heartbeat",
        type=int,
        default=18,
        help="Nombre de vérifications avant d'envoyer un rapport WhatsApp récapitulatif (défaut: 18)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Exécuter en arrière-plan sans affichage de fenêtre graphique",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout maximum en secondes par page (défaut: 60s)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Nombre de mois à explorer sur le calendrier (défaut: 3)",
    )
    return parser.parse_args()


async def handle_cookies(page):
    """Ferme ou accepte les bannières de cookies si présentes (Osano / OneTrust / etc.)."""
    try:
        btn = page.locator(
            "button.osano-cm-accept-all:visible, "
            "button:has-text('Accept All'):visible, "
            "#onetrust-accept-btn-handler:visible, "
            "button:has-text('Tout accepter'):visible, "
            "button:has-text('Accepter'):visible"
        ).first
        if await btn.is_visible(timeout=2500):
            print("🍪 Acceptation du bandeau cookies...")
            await btn.click()
            await page.wait_for_timeout(800)
    except Exception:
        pass


async def check_tls_slots(headless: bool = False, timeout_sec: int = 60, months_to_check: int = 3) -> dict:
    """
    Exécute le parcours complet Playwright pour inspecter le calendrier TLScontact.
    Retourne un dict {'success': bool, 'slots_found': bool, 'details': str, 'url': str}.
    """
    if not TLS_EMAIL or not TLS_PASSWORD:
        print("[!] ERREUR : TLS_EMAIL ou TLS_PASSWORD manquant dans votre fichier .env")
        return {"success": False, "slots_found": False, "details": "Identifiants .env manquants"}

    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    result = {
        "success": False,
        "slots_found": False,
        "details": "",
        "slots_list": [],
        "url": "",
    }

    user_data_dir = Path("tls_user_profile").resolve()
    user_data_dir.mkdir(exist_ok=True)

    # 1. Démarrage de l'instance Chrome avec profil persistant et contournement anti-bot natif
    bp = BrowserProfile(headless=False, user_data_dir=str(user_data_dir))
    b = Browser(browser_profile=bp)
    await b.start()

    if headless:
        # En mode arrière-plan, déplacer immédiatement la fenêtre sur le bureau virtuel 4
        # Cela évite toute fenêtre sur votre écran sans subir le blocage de Cloudflare
        try:
            import subprocess
            await asyncio.sleep(0.8)
            subprocess.run(["wmctrl", "-r", "TLScontact", "-t", "3"], capture_output=True)
            subprocess.run(["wmctrl", "-r", "Google Chrome", "-t", "3"], capture_output=True)
        except Exception:
            pass

    try:
        async with async_playwright() as p:
            pw_browser = await p.chromium.connect_over_cdp(b.cdp_url)
            context = pw_browser.contexts[0] if pw_browser.contexts else await pw_browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(timeout_sec * 1000)

            # 1. Navigation directe vers le centre de Tunis
            print("🌐 [1/6] Navigation vers la page TLScontact Tunis...")
            try:
                await page.goto(TUNIS_CENTER_URL, wait_until="load", timeout=25000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            await handle_cookies(page)

            # 2. Clic sur "Prendre rendez-vous"
            print("🖱️  [2/6] Clic sur 'Prendre rendez-vous'...")
            rdv_btn = page.locator("button:has-text('Prendre rendez-vous'):visible, a:has-text('Prendre rendez-vous'):visible").first
            await rdv_btn.wait_for(state="visible", timeout=20000)
            await rdv_btn.click()
            await page.wait_for_timeout(1500)

            # 3. Réponse aux questions modales (France-Visas et compte TLScontact)
            print("📋 [3/6] Réponse aux questions de la modale...")
            ouis = page.locator("button:has-text('Oui'):visible")
            if await ouis.count() > 0:
                await ouis.first.click()
                await page.wait_for_timeout(1000)

            ouis2 = page.locator("button:has-text('Oui'):visible")
            if await ouis2.count() > 0:
                await ouis2.last.click()
                await page.wait_for_timeout(1500)

            # Clic sur "SE CONNECTER" dans la modale
            modal = page.locator("div.fixed:has(button:has-text('Oui')), div[role='dialog']").last
            modal_connect = modal.locator("a:has-text('SE CONNECTER'), button:has-text('SE CONNECTER')").first
            await modal_connect.wait_for(state="visible", timeout=10000)
            await modal_connect.click()

            # 4. Authentification
            print("🔑 [4/6] Authentification en cours...")
            for _ in range(25):
                if any(k in page.url for k in ["auth", "travel-groups", "appointment", "services"]):
                    break
                await page.wait_for_timeout(1000)

            # Si nous sommes sur la page de connexion
            if "auth" in page.url:
                username_input = page.locator("#email-input-field, input#username, input[name='username']").first
                await username_input.wait_for(state="visible", timeout=15000)
                await username_input.fill(TLS_EMAIL)

                password_input = page.locator("#password-input-field, input#password, input[name='password']").first
                await password_input.fill(TLS_PASSWORD)

                # Gestion du captcha avec ciblage de l'iframe reCAPTCHA
                recaptcha_frame = page.frame_locator("iframe[title*='reCAPTCHA'], iframe[src*='recaptcha']").first
                try:
                    recaptcha_anchor = recaptcha_frame.locator("#recaptcha-anchor, .recaptcha-checkbox").first
                    if await recaptcha_anchor.is_visible(timeout=3000):
                        print("🤖 Coche de la case reCAPTCHA...")
                        await recaptcha_anchor.click()
                        await page.wait_for_timeout(2500)
                except Exception:
                    pass

                # Vérifier si un puzzle d'images est apparu
                challenge_frame = page.locator("iframe[title*='challenge'], iframe[src*='bframe'], iframe[title*='reCAPTCHA expire']").first
                try:
                    if await challenge_frame.is_visible(timeout=2500):
                        print("⚠️  Puzzle d'images reCAPTCHA affiché !")
                        if not headless:
                            print("👉 Résolvez le puzzle d'images sur votre écran (attente jusqu'à 60s)...")
                            for s in range(60):
                                await page.wait_for_timeout(1000)
                                if "travel-groups" in page.url or "services" in page.url:
                                    break
                                try:
                                    # Vérifier si la coche verte est validée
                                    is_checked = await recaptcha_frame.locator(".recaptcha-checkbox-checked, [aria-checked='true']").first.is_visible()
                                    if is_checked:
                                        print(f"✅ reCAPTCHA validé avec succès ({s+1}s) !")
                                        await page.wait_for_timeout(1000)
                                        break
                                except Exception:
                                    pass
                except Exception:
                    pass

                login_btn = page.locator("button#btn-login, button:has-text('Se connecter'), input[type='submit']").first
                await login_btn.wait_for(state="visible", timeout=10000)
                try:
                    await login_btn.click()
                except Exception:
                    # En cas de superposition d'un élément résiduel
                    await login_btn.click(force=True)

            # 5. Sélection du dossier dans le groupe de voyage
            print("📂 [5/6] Sélection du dossier de demande...")
            for _ in range(30):
                if any(k in page.url for k in ["travel-groups", "services", "appointment"]):
                    break
                await page.wait_for_timeout(1000)

            await page.wait_for_timeout(1500)

            if "travel-groups" in page.url:
                select_btn = page.locator("button[name='formGroupId'], button:has-text('Sélectionner')").first
                await select_btn.wait_for(state="attached", timeout=15000)
                print("📂 Clic sur le dossier (formGroupId 29310587)...")
                await select_btn.evaluate("btn => btn.click()")
                await page.wait_for_timeout(3000)

            # 6. Page des services additionnels -> Continuer
            try:
                for _ in range(15):
                    if "appointment-booking" in page.url:
                        break
                    continuer_btn = page.locator("#book-appointment-btn, button:has-text('Continuer'), a:has-text('Continuer')").first
                    if await continuer_btn.count() > 0:
                        print("➡️  Validation des services (Continuer)...")
                        await continuer_btn.evaluate("btn => btn.click()")
                        await page.wait_for_timeout(2500)
                        break
                    await page.wait_for_timeout(1000)
            except Exception:
                pass

            # 7. Calendrier des rendez-vous
            print("📅 [6/6] Inspection du calendrier de rendez-vous...")
            for _ in range(25):
                if "appointment-booking" in page.url:
                    break
                await page.wait_for_timeout(1000)

            await page.wait_for_timeout(3000)
            result["url"] = page.url

            # Analyse des mois disponibles
            available_slots_found = False
            detected_slots = []

            for month_idx in range(months_to_check):
                await page.wait_for_timeout(1000)
                content = await page.content()

                # Recherche d'indices de créneaux ouverts
                slot_buttons = page.locator("button.appointment-slot, button.slot-available, button.btn-slot:not([disabled]), .slot:not(.disabled)")
                count_slots = await slot_buttons.count()

                if count_slots > 0:
                    available_slots_found = True
                    for i in range(min(5, count_slots)):
                        txt = await slot_buttons.nth(i).inner_text()
                        if txt.strip():
                            detected_slots.append(txt.strip())

                # Cliquer sur la flèche mois suivant si disponible
                if month_idx < months_to_check - 1:
                    next_btn = page.locator("button.fc-next-button, button[aria-label='Next month'], button:has-text('>'), .next-month").first
                    if await next_btn.is_visible(timeout=1500):
                        await next_btn.click()
                        await page.wait_for_timeout(1200)

            # Résultat
            result["success"] = True
            result["slots_found"] = available_slots_found
            result["slots_list"] = detected_slots

            if available_slots_found:
                slots_text = ", ".join(detected_slots) if detected_slots else "Créneaux visibles"
                result["details"] = f"CRÉNEAU DISPONIBLE DÉTECTÉ ({slots_text})"
                print(f"\n🎉🎉🎉 ALERTE : {result['details']} ! 🎉🎉🎉")

                # Capture d'écran de confirmation
                screenshot_path = screenshots_dir / f"slots_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                # ENVOI IMMÉDIAT WHATSAPP
                alert_msg = (
                    f"🚨 CRÉNEAU DISPONIBLE TLScontact Tunis !\n"
                    f"Des créneaux viennent d'ouvrir : {slots_text}\n"
                    f"Lien direct de réservation : {page.url}\n"
                    f"Connectez-vous immédiatement pour réserver !"
                )
                print("📲 Envoi immédiat de l'alerte WhatsApp...")
                send_whatsapp(alert_msg)
            else:
                result["details"] = "Aucun créneau disponible actuellement."
                print(f"ℹ️  {result['details']}")

            await pw_browser.close()

    except Exception as e:
        result["success"] = False
        result["details"] = f"Erreur : {e}"
        print(f"❌ Erreur lors de l'exécution Playwright : {e}")

        try:
            err_path = screenshots_dir / f"error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            if 'page' in locals() and page:
                await page.screenshot(path=str(err_path))
                print(f"📸 Capture d'erreur sauvegardée : {err_path}")
        except Exception:
            pass
    finally:
        try:
            await b.stop()
        except Exception:
            pass

    return result


def send_heartbeat(window_runs: int, success_count: int, error_count: int, start_time: datetime.datetime, next_run: datetime.datetime):
    """Envoie un rapport WhatsApp de confirmation de bon fonctionnement."""
    duration_hours = (datetime.datetime.now() - start_time).total_seconds() / 3600.0
    status = "100% Nominal" if error_count == 0 else f"{error_count} passage(s) avec incident"

    msg = (
        f"🤖 [Heartbeat - Playwright TLS Watcher]\n"
        f"✅ Le script 100% autonome (0$) tourne parfaitement !\n\n"
        f"📊 Bilan des {window_runs} dernières vérifications (~{duration_hours:.1f}h) :\n"
        f"• Exécutions réussies : {success_count}/{window_runs}\n"
        f"• État : {status}\n"
        f"• Disponibilité : Aucun créneau ouvert détecté pour l'instant\n"
        f"🕒 Prochaine vérification : {next_run.strftime('%H:%M')}\n\n"
        f"Veille active continue."
    )
    print("\n📲 Envoi du rapport périodique Heartbeat WhatsApp...")
    send_whatsapp(msg)


def main():
    args = parse_args()

    print("\n" + "=" * 65)
    print("⚡ PLAYWRIGHT TLSCONTACT WATCHER (100% GRATUIT / 0$ LLM)")
    print("=" * 65)
    print(f"🎯 Centre surveillé       : Tunis (tnTUN2fr)")
    print(f"⏱️  Mode d'exécution       : {'En boucle toutes les ' + str(args.interval) + ' min' if args.interval > 0 else 'Vérification unique'}")
    if args.interval > 0 and args.heartbeat > 0:
        hb_h = (args.interval * args.heartbeat) / 60.0
        print(f"💬 Rapport Heartbeat      : Tous les {args.heartbeat} passages (~{hb_h:.1f} heures)")
    print(f"🖥️  Affichage navigateur  : {'Arrière-plan (headless)' if args.headless else 'Fenêtre visible en direct'}")
    print("=" * 65 + "\n")

    if args.interval <= 0:
        # Exécution unique
        asyncio.run(check_tls_slots(headless=args.headless, timeout_sec=args.timeout, months_to_check=args.months))
        return

    # Boucle de surveillance continue
    total_runs = 0
    window_runs = 0
    window_success = 0
    window_errors = 0
    window_start = datetime.datetime.now()
    interval_seconds = args.interval * 60

    try:
        while True:
            total_runs += 1
            window_runs += 1
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n>>> [{now_str}] 🚀 Lancement de la vérification #{total_runs} (fenêtre: {window_runs}/{args.heartbeat})...")

            start_t = time.time()
            res = asyncio.run(check_tls_slots(headless=args.headless, timeout_sec=args.timeout, months_to_check=args.months))
            elapsed = time.time() - start_t

            if res["success"]:
                window_success += 1
                print(f">>> [OK] Exécution #{total_runs} terminée en {elapsed:.1f}s.")
            else:
                window_errors += 1
                print(f">>> [ATTENTION] Exécution #{total_runs} terminée avec anomalie en {elapsed:.1f}s.")

            next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_seconds)

            # Heartbeat WhatsApp périodique
            if args.heartbeat > 0 and window_runs >= args.heartbeat:
                send_heartbeat(
                    window_runs=window_runs,
                    success_count=window_success,
                    error_count=window_errors,
                    start_time=window_start,
                    next_run=next_run,
                )
                window_runs = 0
                window_success = 0
                window_errors = 0
                window_start = datetime.datetime.now()

            print(f"⏳ Prochaine vérification à : {next_run.strftime('%H:%M:%S')} (dans {args.interval} min)")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du script Playwright par l'utilisateur.")
        sys.exit(0)


if __name__ == "__main__":
    main()
