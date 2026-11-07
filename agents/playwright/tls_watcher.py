"""
Playwright Agent: TLScontact Tunis Slot Watcher.
Agent 100% autonome, zéro dollar de coût LLM, spécialisé dans la surveillance
des créneaux de rendez-vous TLScontact pour le centre de Tunis.
"""

import asyncio
import datetime
import sys
import time
from pathlib import Path

from core.config import (
    TLS_TUNIS_URL,
    TLS_EMAIL,
    TLS_PASSWORD,
    TLS_USER_PROFILE_DIR,
    SCREENSHOTS_DIR,
)
from core.browser import BrowserManager
from core.notifier import notify_slot_detected, send_heartbeat_report


class TLSContactWatcher:
    """Agent autonome de surveillance des rendez-vous TLScontact Tunis."""

    def __init__(self, headless: bool = False, timeout_sec: int = 60, months_to_check: int = 3):
        self.headless = headless
        self.timeout_sec = timeout_sec
        self.months_to_check = months_to_check

    async def handle_cookies(self, page):
        """Accepte ou ferme les bannières de cookies si présentes."""
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

    async def check_once(self) -> dict:
        """Exécute une vérification unique du calendrier TLScontact."""
        if not TLS_EMAIL or not TLS_PASSWORD:
            print("[!] ERREUR : TLS_EMAIL ou TLS_PASSWORD manquant dans .env")
            return {"success": False, "slots_found": False, "details": "Identifiants .env manquants"}

        result = {
            "success": False,
            "slots_found": False,
            "details": "",
            "slots_list": [],
            "url": "",
        }

        manager = BrowserManager(user_data_dir=TLS_USER_PROFILE_DIR, headless=self.headless)
        page = None

        try:
            _, page = await manager.start()
            page.set_default_timeout(self.timeout_sec * 1000)

            # 1. Navigation directe vers le centre de Tunis
            print("🌐 [1/6] Navigation vers la page TLScontact Tunis...")
            try:
                await page.goto(TLS_TUNIS_URL, wait_until="load", timeout=25000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            await self.handle_cookies(page)

            # 2. Clic sur "Prendre rendez-vous"
            print("🖱️  [2/6] Clic sur 'Prendre rendez-vous'...")
            rdv_btn = page.locator("button:has-text('Prendre rendez-vous'):visible, a:has-text('Prendre rendez-vous'):visible").first
            await rdv_btn.wait_for(state="visible", timeout=20000)
            await rdv_btn.click()
            await page.wait_for_timeout(1500)

            # 3. Réponse aux questions de la modale
            print("📋 [3/6] Réponse aux questions de la modale...")
            ouis = page.locator("button:has-text('Oui'):visible")
            if await ouis.count() > 0:
                await ouis.first.click()
                await page.wait_for_timeout(1000)

            ouis2 = page.locator("button:has-text('Oui'):visible")
            if await ouis2.count() > 0:
                await ouis2.last.click()
                await page.wait_for_timeout(1500)

            modal = page.locator("div.fixed:has(button:has-text('Oui')), div[role='dialog']").last
            modal_connect = modal.locator("a:has-text('SE CONNECTER'), button:has-text('SE CONNECTER')").first
            await modal_connect.wait_for(state="visible", timeout=10000)
            await modal_connect.click()

            # 4. Authentification (si non connectée)
            print("🔑 [4/6] Authentification en cours...")
            for _ in range(25):
                if any(k in page.url for k in ["auth", "travel-groups", "appointment", "services"]):
                    break
                await page.wait_for_timeout(1000)

            if "auth" in page.url:
                username_input = page.locator("#email-input-field, input#username, input[name='username']").first
                await username_input.wait_for(state="visible", timeout=15000)
                await username_input.fill(TLS_EMAIL)

                password_input = page.locator("#password-input-field, input#password, input[name='password']").first
                await password_input.fill(TLS_PASSWORD)

                # reCAPTCHA
                recaptcha_frame = page.frame_locator("iframe[title*='reCAPTCHA'], iframe[src*='recaptcha']").first
                try:
                    recaptcha_anchor = recaptcha_frame.locator("#recaptcha-anchor, .recaptcha-checkbox").first
                    if await recaptcha_anchor.is_visible(timeout=3000):
                        print("🤖 Coche de la case reCAPTCHA...")
                        await recaptcha_anchor.click()
                        await page.wait_for_timeout(2500)
                except Exception:
                    pass

                challenge_frame = page.locator("iframe[title*='challenge'], iframe[src*='bframe'], iframe[title*='reCAPTCHA expire']").first
                try:
                    if await challenge_frame.is_visible(timeout=2500):
                        print("⚠️  Puzzle d'images reCAPTCHA affiché !")
                        if not self.headless:
                            print("👉 Résolvez le puzzle d'images sur votre écran (attente jusqu'à 60s)...")
                            for s in range(60):
                                await page.wait_for_timeout(1000)
                                if "travel-groups" in page.url or "services" in page.url:
                                    break
                                try:
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

            # 6. Services additionnels -> Continuer
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

            available_slots_found = False
            detected_slots = []

            for month_idx in range(self.months_to_check):
                await page.wait_for_timeout(1000)

                slot_buttons = page.locator("button.appointment-slot, button.slot-available, button.btn-slot:not([disabled]), .slot:not(.disabled)")
                count_slots = await slot_buttons.count()

                if count_slots > 0:
                    available_slots_found = True
                    for i in range(min(5, count_slots)):
                        txt = await slot_buttons.nth(i).inner_text()
                        if txt.strip():
                            detected_slots.append(txt.strip())

                if month_idx < self.months_to_check - 1:
                    next_btn = page.locator("button.fc-next-button, button[aria-label='Next month'], button:has-text('>'), .next-month").first
                    if await next_btn.is_visible(timeout=1500):
                        await next_btn.click()
                        await page.wait_for_timeout(1200)

            result["success"] = True
            result["slots_found"] = available_slots_found
            result["slots_list"] = detected_slots

            if available_slots_found:
                slots_text = ", ".join(detected_slots) if detected_slots else "Créneaux visibles"
                result["details"] = f"CRÉNEAU DISPONIBLE DÉTECTÉ ({slots_text})"
                print(f"\n🎉🎉🎉 ALERTE : {result['details']} ! 🎉🎉🎉")

                screenshot_path = SCREENSHOTS_DIR / f"slots_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                print("📲 Envoi immédiat de l'alerte WhatsApp...")
                notify_slot_detected(center_name="Tunis", slots_text=slots_text, booking_url=page.url)
            else:
                result["details"] = "Aucun créneau disponible actuellement."
                print(f"ℹ️  {result['details']}")

        except Exception as e:
            result["success"] = False
            result["details"] = f"Erreur : {e}"
            print(f"❌ Erreur lors de l'exécution Playwright : {e}")

            try:
                err_path = SCREENSHOTS_DIR / f"error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                if page:
                    await page.screenshot(path=str(err_path))
                    print(f"📸 Capture d'erreur sauvegardée : {err_path}")
            except Exception:
                pass
        finally:
            await manager.stop()

        return result

    def start_monitoring(self, interval_minutes: int = 15, heartbeat_frequency: int = 24):
        """Lance la boucle de surveillance continue avec rapports Heartbeat."""
        total_runs = 0
        window_runs = 0
        window_success = 0
        window_errors = 0
        window_start = datetime.datetime.now()
        interval_seconds = interval_minutes * 60

        try:
            while True:
                total_runs += 1
                window_runs += 1
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n>>> [{now_str}] 🚀 Lancement de la vérification #{total_runs} (fenêtre: {window_runs}/{heartbeat_frequency})...")

                start_t = time.time()
                res = asyncio.run(self.check_once())
                elapsed = time.time() - start_t

                if res["success"]:
                    window_success += 1
                    print(f">>> [OK] Exécution #{total_runs} terminée en {elapsed:.1f}s.")
                else:
                    window_errors += 1
                    print(f">>> [ATTENTION] Exécution #{total_runs} terminée avec anomalie en {elapsed:.1f}s.")

                next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_seconds)

                if heartbeat_frequency > 0 and window_runs >= heartbeat_frequency:
                    send_heartbeat_report(
                        agent_name="Playwright TLS Watcher",
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

                print(f"⏳ Prochaine vérification à : {next_run.strftime('%H:%M:%S')} (dans {interval_minutes} min)")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n🛑 Arrêt de la surveillance par l'utilisateur.")
            sys.exit(0)
