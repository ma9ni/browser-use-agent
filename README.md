# 🚀 Browser Automation & AI Agents Suite

Une suite complète, modulaire et professionnelle d'automatisation de navigateur web combinant :
1. **Agents Playwright Déterministes (0$ LLM)** : ultra-rapides, gratuits, contournement natif anti-bot & Cloudflare.
2. **Agents IA Browser-Use (LLM)** : pilotés par modèles de langage (Google Gemini ou OpenRouter) pour explorer le web à partir de prompts en langage naturel.
3. **Système d'Alerte WhatsApp & Heartbeat** : alertes instantanées dès l'ouverture d'un créneau et rapports de bon fonctionnement périodiques.
4. **Intégration IDE (PyCharm / IntelliJ)** : 7 Run Configurations prêtes à l'emploi (1-clic pour exécuter ou déboguer).

---

## 📁 Architecture Modulaire du Projet

```text
browser-use-demo/
│
├── .idea/
│   └── runConfigurations/        # 🎯 Configurations d'exécution PyCharm / IntelliJ
│       ├── ⚡ Playwright TLS - Single Check
│       ├── ⚡ Playwright TLS - Monitor Continuous (Headless)
│       ├── ⚡ Playwright TLS - Monitor Continuous (Visible)
│       ├── 🤖 Agent LLM - TLS (prompts/tls.txt)
│       ├── 🤖 Agent LLM - Freework SRE
│       ├── 📋 Agent LLM - List Prompts
│       └── 📲 WhatsApp - Test Notification
│
├── agents/                       # Vos agents d'automatisation
│   ├── playwright/               # Agents déterministes (0$ LLM, ultra-rapides)
│   │   ├── __init__.py
│   │   └── tls_watcher.py        # Agent TLScontact Tunis (anti-bot, créneaux)
│   └── llm/                      # Agents IA Browser-Use
│       ├── __init__.py
│       └── browser_agent.py      # Agent piloté par IA (Gemini / OpenRouter)
│
├── core/                         # Moteur & Utilitaires partagés
│   ├── __init__.py
│   ├── browser.py                # Gestionnaire Chrome (anti-détection, CDP, Workspaces)
│   ├── config.py                 # Configuration centrale .env & protection des secrets
│   └── notifier.py               # Alertes et rapports Heartbeat WhatsApp (CallMeBot)
│
├── prompts/                      # Banques de prompts pour vos agents IA
│   ├── tls.txt                   # Parcours TLS optimisé
│   ├── freework_sre.txt          # Recherche missions freelances
│   ├── hacker_news.txt           # Veille tech
│   └── leboncoin_olivier.txt     # Recherche immo / annonces
│
├── screenshots/                  # Captures d'écran de validation et diagnostics
├── tls_user_profile/             # Profil navigateur persistant (sessions, cookies)
│
├── main.py                       # 🌟 Point d'entrée CLI unifié et intuitif
├── playwright_tls.py             # Raccourci rétrocompatible Agent TLS (0$)
├── run_agent.py                  # Raccourci rétrocompatible Agent IA
└── notify.py                     # Raccourci rétrocompatible WhatsApp
```

---

## 🖥️ 1. Utilisation dans PyCharm / IntelliJ IDEA

Toutes les configurations d'exécution sont préconfigurées. Dans la barre d'outils en haut de votre IDE, sélectionnez simplement la commande dans le menu déroulant :

| Configuration dans PyCharm / IntelliJ | Description |
| :--- | :--- |
| `⚡ Playwright TLS - Single Check` | Vérification unique du calendrier TLScontact en ~15s (0$ LLM) |
| `⚡ Playwright TLS - Monitor Continuous (Headless)` | Surveillance 24/7 en arrière-plan sans fenêtre intrusive (Workspace 4) |
| `⚡ Playwright TLS - Monitor Continuous (Visible)` | Surveillance continue avec fenêtre Chrome visible à l'écran |
| `🤖 Agent LLM - TLS (prompts/tls.txt)` | Exécute l'agent IA Browser-Use avec le prompt TLS |
| `🤖 Agent LLM - Freework SRE` | Exécute l'agent IA Browser-Use sur Freework |
| `📋 Agent LLM - List Prompts` | Affiche la liste des prompts disponibles |
| `📲 WhatsApp - Test Notification` | Envoie un message WhatsApp pour tester la clé CallMeBot |

---

## ⚡ 2. Agent Playwright TLScontact (100% Gratuit / 0$ LLM)

Idéal pour surveiller en continu l'ouverture de créneaux de rendez-vous TLScontact sans consommer de tokens d'IA.

### Caractéristiques :
- **0$ de coût** : Zéro appel API payant.
- **Ultra-rapide** : Exécution complète en ~15 à 20 secondes.
- **Anti-Cloudflare natif** : Contourne Turnstile et les bannières cookies.
- **Arrière-plan sans perturbation** : En mode `--headless`, la fenêtre tourne sur le bureau virtuel 4 sous Linux (zéro fenêtre sur votre écran de travail).
- **Alerte WhatsApp immédiate** : Dès qu'un créneau est visible, message WhatsApp envoyé avec le lien direct de réservation.

### Ligne de commande :

#### Vérification ponctuelle rapide :
```bash
python main.py tls
# ou
python playwright_tls.py
```

#### Surveillance continue en arrière-plan :
```bash
python main.py tls --interval 15 --heartbeat 24 --headless
# ou
python playwright_tls.py --interval 15 --heartbeat 24 --headless
```
- `--interval 15` : Vérifie toutes les 15 minutes.
- `--heartbeat 24` : Envoie un rapport WhatsApp de bon fonctionnement toutes les 6 heures (24 x 15min).
- `--headless` : Exécution invisible en arrière-plan.

---

## 🤖 3. Agents IA Browser-Use (LLM)

Pour des tâches complexes nécessitant du raisonnement ou de la navigation adaptative via LLM (Gemini ou OpenRouter).

### Commandes :

#### Lancer avec un prompt existant :
```bash
python main.py agent tls.txt
python main.py agent freework_sre.txt
# ou
python run_agent.py prompts/tls.txt
```

#### Lister tous les prompts disponibles :
```bash
python main.py list-prompts
```

#### Lancer avec une instruction directe en ligne de commande :
```bash
python main.py agent -t "Cherche les 3 dernières actualités sur l'IA et résume-les"
```

---

## 📲 4. Notification WhatsApp (CallMeBot)

Pour tester si vos identifiants WhatsApp fonctionnent :
```bash
python main.py test-notify
# ou
python notify.py "Ceci est un test"
```

---

## 🌐 5. Déploiement 24/7 sur une VM Linux (Sans écran)

Pour laisser tourner la surveillance sur un VPS / serveur distant sans écran physique :

1. **Installer Xvfb & Chrome sur la VM** :
   ```bash
   sudo apt update && sudo apt install -y xvfb
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt -f install -y
   ```

2. **Copier votre projet (avec le profil déjà authentifié)** :
   ```bash
   scp -r /home/ahmed/IdeaProjects/browser-use-demo user@ip-vm:~/browser-use-demo
   ```

3. **Lancer la surveillance en continu** :
   ```bash
   nohup xvfb-run -a python main.py tls --interval 15 --heartbeat 24 > monitor.log 2>&1 &
   ```
