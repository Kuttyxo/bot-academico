# 🎓 Bot Académico (Telegram + Notion)

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-API-000000?style=for-the-badge&logo=notion&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)

Un asistente de estudio personal e inteligente que conecta tu agenda de **Notion** con **Telegram**. Gestiona tus exámenes, registra tus sesiones de estudio, mantén el foco con Pomodoro y visualiza tu progreso con gamificación.

## ✨ Características Principales

### 📅 Integración con Notion
*   **Próximos Exámenes**: Consulta tus exámenes futuros directamente desde el chat con `/proximos`.
*   **Detalles Instantáneos**: Recibe fecha, materia, contenido y un **link directo** a la página de Notion.
*   **Recordatorios Automáticos**: Notificaciones diarias a las 08:00 AM si tienes exámenes cerca (configurable).

### 📚 Study Tracker (Seguimiento de Estudio)
*   **Metas Semanales**: Define cuántas sesiones quieres estudiar por materia (`/meta Algebra 3`).
*   **Registro Rápido**: Registra sesiones con un clic usando botones interactivos (`/estudie`).
*   **Progreso Visual**: Visualiza tu avance con barras de progreso y porcentajes (`/progreso`).

### 🍅 Productividad & Gamificación
*   **Pomodoro Timer**: Inicia temporizadores de 25 o 50 minutos para sesiones de enfoque profundo (`/pomodoro`).
*   **Rachas (Streaks)**: Mantén tu "fuego" 🔥 estudiando todos los días.
*   **Reportes Semanales**: Recibe un resumen automático de tu rendimiento cada domingo.
*   **Frases Motivacionales**: Inspiración al consultar tus tareas o terminar sesiones.

## 🛠️ Tecnologías

*   **Python 3.11**
*   **python-telegram-bot**: Interacción con la API de Telegram.
*   **notion-client**: Conexión con la base de datos de Notion.
*   **APScheduler**: Manejo de tareas programadas (check diario, reportes semanales).
*   **Docker**: Contenerización para despliegue fácil.

---

## 🚀 Instalación y Uso Local

### Requisitos
1.  Python 3.8+
2.  Una base de datos en Notion (con columnas: `Nombre`, `Fecha`, `Materia`).
3.  Un Bot de Telegram (creado con @BotFather).

### Pasos

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/TU_USUARIO/bot-academico.git
    cd bot-academico
    ```

2.  **Crear entorno virtual**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno**:
    Crea un archivo `.env` en la raíz y añade:
    ```env
    TELEGRAM_TOKEN=tu_token_de_telegram
    NOTION_TOKEN=tu_token_de_notion
    NOTION_DB_ID=id_de_tu_base_de_notion
    TZ=America/Bogota
    ```

5.  **Ejecutar**:
    ```bash
    python main.py
    ```

## 🐳 Despliegue con Docker

El proyecto incluye un `Dockerfile` optimizado.

```bash
docker build -t bot-academico .
docker run -d --env-file .env bot-academico
```

Para desplegar en la nube (Koyeb, Railway, Render), consulta la [Guía de Despliegue](Guia_Despliegue.md).

---

## 🤖 Comandos del Bot

| Comando | Descripción |
| :--- | :--- |
| `/start` | Inicia el bot y verifica la conexión. |
| `/proximos` | Muestra exámenes pendientes (opcional: `/proximos materia`). |
| `/estudie` | Registra una sesión de estudio (interactivo). |
| `/meta` | Configura meta semanal (`/meta materia numero`). |
| `/progreso` | Muestra tu avance semanal y racha actual. |
| `/plan` | Genera un plan de estudio sugerido para 2 semanas. |
| `/pomodoro` | Inicia un temporizador de concentración. |
| `/config` | Configura la hora de tus recordatorios diarios. |
| `/help` | Muestra la lista de ayuda. |

---

## 📄 Estructura del Proyecto

```
Bot_Academico/
├── src/
│   ├── services/
│   │   ├── notion_service.py   # Lógica de Notion
│   │   ├── telegram_bot.py     # Comandos y handlers de Telegram
│   │   └── data_service.py     # Persistencia de datos (metas, sesiones)
│   └── utils/
│       └── quotes.py           # Frases motivacionales
├── main.py                     # Punto de entrada y Scheduler
├── Dockerfile                  # Configuración Docker
├── requirements.txt            # Dependencias
└── .env                        # Variables (no incluido en repo)
```

## 📝 Licencia
MIT
