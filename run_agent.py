import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, Browser, BrowserProfile

# Nettoyage automatique des préfixes textuels (ex: 'User Safety: safe') d'OpenRouter
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

def parse_args():
    parser = argparse.ArgumentParser(
        description="Lancer l'agent Browser-Use (Gemini ou OpenRouter) avec prompt depuis un fichier ou en ligne de commande."
    )
    
    # Fichier de prompt (par défaut: prompt.txt ou variable PROMPT_FILE)
    default_prompt_file = os.getenv("PROMPT_FILE", "prompt.txt")
    parser.add_argument(
        "-f", "--prompt-file",
        type=str,
        default=default_prompt_file,
        help=f"Chemin vers le fichier texte contenant le prompt (défaut: {default_prompt_file})"
    )
    
    # Texte direct du prompt (optionnel, prend le pas sur le fichier s'il est spécifié)
    parser.add_argument(
        "-t", "--task",
        type=str,
        default=None,
        help="Texte direct du prompt (écrase le contenu du fichier de prompt si renseigné)"
    )
    
    # Flag OpenRouter true/false
    env_use_openrouter = os.getenv("USE_OPENROUTER", "false").lower() in ("true", "1", "yes")
    parser.add_argument(
        "--openrouter",
        type=lambda v: v.lower() in ("true", "1", "yes"),
        nargs="?",
        const=True,
        default=env_use_openrouter,
        help="Activer OpenRouter au lieu de Gemini (true/false, défaut: selon .env ou false)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Nom du modèle LLM à utiliser"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Exécuter le navigateur en arrière-plan sans affichage graphique"
    )
    
    return parser.parse_args()

def load_task_prompt(prompt_file_path: str, direct_task: str | None) -> tuple[str, str]:
    """Charge le prompt depuis l'argument direct ou depuis un fichier."""
    if direct_task:
        return direct_task.strip(), "Argument direct (--task)"
    
    path = Path(prompt_file_path)
    if not path.is_file():
        print(f"\n[!] ERREUR: Le fichier de prompt '{prompt_file_path}' n'existe pas.")
        print("Veuillez créer ce fichier ou spécifier un autre fichier avec :")
        print("    python run_agent.py -f mon_prompt.txt\n")
        sys.exit(1)
        
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        print(f"\n[!] ERREUR: Le fichier de prompt '{prompt_file_path}' est vide.")
        print("Ajoutez votre instruction dans ce fichier et relancez le script.\n")
        sys.exit(1)
        
    return content, f"Fichier '{prompt_file_path}'"

def get_llm(use_openrouter: bool, model_name: str | None):
    if use_openrouter:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("\n[!] ERREUR: Flag OpenRouter activé, mais aucune clé OPENROUTER_API_KEY trouvée dans .env.")
            print("1. Obtenez une clé gratuite sur : https://openrouter.ai/keys")
            print("2. Ajoutez-la dans votre .env : OPENROUTER_API_KEY=\"sk-or-v1-...\"\n")
            sys.exit(1)
            
        model = model_name or os.getenv("OPENROUTER_MODEL", "openrouter/free")
        print(f"🌐 [Provider: OpenRouter (Modèle gratuit: {model})]")
        
        from browser_use.llm.openrouter.chat import ChatOpenRouter
        return ChatOpenRouter(model=model, api_key=api_key)
    else:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("\n[!] ERREUR: Aucune clé GEMINI_API_KEY trouvée dans .env.")
            print("Veuillez renseigner votre clé dans .env")
            sys.exit(1)
            
        model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        print(f"⚡ [Provider: Google Gemini (Modèle: {model})]")
        
        from browser_use.llm.google.chat import ChatGoogle
        return ChatGoogle(model=model, api_key=api_key)

async def main():
    args = parse_args()
    
    # Chargement du prompt depuis le fichier ou argument direct
    task_prompt, source_desc = load_task_prompt(args.prompt_file, args.task)
    
    print("\n=================== BROWSER-USE AGENT ===================")
    print(f"📄 Source du prompt      : {source_desc}")
    print(f"🎯 Prompt chargé          : {task_prompt}")
    print(f"🤖 Mode LLM               : {'OpenRouter (true)' if args.openrouter else 'Gemini (false, par défaut)'}")
    print(f"🖥️  Affichage navigateur  : {'Arrière-plan (headless)' if args.headless else 'Fenêtre visible en direct'}")
    
    llm = get_llm(args.openrouter, args.model)
    browser = Browser(browser_profile=BrowserProfile(headless=args.headless))
    print("=========================================================\n")
    
    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser=browser,
    )
    
    history = await agent.run()
    print("\n=================== RÉSULTAT FINAL ===================")
    print(history.final_result())
    print("======================================================")

if __name__ == "__main__":
    asyncio.run(main())
