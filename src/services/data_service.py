
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

DATA_FILE = "user_data.json"

def _load_data() -> Dict[str, Any]:
    """Carga los datos del archivo JSON. Si no existe, devuelve dict vacío."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_data(data: Dict[str, Any]):
    """Guarda (sobreescribe) el archivo JSON con los nuevos datos."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _migrate_data(data: Dict[str, Any]):
    """
    Sistema de Migración:
    Asegura que los datos antiguos sean compatibles con las nuevas versiones del bot.
    - Convierte metas simples (int) a diccionario separado por materia.
    - Convierte sesiones simples (string fecha) a objetos detallados.
    """
    changed = False
    for chat_id, user_data in data.items():
        # Migrar Meta: de int a dict
        if "study_goal" in user_data and isinstance(user_data["study_goal"], int):
            old_goal = user_data.pop("study_goal")
            if "goals" not in user_data:
                user_data["goals"] = {}
            if "General" not in user_data["goals"]:
                user_data["goals"]["General"] = old_goal
            changed = True
            
        # Migrar Sesiones: de list[str] a list[dict]
        if "study_sessions" in user_data:
            new_sessions = []
            for s in user_data["study_sessions"]:
                if isinstance(s, str):
                    new_sessions.append({"date": s, "subject": "General"})
                else:
                    new_sessions.append(s)
            user_data["sessions"] = new_sessions
            user_data.pop("study_sessions")
            changed = True
            
    if changed:
        _save_data(data)

def set_study_goal(chat_id: int, goal: int, subject: str = "General"):
    """Establece la meta semanal para una materia específica."""
    data = _load_data()
    _migrate_data(data)
    
    str_id = str(chat_id)
    if str_id not in data:
        data[str_id] = {"goals": {}, "sessions": []}
    
    if "goals" not in data[str_id]:
         data[str_id]["goals"] = {}
         
    data[str_id]["goals"][subject] = goal
    _save_data(data)

def log_study_session(chat_id: int, subject: str = "General") -> bool:
    """
    Registra una sesión de estudio para HOY.
    Devuelve True si es un nuevo registro, False si ya existía para hoy.
    """
    data = _load_data()
    _migrate_data(data)
    
    str_id = str(chat_id)
    today_iso = date.today().isoformat()
    
    if str_id not in data:
        data[str_id] = {"goals": {}, "sessions": []}
        
    sessions = data[str_id].get("sessions", [])
    
    # Evitar duplicados para la misma materia el mismo día
    for s in sessions:
        if s["date"] == today_iso and s["subject"] == subject:
            return False
        
    sessions.append({"date": today_iso, "subject": subject})
    data[str_id]["sessions"] = sessions
    _save_data(data)
    return True

def get_weekly_progress(chat_id: int) -> Dict[str, Any]:
    """Calcula el progreso de la semana actual por materia."""
    data = _load_data()
    _migrate_data(data)
    
    str_id = str(chat_id)
    user_data = data.get(str_id, {})
    
    goals = user_data.get("goals", {})
    sessions = user_data.get("sessions", [])
    
    # Calcular inicio y fin de la semana (Lunes a Domingo)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Estructura de respuesta
    progress = {}
    
    # Inicializar con las metas existentes
    for subj, goal in goals.items():
        progress[subj] = {"goal": goal, "current": 0, "percentage": 0}
        
    # Contar sesiones que caen en esta semana
    for s in sessions:
        s_date = date.fromisoformat(s["date"])
        subj = s.get("subject", "General")
        
        if start_of_week <= s_date <= end_of_week:
            if subj not in progress:
                 progress[subj] = {"goal": 0, "current": 0, "percentage": 0}
            progress[subj]["current"] += 1
            
    # Calcular porcentajes
    for subj in progress:
        g = progress[subj]["goal"]
        c = progress[subj]["current"]
        if g > 0:
            progress[subj]["percentage"] = int(c / g * 100)
            
    return progress

def get_current_streak(chat_id: int) -> int:
    """Calcula la 'Racha' (días consecutivos estudiando) hasta hoy/ayer."""
    data = _load_data()
    _migrate_data(data)
    
    str_id = str(chat_id)
    user_data = data.get(str_id, {})
    sessions = user_data.get("sessions", [])
    
    # Obtener lista de fechas únicas ordenadas (más reciente primero)
    dates = sorted(list(set([s["date"] for s in sessions])), reverse=True)
    
    if not dates:
        return 0
        
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    
    streak = 0
    current_check = date.today()
    
    # Verificar si la racha está viva (se estudió hoy o ayer)
    # Si la última sesión fue antes de ayer, la racha se rompió -> 0
    last_session_date = dates[0]
    if last_session_date != today_str and last_session_date != yesterday_str:
        return 0
        
    # Contar hacia atrás
    # Si hoy no se ha estudiado aún, empezamos a contar desde ayer
    if today_str not in dates:
        current_check = date.today() - timedelta(days=1)
    
    # Bucle de seguridad (max 365 días)
    for _ in range(365): 
        check_str = current_check.isoformat()
        if check_str in dates:
            streak += 1
            current_check -= timedelta(days=1)
        else:
            break
            
    return streak
