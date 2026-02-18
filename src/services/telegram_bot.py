import os
import logging
from datetime import datetime, date, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from src.services.notion_service import NotionClient
from src.utils.quotes import get_random_quote
from src.services.data_service import set_study_goal, log_study_session, get_weekly_progress, get_current_streak

# Configure logging if not already done in main
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

import json

# Archivo para almacenar IDs de chat y configuraciones
# Esquema: {"chat_id": {"time": "08:00"}}
CHAT_IDS_FILE = "chat_ids.json"

def get_subscriptions():
    """Devuelve un diccionario de suscripciones: {chat_id: {'time': 'HH:MM'}}"""
    if not os.path.exists(CHAT_IDS_FILE):
        return {}
    try:
        with open(CHAT_IDS_FILE, "r") as f:
            data = json.load(f)
            # Migración: Si la data antigua era una lista [id1, id2], la convertimos a dict
            if isinstance(data, list):
                new_data = {str(uid): {"time": "08:00"} for uid in data}
                save_subscriptions(new_data)
                return new_data
            return data
    except (json.JSONDecodeError, IOError):
        return {}

def save_subscriptions(data):
    """Guarda el diccionario de suscripciones en el archivo JSON."""
    with open(CHAT_IDS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def register_user(chat_id):
    """Registra un nuevo usuario con la hora por defecto (08:00)."""
    data = get_subscriptions()
    str_id = str(chat_id)
    if str_id not in data:
        data[str_id] = {"time": "08:00"}
        save_subscriptions(data)

def set_reminder_time(chat_id, time_str):
    """Actualiza la hora de recordatorio para un usuario específico."""
    data = get_subscriptions()
    str_id = str(chat_id)
    if str_id not in data:
        data[str_id] = {} # Debería estar registrado, pero por seguridad lo creamos
    
    data[str_id]["time"] = time_str
    save_subscriptions(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para el comando /start. Inicia la interacción."""
    user = update.effective_user.first_name
    chat_id = update.effective_chat.id
    
    # Guarda el Chat ID con la configuración por defecto
    register_user(chat_id)
    logging.info(f"Nuevo usuario suscrito: {user} ({chat_id})")

    await update.message.reply_text(
        f"¡Hola {user}! 👋 Soy tu Bot Académico.\n\n"
        "Estoy conectado a tu Notion para recordarte tus exámenes y entregas. 🧠\n\n"
        "He guardado tu ID para enviarte recordatorios diarios a las 8:00 AM. ⏰\n\n"
        "Usa /proximos para ver qué tienes pendiente. 📅"
    )

async def proximos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para el comando /proximos. Lista tareas pendientes."""
    # Verificar si hay argumentos (filtro de búsqueda)
    subject_filter = " ".join(context.args) if context.args else None
    
    if subject_filter:
        await update.message.reply_text(f"🔎 Buscando exámenes de '{subject_filter}'...")
    else:
        await update.message.reply_text("🔎 Consultando Notion... dame un segundo.")
    
    try:
        # Instanciamos el cliente para esta petición específica
        client = NotionClient()
        exams = client.get_upcoming_exams(subject_filter)
        
        if not exams:
            if subject_filter:
                await update.message.reply_text(f"¡No encontré nada para '{subject_filter}'! 🎉 (O quizás no existe esa materia)")
            else:
                await update.message.reply_text("¡Eres libre! No hay pruebas pronto. 🎉 Disfruta tu tiempo.")
            return

        title_msg = f"📅 **Próximos para '{subject_filter}':**\n\n" if subject_filter else "📅 **Próximos Exámenes y Entregas:**\n\n"
        message = title_msg
        
        for exam in exams:
            title = exam.get('titulo', 'Sin título')
            date_str = exam.get('fecha', 'Sin fecha')
            subject = exam.get('materia', 'General')
            content = exam.get('contenido', '')
            
            message += f"📚 *{subject}*\n"
            message += f"📝 {title}\n"
            if content:
                message += f"ℹ️ _{content}_\n"
            message += f"⏰ {date_str}\n"
            if exam.get('url'):
                message += f"🔗 [Ver en Notion]({exam.get('url')})\n"
            message += "-------------------------\n"
            
        message += f"\n{get_random_quote()}"
        
        await update.message.reply_markdown(message)
        
    except ValueError as ve:
        # Manejo de error si faltan variables de entorno
        await update.message.reply_text("⚠️ Error de configuración: Faltan claves en el archivo .env.")
        logging.error(f"Error de configuración: {ve}")
    except Exception as e:
        await update.message.reply_text(f"❌ Hubo un error al intentar conectar con Notion: {e}")
        logging.error(f"Error en /proximos: {e}")

async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para /config HH:MM. Cambia hora de notificación."""
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text("⚠️ Uso: /config HH:MM (ej. /config 10:00)")
        return
    
    time_str = context.args[0]
    
    # Validar formato
    try:
        # Check si es una hora válida
        dt = datetime.strptime(time_str, "%H:%M")
        normalized_time = dt.strftime("%H:%M") # Asegurar formato 00:00
        set_reminder_time(chat_id, normalized_time)
        await update.message.reply_text(f"✅ Recordatorio configurado para las **{normalized_time}** diariamente.")
    except ValueError:
        await update.message.reply_text("❌ Formato inválido. Usa HH:MM (24 horas). Ej: 08:00 o 18:30")

async def meta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para /meta. Fija objetivos de estudio semanales."""
    chat_id = update.effective_chat.id
    
    # Modo Manual/Legado: /meta [Materia] [Numero]
    if context.args:
        try:
            if context.args[-1].isdigit():
                goal = int(context.args[-1])
                if len(context.args) > 1:
                    subject = " ".join(context.args[:-1])
                else:
                    subject = "General"
                set_study_goal(chat_id, goal, subject)
                await update.message.reply_text(f"🎯 ¡Meta fijada! **{subject}**: {goal} sesiones/semana.")
            else:
                await update.message.reply_text("❌ El último argumento debe ser un número.")
        except ValueError:
            await update.message.reply_text("❌ Error de formato.")
        return

    # Modo Interactivo
    await update.message.reply_text("⏳ Cargando materias...")
    try:
        client = NotionClient()
        exams = client.get_upcoming_exams()
        
        keyboard = []
        for exam in exams[:5]:
            title = exam.get('titulo', 'Tarea')
            cb_data = f"META_SUBJ:{title}"[:64]
            keyboard.append([InlineKeyboardButton(f"🎯 {title}", callback_data=cb_data)])
            
        keyboard.append([InlineKeyboardButton("🎯 General", callback_data="META_SUBJ:General")])
        
        await update.message.reply_text("¿Para qué materia quieres fijar una meta?", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"❌ Error Notion: {e}")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# ... (omitted)

async def estudie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para /estudie. Registra sesiones de estudio."""
    chat_id = update.effective_chat.id
    
    # Si hay argumentos, usar registro directo (Modo Legado)
    if context.args:
        subject = " ".join(context.args)
        is_new = log_study_session(chat_id, subject)
        
        if is_new:
            progress_data = get_weekly_progress(chat_id)
            p = progress_data.get(subject, {'current': 0, 'goal': 0, 'percentage': 0})
            current = p['current']
            goal = p['goal']
            percent = p['percentage']
            
            msg = f"✅ ¡Bien hecho! Sesión de **{subject}** registrada.\n"
            if goal > 0:
                msg += f"🔥 Llevas {current}/{goal} ({percent}%)"
            else:
                msg += f"🔥 Llevas {current} sesiones."
            await update.message.reply_markdown(msg)
        else:
            await update.message.reply_text(f"😅 Ya registraste **{subject}** hoy.")
        return

    # Modo Interactivo: Buscar opciones en Notion
    await update.message.reply_text("⏳ Buscando entregas pendientes...")
    
    try:
        client = NotionClient()
        exams = client.get_upcoming_exams()
        
        keyboard = []
        # Crear botones para los próximos 5 exámenes
        for exam in exams[:5]:
            title = exam.get('titulo', 'Tarea')
            # Callback data: "LOG:<Title>"
            # Truncamos título para evitar límite de 64 caracteres
            cb_data = f"LOG:{title}"[:64] 
            keyboard.append([InlineKeyboardButton(f"📝 {title}", callback_data=cb_data)])
            
        # Opciones genéricas
        keyboard.append([InlineKeyboardButton("📚 Estudio General", callback_data="LOG:General")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("¿Qué estudiaste hoy? Selecciona una opción:", reply_markup=reply_markup)
        
    except Exception as e:
        logging.error(f"Error buscando botones: {e}")
        await update.message.reply_text("❌ Error con Notion. Usa `/estudie [Materia]` manualmente.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja TODOS los clics en botones (LOG, META, PLAN, POMO)."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = update.effective_chat.id
    
    # --- REGISTRO DE ESTUDIO (LOG) ---
    if data.startswith("LOG:"):
        subject = data.split("LOG:")[1]
        is_new = log_study_session(chat_id, subject)
        
        streak = get_current_streak(chat_id)
        if streak > 1:
            streak_msg = f"\n🔥 **¡Racha de {streak} días!** ¡Sigue así!"
        elif streak == 1:
             streak_msg = "\n🔥 ¡Primer día de la racha!"
        else:
            streak_msg = ""
        
        if is_new:
            progress_data = get_weekly_progress(chat_id)
            p = progress_data.get(subject, {'current': 0, 'goal': 0, 'percentage': 0})
            current = p['current']
            msg = f"✅ ¡Registrado! **{subject}**\n📚 Llevas {current} sesiones.{streak_msg}"
        else:
            msg = f"😅 Ya habías registrado **{subject}** hoy.{streak_msg}"
        await query.edit_message_text(text=msg, parse_mode='Markdown')

    # --- META: SELECCIONAR MATERIA ---
    elif data.startswith("META_SUBJ:"):
        subject = data.split("META_SUBJ:")[1]
        # Mostrar botones de números del 1 al 7
        keyboard = []
        row1 = [InlineKeyboardButton(str(i), callback_data=f"META_SET:{subject}:{i}") for i in range(1, 4)]
        row2 = [InlineKeyboardButton(str(i), callback_data=f"META_SET:{subject}:{i}") for i in range(4, 7)]
        keyboard.append(row1)
        keyboard.append(row2)
        
        await query.edit_message_text(f"🎯 Meta semanal para **{subject}**:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # --- META: GUARDAR OBJETIVO ---
    elif data.startswith("META_SET:"):
        parts = data.split(":")
        subject = parts[1]
        goal = int(parts[2])
        set_study_goal(chat_id, goal, subject)
        await query.edit_message_text(f"✅ ¡Listo! Meta para **{subject}**: {goal} veces/semana.", parse_mode='Markdown')

    # --- PLAN DE ESTUDIO (GENERAR) ---
    elif data.startswith("PLAN_SEL:") or data == "PLAN_ALL":
        await query.edit_message_text("⚡ Generando plan...")
        
        subject_filter = None
        if data.startswith("PLAN_SEL:"):
            subject_filter = data.split("PLAN_SEL:")[1]
            
        try:
            client = NotionClient()
            all_exams = client.get_upcoming_exams()
            target_exams = []
            
            # Filtramos si el usuario pidió uno específico
            if subject_filter:
                for ex in all_exams:
                    if ex.get('titulo') == subject_filter:
                        target_exams.append(ex)
            else:
                target_exams = all_exams # Plan Global
            
            if not target_exams:
                await query.edit_message_text("❌ No encontré el examen solicitado.")
                return

            message = "📅 **Plan de Estudio**\n\n"
            today = date.today()
            
            for exam in target_exams:
                title = exam.get('titulo', 'Sin título')
                date_str = exam.get('fecha')
                if not date_str: continue
                
                exam_date = date.fromisoformat(date_str)
                days_until = (exam_date - today).days
                
                start_week_2 = exam_date - timedelta(days=7)
                
                message += f"🎓 **{title}**\n🗓 {date_str} (en {days_until} días)\n\n"
             
                if days_until > 14:
                    message += f"**Semana 1** (hasta {start_week_2.strftime('%d-%m')}): 📖 Teoría\n"
                    message += f"- Lee la bibliografía.\n- Haz mapas conceptuales.\n- Revisa 'Contenido' en Notion.\n\n"
                    message += f"**Semana 2**: ✍️ Práctica Intensiva\n"
                    message += f"- Realiza ejercicios tipo prueba.\n- Simula un examen real.\n- Repasa errores.\n"
                elif days_until > 1:
                    # Dividimos los días restantes a la mitad
                    mid_point = days_until // 2
                    today_formatted = date.today().strftime('%d-%m')
                    mid_date = (date.today() + timedelta(days=mid_point)).strftime('%d-%m')
                    
                    message += f"⚡ **Plan Intensivo ({days_until} días)**\n"
                    message += f"📅 **Días 1-{mid_point}** (Hoy - {mid_date}): 📖 **Repaso Conceptual**\n"
                    message += f"- Revisa tus notas y resúmenes.\n- Asegura los conceptos base.\n\n"
                    message += f"📅 **Días {mid_point+1}-{days_until}**: 🧨 **Full Ejercicios**\n"
                    message += f"- Resuelve exámenes pasados.\n- Cronometra tu tiempo.\n"
                elif days_until == 1:
                    message += f"🚨 **Plan de Emergencia (24h)**\n"
                    message += f"- 🛑 No intentes aprender nada nuevo.\n"
                    message += f"- 🔄 Repasa solo lo que ya sabes para asegurarlo.\n"
                    message += f"- 💤 Duerme bien hoy. Es lo más importante.\n"
                else:
                    message += "🏁 **¡Es hoy!**\n🍀 ¡Mucho éxito! Tú sabes lo que sabes. Confía en ti.\n"
                
                message += "-------------------------\n"
             
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error Plan: {e}")
            await context.bot.send_message(chat_id=chat_id, text="❌ Error generando el plan.")
            
    # --- POMODORO start ---
    elif data.startswith("POMO:"):
        minutes = int(data.split("POMO:")[1])
        
        # Programamos el callback usando JobQueue
        context.job_queue.run_once(pomodoro_callback, minutes * 60, chat_id=chat_id, data=minutes)
        await query.edit_message_text(f"🍅 **Modo Concentración Iniciado**\n⏳ {minutes} minutos. ¡A trabajar!\n(Te avisaré cuando termine)")

async def pomodoro_callback(context: ContextTypes.DEFAULT_TYPE):
    """Callback: Envia alarma cuando el Pomodoro termina."""
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"⏰ **¡DING DING!** Tiempo cumplido ({job.data} min).\n☕ Tómate un descanso de 5 minutos.")

async def pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para /pomodoro. Inicia timer."""
    keyboard = [
        [InlineKeyboardButton("🍅 25 min", callback_data="POMO:25")],
        [InlineKeyboardButton("🍅 50 min", callback_data="POMO:50")]
    ]
    await update.message.reply_text("🍅 **Modo Concentración**\nElige tu bloque de tiempo:", reply_markup=InlineKeyboardMarkup(keyboard))

async def progreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para /progreso. Muestra reporte semanal."""
    chat_id = update.effective_chat.id
    progress_data = get_weekly_progress(chat_id)
    streak = get_current_streak(chat_id)
    
    streak_header = f"🔥 **Racha Actual: {streak} días seguidos**\n\n" if streak > 1 else ""
    
    if not progress_data:
        await update.message.reply_text(f"{streak_header}📊 Aún no tienes metas ni sesiones registradas. ¡Empieza con /meta!")
        return

    msg = f"{streak_header}📊 **Tu Progreso Semanal**\n\n"
    
    total_sessions = 0
    
    for subject, p in progress_data.items():
        current = p['current']
        goal = p['goal']
        percent = p['percentage']
        total_sessions += current
        
        msg += f"📘 **{subject}**\n"
        if goal > 0:
            # Barra visual de progreso
            bar_len = 8
            filled = int(bar_len * percent / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            msg += f"[{bar}] {current}/{goal} ({percent}%)\n\n"
        else:
            msg += f"📚 {current} sesiones (Sin meta)\n\n"
            
    msg += f"🔥 **Total Semanal:** {total_sessions} sesiones"
        
    await update.message.reply_markdown(msg)

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para /plan. Genera plan de estudio estratégico."""
    await update.message.reply_text("⏳ Buscando exámenes...")
    try:
        client = NotionClient()
        exams = client.get_upcoming_exams()
        
        if not exams:
             await update.message.reply_text("🎉 No tienes exámenes próximos.")
             return

        keyboard = []
        for exam in exams[:5]:
            title = exam.get('titulo', 'Examen')
            cb_data = f"PLAN_SEL:{title}"[:64]
            keyboard.append([InlineKeyboardButton(f"📅 {title}", callback_data=cb_data)])
            
        keyboard.append([InlineKeyboardButton("🌎 Plan Global (Todo)", callback_data="PLAN_ALL")])
        
        await update.message.reply_text("¿Para qué examen quieres el plan?", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

def create_bot_application():
    """Crea y configura la aplicación de Telegram."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN must be set in environment variables.")
        
    application = ApplicationBuilder().token(token).build()
    
    # Registrar comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proximos", proximos))
    application.add_handler(CommandHandler("config", config))
    application.add_handler(CommandHandler("meta", meta))
    application.add_handler(CommandHandler("estudie", estudie))
    application.add_handler(CommandHandler("progreso", progreso))
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CommandHandler("pomodoro", pomodoro))
    
    # Registrar manejador de botones (Callbacks)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    return application
