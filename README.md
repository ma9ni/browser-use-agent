# 🤖 Browser-Use Autonomous Web Agent

Agent d'automatisation et de navigation web autonome basé sur **[browser-use](https://github.com/browser-use/browser-use)** et **Playwright**, piloté par les modèles **Google Gemini** ou **OpenRouter (modèles gratuits)**.

L'agent est capable d'analyser le DOM, de cliquer, de remplir des formulaires, d'interagir avec des menus complexes, d'extraire des données et de compiler des synthèses structurées.

---

## ✨ Fonctionnalités

- 📁 **Prompts via arguments et fichiers texte** : Lancez des jobs directement en passant un ou plusieurs noms de fichiers de prompt en argument (ex: `python run_agent.py freework_sre.txt`), ou via `prompt.txt`.
- 📲 **Notifications WhatsApp en direct** : Alerte instantanée via [`notify.py`](file:///home/ahmed/IdeaProjects/browser-use-demo/notify.py) dès qu'un créneau ou événement cible est détecté au cours des étapes.
- 🔄 **Multi-jobs séquentiel ou parallèle** : Exécutez plusieurs prompts à la suite ou en parallèle (`--parallel`) avec synthèse finale de chaque job.
- ⚡ **Multi-Providers** :
  - **Google Gemini** (`gemini-3.8-flash` ou `gemini-2.5-pro`) : Ultra-rapide (~1.5s), gratuit sur Google AI Studio.
  - **OpenRouter** (`openrouter/free`) : 100% gratuit via les modèles communautaires.
- 🖥️ **Mode Graphique ou Headless** : Visualisez l'écran en direct sur votre machine ou faites-le tourner en arrière-plan sur une VM distante (`--headless`).
- 🛡️ **Résilience intégrée** : Nettoyage et assainissement automatique des réponses JSON pour pallier les instabilités des modèles gratuits.
- 🚀 **Prêt pour le déploiement sur VM** : Script d'installation `setup.sh` automatisé pour Ubuntu / Debian.

---

## 📂 Structure du projet

```text
.
├── run_agent.py              # Script principal d'exécution IA (Browser-Use)
├── playwright_tls.py         # Script Playwright pur 100% autonome (0$ de coût, sans LLM)
├── monitor.py                # Surveillance continue & boucle planifiée (ex: TLScontact)
├── notify.py                 # Envoi d'alertes WhatsApp via CallMeBot
├── prompt.txt                # Fichier contenant le prompt courant
├── prompts/                  # Dossier d'exemples de prompts
│   ├── tls.txt               # Parcours prise de RDV TLScontact (Tunis)
│   ├── freework_sre.txt      # Recherche de missions Freelance SRE/DevOps
│   ├── leboncoin_olivier.txt # Recherche d'annonces sur Leboncoin
│   └── hacker_news.txt       # Extraction des top articles Hacker News
├── requirements.txt          # Dépendances Python
├── setup.sh                  # Script d'installation automatisé pour VM Linux
├── .env.example              # Gabarit des variables d'environnement
├── .gitignore                # Fichiers et secrets ignorés par Git
└── README.md
```

---

## 🚀 Démarrage Rapide (En local)

### 1. Cloner le projet
```bash
git clone https://github.com/ma9ni/browser-use-agent.git
cd browser-use-agent
```

### 2. Créer l'environnement virtuel et installer les dépendances
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurer les clés API
Copiez le fichier `.env.example` en `.env` :
```bash
cp .env.example .env
```
Renseignez au choix :
- Votre clé **Gemini** (Gratuite sur [Google AI Studio](https://aistudio.google.com/app/apikey))
- Ou votre clé **OpenRouter** (Gratuite sur [OpenRouter Keys](https://openrouter.ai/keys))

```env
GEMINI_API_KEY=AIzaSy...
# ou
OPENROUTER_API_KEY=sk-or-v1-...
USE_OPENROUTER=true

# Identifiants confidentiels pour vos jobs (ex: TLScontact, etc.)
TLS_EMAIL=votre_email@domaine.com
TLS_PASSWORD=votre_mot_de_passe
```

> 🔒 **Sécurité et confidentialité des identifiants** : Les identifiants définis dans `.env` sont injectés de manière chiffrée/masquée dans l'agent via `sensitive_data`. L'agent ne lit jamais vos mots de passe en clair et ceux-ci ne sont jamais affichés dans les logs ou transmis au LLM. Dans vos prompts, vous pouvez référencer ces valeurs avec `<secret>tls_email</secret>` ou `<secret>tls_password</secret>`. Vous pouvez ajouter n'importe quelle variable d'authentification pour vos futurs processus (ex: `AMAZON_USER`, `GITHUB_TOKEN`, etc.), l'agent les détectera automatiquement.

### 4. Lancer l'agent
```bash
# Exécute le prompt situé dans prompt.txt (fenêtre navigateur visible)
python run_agent.py
```

---

## 🛠️ Options et Ligne de Commande

| Argument / Option | Raccourci | Description | Défaut |
| :--- | :---: | :--- | :--- |
| `[prompts ...]` | *(positionnel)* | Nom(s) ou chemin(s) des fichiers de prompt à exécuter | `prompt.txt` |
| `--prompt-file` | `-f` | Chemin vers un fichier texte contenant le prompt (alternative) | `prompt.txt` |
| `--parallel` | | Exécuter plusieurs jobs de prompts en parallèle | `False` (séquentiel) |
| `--task` | `-t` | Instruction directe en ligne de commande (écrase les fichiers) | `None` |
| `--openrouter` | | Activer OpenRouter au lieu de Gemini (`true` / `false`) | Selon `.env` |
| `--model` | | Nom du modèle LLM à forcer | Selon `.env` |
| `--headless` | | Exécuter le navigateur en arrière-plan sans affichage graphique | `False` |

### Exemples d'utilisation :

- **Lancer un job avec le nom du prompt en argument direct** :
  ```bash
  # Cherche automatiquement dans prompts/ ou le dossier courant
  python run_agent.py freework_sre.txt
  # ou avec le chemin complet :
  python run_agent.py prompts/freework_sre.txt
  ```

- **Lancer plusieurs jobs à la suite (séquentiel)** :
  ```bash
  python run_agent.py freework_sre.txt hacker_news.txt
  # ou tous les prompts du dossier :
  python run_agent.py prompts/*.txt
  ```

- **Lancer plusieurs jobs en parallèle** :
  ```bash
  python run_agent.py freework_sre.txt hacker_news.txt --parallel --headless
  ```

- **Lancer plusieurs jobs en tâche de fond (arrière-plan Linux / VM)** :
  ```bash
  python run_agent.py prompts/freework_sre.txt --headless &
  python run_agent.py prompts/hacker_news.txt --headless &
  ```

- **Forcer l'utilisation d'OpenRouter gratuit** :
  ```bash
  python run_agent.py hacker_news.txt --openrouter true
  ```

- **Exécuter en tâche de fond (Headless) sur serveur** :
  ```bash
  python run_agent.py --headless
  ```

- **Passer une instruction rapide directement** :
  ```bash
  python run_agent.py -t "Va sur wikipedia.org et résume l'article en vedette"
  ```

---

## 📡 Surveillance Continue (Monitoring Automatique)

Pour surveiller l'ouverture de créneaux (ex: TLScontact) en continu sans saturer la mémoire ni le contexte LLM, utilisez le script [`monitor.py`](monitor.py) :

```bash
# Vérification toutes les 20 minutes avec rapport WhatsApp toutes les 6h (18 passages) :
python monitor.py tls --interval 20 --heartbeat 18

# Rapport WhatsApp toutes les 10 vérifications :
python monitor.py tls --interval 20 --heartbeat 10

# En arrière-plan (headless) sur serveur / VM distante :
python monitor.py tls --interval 20 --heartbeat 18 --headless

# En tâche de fond permanente (nohup) :
nohup python monitor.py tls --interval 20 --heartbeat 18 --headless > /dev/null 2>&1 &
```

| Option | Raccourci | Description | Défaut |
| :--- | :---: | :--- | :--- |
| `prompt` | *(positionnel)* | Nom du prompt à exécuter | `tls` |
| `--interval` | `-i` | Intervalle entre chaque passage en minutes | `20` |
| `--heartbeat` | `-s` | Envoyer un rapport WhatsApp périodique tous les N passages | `18` (~6h à 20 min) |
| `--headless` | | Navigateur en arrière-plan (sans affichage) | `False` |
| `--timeout` | | Délai max par vérification en secondes avant coupure | `180` |
| `--max-runs` | | Nombre max d'exécutions avant arrêt | Illimité |
| `--log-file` | | Fichier de log cumulé | `monitor.log` |

---

## ⚡ Solution 100% Gratuite (0$ Coût / Sans LLM) : `playwright_tls.py`

Si vous souhaitez surveiller les créneaux TLScontact en continu **sans consommer de jetons IA, sans clé API payante et sans limite de quota** :

```bash
# Vérification unique immédiate (test en direct) :
python playwright_tls.py

# Surveillance continue en boucle (ex: toutes les 15 minutes avec rapport WhatsApp toutes les 6h) :
python playwright_tls.py --interval 15 --heartbeat 24

# En arrière-plan (headless) sur serveur / VM distante :
python playwright_tls.py --interval 15 --heartbeat 24 --headless

# En tâche de fond permanente (nohup) :
nohup python playwright_tls.py --interval 15 --heartbeat 24 --headless > /dev/null 2>&1 &
```

- 🚀 **Ultra-rapide** : Exécution directe en ~5 à 8 secondes (au lieu de 30-40s avec un LLM).
- 💰 **0$** : Aucun appel d'API LLM, fonctionne 24h/24 et 7j/7 sans limitation.
- 📲 **Alerte WhatsApp** : Notifie immédiatement via [`notify.py`](notify.py) dès qu'un créneau est libre.

---

## ☁️ Déploiement sur une Machine Virtuelle (Serveur Linux distant)

Sur une VM Ubuntu / Debian (sans écran connecté) :

### 1. Installation en une commande
```bash
git clone https://github.com/ma9ni/browser-use-agent.git
cd browser-use-agent
chmod +x setup.sh
./setup.sh
```

### 2. Configurer `.env`
```bash
nano .env
```

### 3. Exécuter l'agent
```bash
source .venv/bin/activate
python run_agent.py --headless
```

> **Note VM sans interface graphique** : Le drapeau `--headless` est indispensable sur les serveurs distants pour exécuter le navigateur sans serveur d'affichage X11.

---

## 📄 Licence
Ce projet est open-source sous licence MIT.
