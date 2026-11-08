FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Empêche la mise en mémoire tampon de Python pour afficher les logs en temps réel
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Installation des dépendances Python et mise à jour de Chromium si nécessaire
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

# Copie du reste du code source (filtré par .dockerignore)
COPY . .

# Préparation des dossiers requis
RUN mkdir -p screenshots tls_user_profile profiles prompts

# Commande par défaut (séparée sous forme de tableau JSON valide)
ENTRYPOINT ["python", "main.py"]
CMD ["tls", "--interval", "15", "--heartbeat", "24", "--headless"]
