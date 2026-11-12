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
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from core.config import (
    TLS_TUNIS_URL,
    TLS_EMAIL,
    TLS_PASSWORD,
    TLS_USER_PROFILE_DIR,
    SCREENSHOTS_DIR,
)
from core.browser import BrowserManager
from core.recaptcha import solve_recaptcha
from core.notifier import (
    notify_slot_detected,
    notify_critical_error,
    notify_recovery,
    send_heartbeat_report,
)


class TLSWatcherError(RuntimeError):
    """Exception de base qualifiée pour les anomalies du watcher TLScontact."""

    def __init__(self, error_type: str, message: str, url: str = ""):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.url = url


class TLSContactWatcher:
    """Agent autonome de surveillance des rendez-vous TLScontact Tunis."""

    def __init__(
        self,
        headless: bool = False,
        timeout_sec: int = 60,
        months_to_check: int = 3,
        alert_on_critical: bool = True,
    ):
        self.headless = headless
        self.timeout_sec = timeout_sec
        self.months_to_check = months_to_check
        self.alert_on_critical = alert_on_critical

    async def detect_anti_bot_block(self, page) -> str | None:
        """Détecte si la page est bloquée par un écran Cloudflare Turnstile ou similaire."""
        try:
            title = (await page.title()).lower()
            body_text = await page.locator("body").inner_text(timeout=2000)
        except Exception:
            return None

        combined = f"{title}\n{body_text.lower()}"
        if "sorry, you have been blocked" in combined or "you are unable to access" in combined:
            return "Accès refusé par Cloudflare avant l'authentification ; le reCAPTCHA n'a pas été atteint."

        cloudflare_markers = [
            "performing security verification",
            "verify you are human",
            "vérification de sécurité",
            "vérifiez que vous êtes humain",
            "just a moment...",
            "un instant...",
        ]
        for marker in cloudflare_markers:
            if marker in combined:
                return "Page bloquée par la vérification anti-bot Cloudflare (Verify you are human)."
        return None

    async def wait_for_cloudflare(self, page, timeout_sec: int = 30) -> None:
        """Laisse une vérification transitoire se terminer avant de signaler le blocage."""
        block = await self.detect_anti_bot_block(page)
        if not block:
            return
        if block.startswith("Accès refusé"):
            raise TLSWatcherError("CLOUDFLARE_BLOCK", block, page.url)

        print(f"⏳ Vérification Cloudflare en cours (attente maximale : {timeout_sec}s)...")
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            await page.wait_for_timeout(2000)
            block = await self.detect_anti_bot_block(page)
            if not block:
                print("✅ Vérification Cloudflare terminée.")
                return
            if block.startswith("Accès refusé"):
                break
        raise TLSWatcherError("CLOUDFLARE_BLOCK", block, page.url)

    async def detect_missing_dossier(self, page) -> str | None:
        """
        Vérifie sur la page /travel-groups si le dossier a été supprimé ou retiré
        ('Aucune demande créée' / 'No application created').
        """
        try:
            body_text = await page.locator("body").inner_text(timeout=3000)
        except Exception:
            return None

        empty_markers = [
            "aucune demande créée",
            "aucune demande creee",
            "no application created",
            "no applications found",
        ]
        lower_text = body_text.lower()
        for marker in empty_markers:
            if marker in lower_text:
                return (
                    "La page 'Gestionnaire des demandes' affiche « Aucune demande créée ». "
                    "Le dossier (ex: Latifa NABLI) a été retiré, supprimé ou a expiré sur TLScontact."
                )
        return None

    async def get_dossier_summary(self, page) -> str:
        """Extrait le nom et le numéro de groupe du dossier affiché sur /travel-groups."""
        try:
            row_text = await page.locator("main, .tls-table, table, [class*='group'], body").first.inner_text(timeout=2000)
            lines = [line.strip() for line in row_text.splitlines() if line.strip()]
            for i, line in enumerate(lines):
                if "29310587" in line or "nabli" in line.lower() or "latifa" in line.lower():
                    snippet = " | ".join(lines[max(0, i - 1): min(len(lines), i + 3)])
                    return snippet[:160]
        except Exception:
            pass
        return "Dossier détecté"

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

    async def check_once(self, send_critical_whatsapp: bool | None = None) -> dict:
        """Exécute une vérification unique du calendrier TLScontact avec diagnostic strict."""
        should_alert = self.alert_on_critical if send_critical_whatsapp is None else send_critical_whatsapp

        if not TLS_EMAIL or not TLS_PASSWORD:
            msg = "Identifiants TLS_EMAIL ou TLS_PASSWORD manquants dans .env"
            print(f"[!] ERREUR : {msg}")
            return {
                "success": False,
                "slots_found": False,
                "error_type": "CONFIG_ERROR",
                "details": msg,
                "slots_list": [],
                "url": "",
            }

        result = {
            "success": False,
            "slots_found": False,
            "error_type": None,
            "details": "",
            "dossier_info": "",
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

            await self.wait_for_cloudflare(page)

            await self.handle_cookies(page)

            # 2. Clic sur "Prendre rendez-vous"
            print("🖱️  [2/6] Clic sur 'Prendre rendez-vous'...")
            rdv_btn = page.locator("button:has-text('Prendre rendez-vous'):visible, a:has-text('Prendre rendez-vous'):visible").first
            try:
                await rdv_btn.wait_for(state="visible", timeout=20000)
            except Exception as e:
                await self.wait_for_cloudflare(page)
                try:
                    await rdv_btn.wait_for(state="visible", timeout=5000)
                except PlaywrightTimeoutError:
                    raise TLSWatcherError(
                        "HOME_LOAD_ERROR",
                        f"Bouton 'Prendre rendez-vous' introuvable sur la page d'accueil (URL: {page.url}).",
                        page.url,
                    ) from e

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
            reached_next = False
            for _ in range(25):
                if any(k in page.url for k in ["auth", "travel-groups", "appointment", "services"]):
                    reached_next = True
                    break
                await page.wait_for_timeout(1000)

            if not reached_next:
                cf_block = await self.detect_anti_bot_block(page)
                if cf_block:
                    raise TLSWatcherError("CLOUDFLARE_BLOCK", cf_block, page.url)
                raise TLSWatcherError(
                    "MODAL_REDIRECT_ERROR",
                    f"La redirection après 'SE CONNECTER' a échoué (URL: {page.url}).",
                    page.url,
                )

            if "auth" in page.url:
                username_input = page.locator("#email-input-field, input#username, input[name='username']").first
                await username_input.wait_for(state="visible", timeout=15000)
                await username_input.fill(TLS_EMAIL)

                password_input = page.locator("#password-input-field, input#password, input[name='password']").first
                await password_input.fill(TLS_PASSWORD)

                # Le solveur agit sur cette même page et valide la case ou le puzzle si nécessaire.
                recaptcha_frame = page.frame_locator("iframe[title*='reCAPTCHA'], iframe[src*='recaptcha']").first
                recaptcha_anchor = recaptcha_frame.locator("#recaptcha-anchor, .recaptcha-checkbox").first
                try:
                    await recaptcha_anchor.wait_for(state="visible", timeout=5000)
                except PlaywrightTimeoutError:
                    pass
                else:
                    print("🤖 Validation reCAPTCHA avec reCognizer...")
                    try:
                        await solve_recaptcha(page)
                    except Exception as e:
                        raise TLSWatcherError(
                            "RECAPTCHA_SOLVE_FAILED",
                            f"reCognizer n'a pas résolu le reCAPTCHA : {type(e).__name__}: {e}",
                            page.url,
                        ) from e
                    print("✅ reCAPTCHA validé ; vérification de la connexion après soumission...")

                login_btn = page.locator("button#btn-login, button:has-text('Se connecter'), input[type='submit']").first
                await login_btn.wait_for(state="visible", timeout=10000)
                try:
                    await login_btn.click()
                except Exception:
                    await login_btn.click(force=True)

            # 5. Sélection du dossier dans le groupe de voyage
            print("📂 [5/6] Sélection du dossier de demande...")
            reached_account = False
            for _ in range(30):
                if any(k in page.url for k in ["travel-groups", "services", "appointment"]):
                    reached_account = True
                    break
                await page.wait_for_timeout(1000)

            if not reached_account:
                cf_block = await self.detect_anti_bot_block(page)
                if cf_block:
                    raise TLSWatcherError("CLOUDFLARE_BLOCK", cf_block, page.url)
                if "auth" in page.url:
                    raise TLSWatcherError(
                        "AUTH_FAILED",
                        "Authentification bloquée sur la page de login (identifiants refusés ou reCAPTCHA actif).",
                        page.url,
                    )
                raise TLSWatcherError(
                    "ACCOUNT_PAGE_NOT_REACHED",
                    f"Impossible d'atteindre la page des dossiers après connexion (URL: {page.url}).",
                    page.url,
                )

            await page.wait_for_timeout(2000)

            if "travel-groups" in page.url:
                select_btn = page.locator("button[name='formGroupId'], button:has-text('Sélectionner')").first

                # Attente active : soit le bouton 'Sélectionner' apparaît, soit 'Aucune demande créée' est détecté
                dossier_ready = False
                for _ in range(15):
                    if await select_btn.count() > 0:
                        dossier_ready = True
                        break
                    missing_msg = await self.detect_missing_dossier(page)
                    if missing_msg:
                        raise TLSWatcherError("DOSSIER_SUPPRIME", missing_msg, page.url)
                    await page.wait_for_timeout(1000)

                if not dossier_ready:
                    missing_msg = await self.detect_missing_dossier(page)
                    if missing_msg:
                        raise TLSWatcherError("DOSSIER_SUPPRIME", missing_msg, page.url)
                    raise TLSWatcherError(
                        "DOSSIER_INTROUVABLE",
                        "Aucun bouton 'Sélectionner' trouvé sur la page Gestionnaire des demandes (/travel-groups).",
                        page.url,
                    )

                dossier_summary = await self.get_dossier_summary(page)
                result["dossier_info"] = dossier_summary
                print(f"📂 Dossier trouvé : {dossier_summary}")
                print("📂 Clic sur le bouton 'Sélectionner' du dossier...")
                await select_btn.evaluate("btn => btn.click()")
                await page.wait_for_timeout(3000)

            # 6. Services additionnels -> Continuer
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

            # 7. Calendrier des rendez-vous (Validation stricte de l'URL et de la page)
            print("📅 [6/6] Inspection du calendrier de rendez-vous...")
            reached_calendar = False
            for _ in range(25):
                if "appointment-booking" in page.url:
                    reached_calendar = True
                    break
                await page.wait_for_timeout(1000)

            if not reached_calendar or "appointment-booking" not in page.url:
                missing_msg = await self.detect_missing_dossier(page)
                if missing_msg:
                    raise TLSWatcherError("DOSSIER_SUPPRIME", missing_msg, page.url)
                raise TLSWatcherError(
                    "CALENDAR_NOT_REACHED",
                    f"La page du calendrier des rendez-vous n'a pas été atteinte (URL finale: {page.url}).",
                    page.url,
                )

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
                result["details"] = "Aucun créneau disponible actuellement (calendrier vérifié)."
                print(f"ℹ️  {result['details']}")

        except TLSWatcherError as e:
            result["success"] = False
            result["error_type"] = e.error_type
            result["details"] = f"[{e.error_type}] {e.message}"
            result["url"] = e.url or (page.url if page else "")
            print(f"❌ Anomalie détectée ({e.error_type}) : {e.message}")

            try:
                prefix = "missing_dossier" if e.error_type == "DOSSIER_SUPPRIME" else "error"
                err_path = SCREENSHOTS_DIR / f"{prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                if page:
                    await page.screenshot(path=str(err_path), full_page=True)
                    print(f"📸 Capture d'anomalie sauvegardée : {err_path}")
            except Exception:
                pass

            if should_alert and e.error_type in ("DOSSIER_SUPPRIME", "DOSSIER_INTROUVABLE"):
                print("📲 Envoi immédiat d'une alerte critique WhatsApp (dossier manquant)...")
                notify_critical_error(
                    title="DOSSIER TLSCONTACT INTROUVABLE OU SUPPRIMÉ !",
                    error_details=e.message,
                    current_url=result["url"],
                    action_required="Connectez-vous sur TLScontact pour vérifier ou recréer la demande.",
                )

        except Exception as e:
            result["success"] = False
            result["error_type"] = "UNEXPECTED_ERROR"
            result["details"] = f"Erreur inattendue : {e}"
            result["url"] = page.url if page else ""
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

    def start_monitoring(
        self,
        interval_minutes: int = 15,
        heartbeat_frequency: int = 24,
        max_consecutive_error_alerts: int = 3,
    ):
        """Lance la boucle de surveillance continue avec alertes d'anomalies et rapports Heartbeat."""
        total_runs = 0
        window_runs = 0
        window_success = 0
        window_errors = 0
        consecutive_errors = 0
        consecutive_missing_dossier = 0
        last_error_details = ""
        window_start = datetime.datetime.now()
        interval_seconds = interval_minutes * 60

        try:
            while True:
                total_runs += 1
                window_runs += 1
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n>>> [{now_str}] 🚀 Lancement de la vérification #{total_runs} (fenêtre: {window_runs}/{heartbeat_frequency})...")

                start_t = time.time()
                # En mode boucle, on gère l'alerte WhatsApp ci-dessous pour éviter le spam
                res = asyncio.run(self.check_once(send_critical_whatsapp=False))
                elapsed = time.time() - start_t

                if res["success"]:
                    if consecutive_errors >= max_consecutive_error_alerts:
                        notify_recovery(
                            agent_name="Playwright TLS Watcher",
                            previous_errors=consecutive_errors,
                            details=res.get("dossier_info", ""),
                        )
                    window_success += 1
                    consecutive_errors = 0
                    consecutive_missing_dossier = 0
                    print(f">>> [OK] Exécution #{total_runs} terminée en {elapsed:.1f}s.")
                else:
                    window_errors += 1
                    consecutive_errors += 1
                    last_error_details = res.get("details", "Erreur inconnue")
                    error_type = res.get("error_type") or "ERROR"
                    print(f">>> [ATTENTION] Exécution #{total_runs} en échec ({error_type}) en {elapsed:.1f}s : {last_error_details}")

                    # Cas 1 : Dossier supprimé ou introuvable -> Alerte immédiate dès le 1er constat !
                    if error_type in ("DOSSIER_SUPPRIME", "DOSSIER_INTROUVABLE"):
                        consecutive_missing_dossier += 1
                        if consecutive_missing_dossier == 1:
                            print("📲 [ALERTE CRITIQUE] Envoi WhatsApp immédiat : Dossier absent sur TLScontact !")
                            notify_critical_error(
                                title="DOSSIER TLSCONTACT SUPPRIMÉ OU INTROUVABLE !",
                                error_details=res.get("details", ""),
                                current_url=res.get("url", ""),
                                action_required=(
                                    "Le robot a constaté qu'aucun dossier n'est présent sur le compte. "
                                    "Nouvelle vérification de confirmation au prochain passage avant arrêt automatique."
                                ),
                            )
                        elif consecutive_missing_dossier >= 2:
                            print("🛑 [ARRÊT SÉCURITÉ] Absence du dossier confirmée 2 fois de suite. Arrêt du monitoring.")
                            notify_critical_error(
                                title="ARRÊT DE LA SURVEILLANCE TLSCONTACT (DOSSIER ABSENT CONFIRMÉ)",
                                error_details=(
                                    "L'absence du dossier ('Aucune demande créée') a été confirmée sur 2 vérifications consécutives. "
                                    "La surveillance automatique s'est arrêtée pour ne pas tourner à vide."
                                ),
                                current_url=res.get("url", ""),
                                action_required="Recréez le dossier sur France-Visas / TLScontact puis relancez le watcher.",
                            )
                            sys.exit(2)
                    else:
                        consecutive_missing_dossier = 0

                        # Cas 2 : Échecs techniques consécutifs (ex: 3 fois de suite, puis tous les 12 passages)
                        if consecutive_errors == max_consecutive_error_alerts or (
                            consecutive_errors > max_consecutive_error_alerts
                            and (consecutive_errors - max_consecutive_error_alerts) % 12 == 0
                        ):
                            print(f"📲 [ALERTE ANOMALIE] {consecutive_errors} échecs consécutifs -> Envoi alerte WhatsApp...")
                            notify_critical_error(
                                title=f"{consecutive_errors} échecs consécutifs sur TLS Watcher",
                                error_details=last_error_details,
                                current_url=res.get("url", ""),
                                action_required=(
                                    "Vérifiez la session navigateur (Cloudflare / reCAPTCHA / identifiants) "
                                    "ou les captures dans screenshots/."
                                ),
                            )

                next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_seconds)

                if heartbeat_frequency > 0 and window_runs >= heartbeat_frequency:
                    send_heartbeat_report(
                        agent_name="Playwright TLS Watcher",
                        window_runs=window_runs,
                        success_count=window_success,
                        error_count=window_errors,
                        start_time=window_start,
                        next_run=next_run,
                        last_error=last_error_details,
                        consecutive_errors=consecutive_errors,
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
