"""
LLM Agent Module: Browser-Use AI Agent.
Pilote des agents IA autonomes capables d'explorer le web à partir de prompts
en langage naturel, avec injection sécurisée des credentials et contrôleur d'actions.
"""

import asyncio
from pathlib import Path
from browser_use import Agent, Browser, BrowserProfile, Controller
from core.config import (
    USE_OPENROUTER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    get_sensitive_data,
    PROMPTS_DIR,
)
from core.notifier import send_whatsapp

# Patch préfixes OpenRouter
try:
    from browser_use.llm.openrouter import chat as or_chat
    _orig_get_first_choice = or_chat.ChatOpenRouter._get_first_choice

    def _sanitized_get_first_choice(self, response):
        choice = _orig_get_first_choice(self, response)
        if choice and getattr(choice, 'message', None) and choice.message.content:
            text = choice.message.content.strip()
            if '{' in text and '}' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                choice.message.content = text[start:end]
        return choice

    or_chat.ChatOpenRouter._get_first_choice = _sanitized_get_first_choice
except Exception:
    pass


def create_controller() -> Controller:
    """Instancie le contrôleur avec l'action personnalisée de notification WhatsApp."""
    controller = Controller()

    @controller.action("Envoyer immédiatement un message d'alerte WhatsApp")
    def notify_whatsapp(message: str) -> str:
        """Envoie un message WhatsApp direct via notify.py."""
        success = send_whatsapp(message)
        if success:
            return "Alerte WhatsApp délivrée avec succès."
        return "Échec lors de la transmission WhatsApp."

    return controller


def get_llm():
    """Initialise le modèle LLM approprié (OpenRouter ou Gemini)."""
    if USE_OPENROUTER:
        from browser_use.llm.openrouter import ChatOpenRouter
        return ChatOpenRouter(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
        )
    else:
        from browser_use.llm.google import ChatGoogle
        return ChatGoogle(
            model=GEMINI_MODEL,
            api_key=GEMINI_API_KEY,
        )


class LLMBrowserAgent:
    """Agent autonome piloté par LLM."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.sensitive_data = get_sensitive_data()
        self.controller = create_controller()
        self.llm = get_llm()

    async def run_task(self, task_prompt: str, job_label: str = "Job") -> dict:
        """Exécute un prompt donné."""
        print(f"\n=================== JOB: {job_label} ===================")
        print(f"🎯 Prompt : {task_prompt[:150]}...")
        print(f"🖥️  Affichage : {'Arrière-plan (headless)' if self.headless else 'Fenêtre visible'}")
        print("--------------------------------------------------------------------------------")

        browser = Browser(browser_profile=BrowserProfile(headless=self.headless))
        try:
            agent = Agent(
                task=task_prompt,
                llm=self.llm,
                browser=browser,
                controller=self.controller,
                sensitive_data=self.sensitive_data,
            )
            history = await agent.run()
            result = history.final_result()
            print(f"\n=================== RÉSULTAT [{job_label}] ===================")
            print(result)
            return {"job": job_label, "status": "success", "result": result}
        except Exception as e:
            print(f"\n❌ [ERREUR {job_label}] : {e}")
            return {"job": job_label, "status": "error", "error": str(e)}
        finally:
            try:
                await browser.close()
            except Exception:
                pass
