import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, Browser, BrowserProfile, Controller

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
        description="Lancer l'agent Browser-Use (Gemini ou OpenRouter) avec un ou plusieurs fichiers de prompts ou en ligne de commande."
    )
    
    # Arguments positionnels : un ou plusieurs fichiers de prompt
    parser.add_argument(
        "prompts",
        nargs="*",
        help="Nom(s) ou chemin(s) des fichiers de prompt à exécuter (ex: prompts/freework_sre.txt, freework_sre.txt ou job1.txt job2.txt)"
    )
    
    # Fichier de prompt (option pour compatibilité ascendante)
    default_prompt_file = os.getenv("PROMPT_FILE", "prompt.txt")
    parser.add_argument(
        "-f", "--prompt-file",
        type=str,
        default=None,
        help=f"Chemin vers un fichier texte contenant le prompt (alternative: argument positionnel direct, défaut: {default_prompt_file})"
    )
    
    # Texte direct du prompt (optionnel, prend le pas sur les fichiers s'il est spécifié)
    parser.add_argument(
        "-t", "--task",
        type=str,
        default=None,
        help="Texte direct du prompt (écrase le contenu des fichiers de prompt si renseigné)"
    )
    
    # Exécution en parallèle de plusieurs jobs
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help="Exécuter les différents jobs de prompt en parallèle plutôt que séquentiellement"
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

def resolve_prompt_file(prompt_input: str) -> Path:
    """Résout intelligemment le chemin d'un fichier de prompt (direct, dans prompts/, avec ou sans .txt)."""
    p = Path(prompt_input)
    candidates = [
        p,
        Path("prompts") / p,
        p.with_suffix(".txt") if p.suffix != ".txt" else p,
        Path("prompts") / (p.name if p.suffix == ".txt" else f"{p.name}.txt"),
    ]
    
    for candidate in candidates:
        if candidate.is_file():
            return candidate
            
    # Si non trouvé, afficher la liste des prompts disponibles
    available_prompts: list[str] = []
    if Path("prompt.txt").is_file():
        available_prompts.append("prompt.txt")
    prompts_dir = Path("prompts")
    if prompts_dir.is_dir():
        available_prompts.extend([str(f) for f in sorted(prompts_dir.glob("*.txt"))])
        
    print(f"\n[!] ERREUR: Le fichier de prompt '{prompt_input}' n'a pas été trouvé.")
    if available_prompts:
        print("Fichiers de prompt disponibles :")
        for f in available_prompts:
            print(f"  - {f}")
    print("\nExemples d'utilisation :")
    print("    python run_agent.py prompts/freework_sre.txt")
    print("    python run_agent.py freework_sre.txt")
    print("    python run_agent.py freework_sre.txt hacker_news.txt\n")
    sys.exit(1)

def load_prompt_content(path: Path) -> str:
    """Lit et valide le contenu d'un fichier de prompt."""
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        print(f"\n[!] ERREUR: Le fichier de prompt '{path}' est vide.")
        print("Ajoutez votre instruction dans ce fichier et relancez le script.\n")
        sys.exit(1)
    return content

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

def load_sensitive_data() -> dict[str, str]:
    """
    Extrait automatiquement les identifiants et variables confidentielles définies dans .env.
    Exclut les clés de configuration système (clés LLM, flags, notify, etc.).
    Retourne un dictionnaire {placeholder: valeur_secrete} qui alimente l'agent Browser-Use
    via sensitive_data. Les secrets sont injectés directement dans le DOM du navigateur
    sans jamais être affichés ni lus en clair dans les logs ou le contexte LLM.
    """
    from dotenv import dotenv_values
    
    SYSTEM_KEYS = {
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL",
        "USE_OPENROUTER", "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
        "PROMPT_FILE", "WHATSAPP_PHONE", "WHATSAPP_API_KEY",
    }
    
    env_vars = dotenv_values(".env")
    sensitive: dict[str, str] = {}
    
    for key, val in env_vars.items():
        if not key or not val:
            continue
        clean_key = key.strip()
        clean_val = val.strip()
        if clean_key in SYSTEM_KEYS or not clean_val:
            continue
        
        # Enregistre sous les deux formes (minuscule et originale)
        sensitive[clean_key.lower()] = clean_val
        sensitive[clean_key] = clean_val
        
    return sensitive

def create_controller() -> Controller:
    """Initialise le Controller avec les actions personnalisées, notamment la notification WhatsApp en temps réel."""
    controller = Controller()

    @controller.action(
        "Envoie immédiatement une notification d'alerte WhatsApp via notify.py. "
        "À déclencher obligatoirement et instantanément dès qu'un créneau disponible est repéré sur la page, sans attendre la fin du processus."
    )
    def notify_whatsapp(message: str) -> str:
        """Envoie immédiatement une notification WhatsApp via notify.py."""
        print(f"\n📲 [NOTIFICATION WHATSAPP EN COURS D'ACTION] : {message}")
        try:
            from notify import send_whatsapp
            success = send_whatsapp(message)
            if success:
                print("✅ [NOTIFICATION WHATSAPP ENVOYÉE]")
                return f"Notification WhatsApp envoyée avec succès : {message}"
            else:
                print("❌ [ÉCHEC NOTIFICATION WHATSAPP]")
                return "Échec lors de l'envoi WhatsApp via notify.py"
        except Exception as e:
            print(f"❌ [ERREUR NOTIFICATION WHATSAPP] : {e}")
            return f"Erreur lors de l'envoi WhatsApp : {e}"

    return controller

