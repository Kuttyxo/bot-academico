# 🐳 Dockerfile para el Bot Académico
# Este archivo le dice a la nube cómo construir la "computadora virtual" para tu bot.

# 1. Usamos una versión ligera de Python 3.10 (como un Windows mini)
FROM python:3.10-slim

# 2. Creamos una carpeta dentro de esa computadora para guardar el bot
WORKDIR /app

# 3. Copiamos el archivo de "ingredientes" (librerías necesarias)
COPY requirements.txt .

# 4. Instalamos esos ingredientes
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos todo el resto del código del bot a la carpeta
COPY . .

# 6. Comando para encender el bot cuando la máquina arranque
CMD ["python", "main.py"]
