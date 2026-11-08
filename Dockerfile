FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Empêche la mise en mémoire tampon de Python pour afficher les logs en temps réel
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Installation de Google Chrome officiel et de Xvfb
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    xvfb \
    ca-certificates \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code source
COPY . .

# Préparation des dossiers requis
RUN mkdir -p screenshots tls_user_profile profiles prompts

# Exécution sous Xvfb (écran virtuel 1080p) pour contourner la détection Cloudflare Headless
ENTRYPOINT ["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24", "python", "main.py"]
CMD ["tls", "--interval", "15", "--heartbeat", "24"]