async def run_single_job(
    task_prompt: str,
    job_label: str,
    llm,
    headless: bool,
    sensitive_data: dict[str, str] | None = None,
    job_index: int = 1,
    total_jobs: int = 1,
) -> dict:
    """Exécute un job d'agent individuel avec son propre profil de navigateur."""
    print(f"\n=================== JOB [{job_index}/{total_jobs}]: {job_label} ===================")
    print(f"📄 Source du prompt      : {job_label}")
    print(f"🎯 Prompt                : {task_prompt}")
    print(f"🖥️  Affichage navigateur  : {'Arrière-plan (headless)' if headless else 'Fenêtre visible en direct'}")
    if sensitive_data:
        keys_display = sorted(list(set(k.lower() for k in sensitive_data.keys())))
        print(f"🔒 Données sécurisées    : {', '.join(keys_display)} (valeurs masquées)")
    print("--------------------------------------------------------------------------------")
    
    browser = Browser(browser_profile=BrowserProfile(headless=headless))
    controller = create_controller()
    try:
        agent = Agent(
            task=task_prompt,
            llm=llm,
            browser=browser,
            controller=controller,
            sensitive_data=sensitive_data,
        )
        history = await agent.run()
        result = history.final_result()
        print(f"\n=================== RÉSULTAT FINAL [{job_label}] ===================")
        print(result)
        print("=====================================================================")
        return {"job": job_label, "status": "success", "result": result}
    except Exception as e:
        print(f"\n❌ [ERREUR Job {job_label}] : {e}")
        return {"job": job_label, "status": "error", "error": str(e)}
    finally:
        try:
            await browser.close()
        except Exception:
            pass

async def main():
    args = parse_args()
    
    # Détermination de la liste des jobs à exécuter
    jobs = []
    if args.task:
        jobs.append({
            "content": args.task.strip(),
            "label": "Argument direct (--task)"
        })
    else:
        # Si des fichiers sont passés en positionnel ou via -f
        raw_files = []
        if args.prompts:
            raw_files.extend(args.prompts)
        if args.prompt_file and args.prompt_file not in raw_files:
            raw_files.append(args.prompt_file)
        if not raw_files:
            default_file = os.getenv("PROMPT_FILE", "prompt.txt")
            raw_files = [default_file]
            
        for file_input in raw_files:
            resolved_path = resolve_prompt_file(file_input)
            content = load_prompt_content(resolved_path)
            try:
                display_label = str(resolved_path.relative_to(Path.cwd()))
            except ValueError:
                display_label = str(resolved_path)
            jobs.append({
                "content": content,
                "label": display_label,
                "path": resolved_path
            })
            
    print("\n=================== BROWSER-USE AGENT ===================")
    print(f"🤖 Mode LLM               : {'OpenRouter (true)' if args.openrouter else 'Gemini (false, par défaut)'}")
    print(f"🖥️  Affichage navigateur  : {'Arrière-plan (headless)' if args.headless else 'Fenêtre visible en direct'}")
    print(f"📋 Nombre de job(s)       : {len(jobs)}")
    if len(jobs) > 1:
        mode_str = "Parallèle (--parallel)" if args.parallel else "Séquentiel"
        print(f"⚙️  Mode d'exécution       : {mode_str}")
        print("📑 Jobs prévus :")
        for i, j in enumerate(jobs, 1):
            print(f"   {i}. {j['label']}")
    print("=========================================================\n")
    
    llm = get_llm(args.openrouter, args.model)
    sensitive_data = load_sensitive_data()
    if sensitive_data:
        keys_display = sorted(list(set(k.lower() for k in sensitive_data.keys())))
        print(f"🔒 Identifiants .env chargés : {', '.join(keys_display)} (valeurs protégées & masquées)")
    
    if args.parallel and len(jobs) > 1:
        print(f"⚡ Lancement simultané de {len(jobs)} jobs...")
        tasks = [
            run_single_job(
                task_prompt=job["content"],
                job_label=job["label"],
                llm=llm,
                headless=args.headless,
                sensitive_data=sensitive_data,
                job_index=idx + 1,
                total_jobs=len(jobs),
            )
            for idx, job in enumerate(jobs)
        ]
        results = await asyncio.gather(*tasks)
    else:
        results = []
        for idx, job in enumerate(jobs):
            res = await run_single_job(
                task_prompt=job["content"],
                job_label=job["label"],
                llm=llm,
                headless=args.headless,
                sensitive_data=sensitive_data,
                job_index=idx + 1,
                total_jobs=len(jobs),
            )
            results.append(res)
            
    if len(jobs) > 1:
        print("\n=================== RÉCAPITULATIF DE TOUS LES JOBS ===================")
        for res in results:
            icon = "✅" if res["status"] == "success" else "❌"
            print(f"{icon} {res['job']} : {res['status'].upper()}")
        print("======================================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
