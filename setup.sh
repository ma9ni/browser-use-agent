#!/usr/bin/env bash
set -e

echo "🚀 [Browser-Use Agent] Installation et configuration automatique..."

# 1. Vérification de Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 n'est pas installé. Veuillez installer python3 et python3-venv."
    exit 1
fi

# 2. Création de l'environnement virtuel
if [ ! -d ".venv" ]; then
    echo "📦 Création du venv Python..."
    python3 -m venv .venv || uv venv .venv
fi

# 3. Activation et installation des dépendances
echo "📥 Installation des packages Python..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Installation des navigateurs Playwright et dépendances système
echo "🌐 Installation de Playwright Chromium..."
playwright install chromium

if command -v sudo &>/dev/null; then
    echo "🔧 Installation des dépendances système Linux pour Chromium..."
    sudo playwright install-deps chromium || true
else
    echo "⚠️ Sudo non disponible, tentative d'installation des deps..."
    playwright install-deps chromium || true
fi

# 5. Préparation du .env
if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env depuis .env.example..."
    cp .env.example .env
    echo "⚠️ Pensez à renseigner votre GEMINI_API_KEY ou OPENROUTER_API_KEY dans .env !"
fi

echo ""
echo "✅ Installation terminée avec succès !"
echo "Pour exécuter l'agent :"
echo "    source .venv/bin/activate"
echo "    python run_agent.py --headless"
