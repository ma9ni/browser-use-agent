import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from agents.playwright.tls_watcher import TLSContactWatcher, TLSWatcherError
from core.recaptcha import _english_challenge_label


class RecaptchaLabelTests(unittest.TestCase):
    def test_french_label_with_accents(self):
        self.assertEqual(
            _english_challenge_label("Sélectionnez toutes les images contenant des feux de circulation"),
            "traffic light",
        )

    def test_english_label_is_preserved(self):
        self.assertEqual(_english_challenge_label("traffic lights"), "traffic lights")

    def test_motorcycle_label_from_tlscontact(self):
        self.assertEqual(_english_challenge_label("motos"), "motorcycle")


class CloudflareDetectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_block_page_is_classified(self):
        page = SimpleNamespace(
            title=AsyncMock(return_value="Sorry, you have been blocked"),
            locator=Mock(return_value=SimpleNamespace(inner_text=AsyncMock(return_value="You are unable to access this site"))),
        )
        self.assertIsNotNone(await TLSContactWatcher().detect_anti_bot_block(page))

    async def test_transient_verification_can_clear(self):
        watcher = TLSContactWatcher()
        watcher.detect_anti_bot_block = AsyncMock(side_effect=["Vérification en cours", None])
        page = SimpleNamespace(url="https://example.test", wait_for_timeout=AsyncMock())
        await watcher.wait_for_cloudflare(page, timeout_sec=5)
        page.wait_for_timeout.assert_awaited_once()

    async def test_explicit_refusal_is_not_retried(self):
        watcher = TLSContactWatcher()
        watcher.detect_anti_bot_block = AsyncMock(return_value="Accès refusé par Cloudflare")
        page = SimpleNamespace(url="https://example.test", wait_for_timeout=AsyncMock())
        with self.assertRaises(TLSWatcherError):
            await watcher.wait_for_cloudflare(page)
        page.wait_for_timeout.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
