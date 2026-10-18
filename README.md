# 🤖 Browser-Use Autonomous Web Agent

Agent d'automatisation et de navigation web autonome basé sur **[browser-use](https://github.com/browser-use/browser-use)** et **Playwright**, piloté par les modèles **Google Gemini** ou **OpenRouter (modèles gratuits)**.

L'agent est capable d'analyser le DOM, de cliquer, de remplir des formulaires, d'interagir avec des menus complexes, d'extraire des données et de compiler des synthèses structurées.

---

## ✨ Fonctionnalités

- 📁 **Prompts via fichiers texte** : Modifiez simplement `prompt.txt` ou chargez des fichiers personnalisés (`-f prompts/mon_prompt.txt`) sans toucher au code.
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
├── run_agent.py              # Script principal d'exécution
├── prompt.txt                # Fichier contenant le prompt courant
├── prompts/                  # Dossier d'exemples de prompts
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
git clone https://github.com/<votre-user>/browser-use-agent.git
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
```

### 4. Lancer l'agent
```bash
# Exécute le prompt situé dans prompt.txt (fenêtre navigateur visible)
python run_agent.py
```

---

## 🛠️ Options et Ligne de Commande

| Option | Raccourci | Description | Défaut |
| :--- | :---: | :--- | :--- |
| `--prompt-file` | `-f` | Chemin vers le fichier texte contenant le prompt | `prompt.txt` |
| `--task` | `-t` | Instruction directe en ligne de commande (écrase le fichier) | `None` |
| `--openrouter` | | Activer OpenRouter au lieu de Gemini (`true` / `false`) | Selon `.env` |
| `--model` | | Nom du modèle LLM à forcer | Selon `.env` |
| `--headless` | | Exécuter le navigateur en arrière-plan sans affichage graphique | `False` |

### Exemples d'utilisation :

- **Tester un prompt spécifique du dossier `prompts/`** :
  ```bash
  python run_agent.py -f prompts/freework_sre.txt
  ```

- **Forcer l'utilisation d'OpenRouter gratuit** :
  ```bash
  python run_agent.py --openrouter true
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

## ☁️ Déploiement sur une Machine Virtuelle (Serveur Linux distant)

Sur une VM Ubuntu / Debian (sans écran connecté) :

### 1. Installation en une commande
```bash
git clone https://github.com/<votre-user>/browser-use-agent.git
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
