import os
import asyncio
import logging
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# APScheduler: Librería para ejecutar tareas programadas (check diario)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Importaciones de módulos del proyecto
from src.services.telegram_bot import create_bot_application, get_subscriptions
from src.services.notion_service import NotionClient
from src.services.data_service import get_weekly_progress, get_current_streak
from src.utils.quotes import get_random_quote

# Configuración básica para ver logs en la consola
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def scheduled_check(application):
    """
    Función que se ejecuta cada minuto para verificar si hay usuarios que deben ser notificados.
    Compara la hora configurada por el usuario con la hora actual.
    """
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    logging.info(f"Ejecutando chequeo programado a las {current_time_str}")
    
    # 1. Obtener lista de usuarios suscritos y sus horas preferidas
    subscriptions = get_subscriptions()
    if not subscriptions:
        return

    # 2. Filtrar usuarios que deben ser notificados AHORA MISMO
    users_to_notify = []
    for chat_id, prefs in subscriptions.items():
        user_time = prefs.get("time", "08:00")
        if user_time == current_time_str:
            users_to_notify.append(chat_id)
            logging.info(f"¡Hora de notificar al usuario {chat_id}!")
            
    if not users_to_notify:
        return # Nadie programado para esta hora

    logging.info(f"Notificando a {len(users_to_notify)} usuarios...")

    try:
        # 3. Obtener exámenes desde Notion (Optimizamos haciendo una sola consulta para todos)
        client = NotionClient()
        all_upcoming = client.get_upcoming_exams()
        
        # Filtrar solo eventos para los próximos 5 días
        today = date.today()
        limit_date = today + timedelta(days=5)
        
        imminent_exams = []
        for exam in all_upcoming:
            exam_date_str = exam.get('fecha')
            if not exam_date_str:
                continue
            
            try:
                exam_date = date.fromisoformat(exam_date_str)
            except ValueError:
                continue
            
            if today <= exam_date <= limit_date:
                imminent_exams.append(exam)
        
        if not imminent_exams:
            return # No hay nada urgente que avisar

        # 4. Construir el mensaje de alerta
        message = "🚨 **ALERTA: Exámenes en los próximos 5 días** 🚨\n\n"
        for exam in imminent_exams:
            title = exam.get('titulo', 'Sin título')
            d_str = exam.get('fecha', '-')
            subj = exam.get('materia', 'General')
            content = exam.get('contenido', '')
            
            d_date = date.fromisoformat(d_str)
            days_left = (d_date - today).days
            day_msg = "HOY" if days_left == 0 else f"en {days_left} días"
            
            message += f"⏳ **{subj}** ({day_msg})\n"
            message += f"📝 {title}\n"
            if content:
                message += f"ℹ️ _{content}_\n"
            if exam.get('url'):
                 message += f"🔗 [Ver en Notion]({exam.get('url')})\n"
            message += "-------------------------\n"
            
        message += f"\n{get_random_quote()}"
            
        # 5. Enviar mensaje a cada usuario programado
        for chat_id in users_to_notify:
            try:
                await application.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Error enviando mensaje a {chat_id}: {e}")

    except Exception as e:
        logging.error(f"Error durante el chequeo programado: {e}")

async def weekly_report_job(application):
    """
    Reporte Semanal Automático (Domingo 20:00).
    Envía un resumen del progreso a todos los usuarios suscritos.
    """
    logging.info("⏳ Ejecutando Reporte Semanal...")
    subscriptions = get_subscriptions()
    
    if not subscriptions:
        logging.info("No hay usuarios para el reporte semanal.")
        return

    for chat_id in subscriptions.keys():
        try:
            # Convertir chat_id a int para las funciones de data_service
            cid = int(chat_id)
            progress = get_weekly_progress(cid)
            streak = get_current_streak(cid)
            
            # Enviaremos resumen siempre para mantener engagement.
            msg = "📉 **Resumen de tu Semana** (Automático)\n\n"
            
            if streak > 0:
                msg += f"🔥 **Racha Activa**: {streak} días\n"
            else:
                msg += f"❄️ **Racha**: 0 días (¡Empieza mañana!)\n"
                
            total = 0
            details = ""
            for subj, data in progress.items():
                c = data['current']
                if c > 0:
                    details += f"- {subj}: {c} sesiones\n"
                    total += c
            
            msg += f"📚 **Total Sesiones**: {total}\n\n"
            
            if total > 0:
                msg += "Detalle:\n" + details
                msg += "\n🎉 ¡Buen esfuerzo! Descansa y prepárate para la próxima. 💪"
            else:
                msg += "❌ No registraste actividad esta semana.\n¡La próxima será mejor! 👊"
            
            await application.bot.send_message(chat_id=cid, text=msg, parse_mode='Markdown')
            logging.info(f"Reporte semanal enviado a {cid}")
            
        except Exception as e:
            logging.error(f"Error enviando reporte semanal a {chat_id}: {e}")

def main():
    # Cargar variables de entorno del archivo .env
    load_dotenv()
    if not os.getenv("TELEGRAM_TOKEN") or not os.getenv("NOTION_TOKEN") or not os.getenv("NOTION_DB_ID"):
        logging.error("Faltan variables de entorno. Por favor revisa el archivo .env.")
        return

    print("Bot Académico iniciando...")
    
    # Crear la aplicación del Bot
    application = create_bot_application()
    
    # Iniciar el planificador de tareas (Scheduler)
    scheduler = AsyncIOScheduler()
    
    # Programar el chequeo para ejecutarse cada minuto (CronTrigger)
    scheduler.add_job(
        scheduled_check, 
        CronTrigger(minute='*'), # Se dispara en el minuto 0, 1, 2... de cada hora
        args=[application]
    )
    
    # NUEVO: Reporte Semanal (Domingos a las 20:00)
    scheduler.add_job(
        weekly_report_job,
        CronTrigger(day_of_week='sun', hour=20, minute=0),
        args=[application]
    )
    
    # Hook para iniciar el scheduler cuando arranque el bot
    async def on_startup(app):
        scheduler.start()
        logging.info("Scheduler iniciado correctamente.")

    application.post_init = on_startup
    
    # --- RENDER HEALTH CHECK SERVER ---
    # Render necesita que la app escuche en un puerto para considerarla "viva".
    # Como python-telegram-bot usa Polling (no Webhook), creamos un servidor dummy.
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is alive!")

    def start_health_server():
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logging.info(f"Health check server listening on port {port}")
        server.serve_forever()

    # Iniciar servidor en hilo aparte
    threading.Thread(target=start_health_server, daemon=True).start()
    # ----------------------------------

    # Iniciar el bot en modo polling (escucha infinita)
    # Se bloquea aquí, por eso el server va en hilo aparte.
    application.run_polling()

if __name__ == "__main__":
    main()
