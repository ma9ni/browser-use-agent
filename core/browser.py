"""
Browser Management Module.
Gère le cycle de vie du navigateur Chrome avec contournement natif anti-bot,
profil persistant, et gestion propre de l'arrière-plan sous Linux (Workspaces / Xvfb).
"""

import asyncio
import os
import subprocess
from pathlib import Path
from browser_use import Browser, BrowserProfile
from playwright.async_api import async_playwright, BrowserContext, Page


class BrowserManager:
    """Gestionnaire de session Chrome anti-détection avec support CDP pour Playwright."""

    def __init__(self, user_data_dir: Path | str, headless: bool = False):
        self.user_data_dir = Path(user_data_dir).resolve()
        self.user_data_dir.mkdir(exist_ok=True)
        self.headless = headless
        self.browser_session: Browser | None = None
        self.playwright_instance = None
        self.pw_browser = None

    async def start(self) -> tuple[BrowserContext, Page]:
        """Démarre Chrome anti-détection et connecte Playwright via CDP."""
        extra_args = []
        if self.headless:
            # En mode arrière-plan, éviter le flag --headless standard qui est bloqué par Cloudflare
            # On laisse le rendu GPU complet actif
            pass

        bp = BrowserProfile(headless=False, user_data_dir=str(self.user_data_dir), args=extra_args)
        self.browser_session = Browser(browser_profile=bp)
        await self.browser_session.start()

        if self.headless:
            # Déplacer immédiatement sur le bureau virtuel 4 si wmctrl est disponible
            try:
                await asyncio.sleep(0.8)
                subprocess.run(["wmctrl", "-r", "TLScontact", "-t", "3"], capture_output=True)
                subprocess.run(["wmctrl", "-r", "Google Chrome", "-t", "3"], capture_output=True)
            except Exception:
                pass

        # Connexion de Playwright via CDP
        self.playwright_instance = await async_playwright().start()
        self.pw_browser = await self.playwright_instance.chromium.connect_over_cdp(self.browser_session.cdp_url)
        context = self.pw_browser.contexts[0] if self.pw_browser.contexts else await self.pw_browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        return context, page

    async def stop(self):
        """Ferme proprement la connexion Playwright et la session Chrome."""
        try:
            if self.pw_browser:
                await self.pw_browser.close()
        except Exception:
            pass

        try:
            if self.playwright_instance:
                await self.playwright_instance.stop()
        except Exception:
            pass

        try:
            if self.browser_session:
                await self.browser_session.stop()
        except Exception:
            pass
