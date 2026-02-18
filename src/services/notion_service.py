import os
from datetime import date
from typing import List, Dict, Any, Optional
from notion_client import Client
import logging

class NotionClient:
    def __init__(self):
        # Cargar y limpiar tokens (eliminar espacios en blanco por si acaso)
        self.token = os.getenv("NOTION_TOKEN", "").strip()
        self.database_id = os.getenv("NOTION_DB_ID", "").strip()
        
        if not self.token or not self.database_id:
            raise ValueError("Faltan NOTION_TOKEN y NOTION_DB_ID en el archivo .env.")

        # Limpiar el ID de la Base de Datos (por si el usuario pegó el link completo)
        if "notion.so" in self.database_id:
            try:
                self.database_id = self.database_id.split("?")[0].split("/")[-1]
            except Exception:
                pass 
            self.database_id = self.database_id.strip() # Asegurar limpieza
            logging.info(f"ID de base de datos saneado: {self.database_id}")
            
        self.client = Client(auth=self.token)
        
        # Mapeo de nombres de propiedades en Notion
        # Si cambias los nombres en Notion, actualízalos aquí.
        self.prop_date = "Date"
        self.prop_title = "Name"
        self.prop_subject = "Ramo"
        self.prop_content = "Contenido" 

    def get_upcoming_exams(self, subject_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene exámenes desde Notion con fecha HOY o FUTURA.
        Opcional: filtra por materia (coincidencia parcial sin distinción mayúsculas/minúsculas).
        Devuelve lista de dicts: [{'titulo': '...', 'fecha': 'YYYY-MM-DD', 'materia': '...', 'contenido': '...'}]
        """
        today = date.today().isoformat()
        
        query_filter = {
            "property": self.prop_date,
            "date": {
                "on_or_after": today
            }
        }
        
        # Ordenar por fecha ascendente (lo más proximo primero)
        sorts = [
            {
                "property": self.prop_date,
                "direction": "ascending"
            }
        ]

        # Usamos httpx directo para evitar problemas con la librería oficial en ciertos entornos
        import httpx
        
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        logging.info(f"Consultando Notion URL: {url}")
        
        try:
            with httpx.Client() as http_client:
                response = http_client.post(
                    url,
                    headers=headers,
                    json={
                        "filter": query_filter,
                        "sorts": sorts
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
            results = data.get("results", [])
            logging.info(f"Notion encontró {len(results)} resultados.")
            
            if results:
                # Debug: Imprimir propiedades disponibles del primer resultado para troubleshooting
                first_props = results[0].get("properties", {}).keys()
                logging.info(f"Propiedades disponibles en Notion DB: {list(first_props)}")

            exams = []
            for page in results:
                exam_data = self._parse_page(page)
                if exam_data:
                    # Filtrar por materia si se solicitó
                    if subject_filter:
                        materia = exam_data.get('materia', '').lower()
                        if subject_filter.lower() not in materia:
                            continue # Saltar si no coincide
                            
                    exams.append(exam_data)
                else:
                    logging.warning(f"No se pudo analizar la página: {page.get('id')}")
                    
            return exams

        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            logging.error(f"Error HTTP Notion: {error_details}")
            # Lanzar excepción con detalles para que el bot la muestre
            raise Exception(f"Error API Notion: {error_details}")
        except Exception as e:
            logging.error(f"Error consultando Notion: {e}")
            raise e

    def _parse_page(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convierte una página cruda de Notion a nuestro formato simplificado."""
        properties = page.get("properties", {})
        
        # Extraer Fecha
        date_prop = properties.get(self.prop_date, {})
        date_val = None
        if date_prop.get("type") == "date" and date_prop.get("date"):
            date_val = date_prop["date"]["start"]
        
        if not date_val:
            return None # Ignorar si no tiene fecha

        # Extraer Título
        title_prop = properties.get(self.prop_title, {})
        title_val = "Sin Título"
        if title_prop.get("type") == "title" and title_prop.get("title"):
             # Unir fragmentos de texto
            title_text = [t.get("plain_text", "") for t in title_prop.get("title", [])]
            title_val = "".join(title_text)
        elif title_prop.get("type") == "rich_text" and title_prop.get("rich_text"):
             # Fallback if title is actually a rich_text field
            title_text = [t.get("plain_text", "") for t in title_prop.get("rich_text", [])]
            title_val = "".join(title_text)

        # Extraer Materia (Select/Multi-select/Title)
        subject_prop = properties.get(self.prop_subject, {})
        subject_val = "Sin Materia"
        if subject_prop.get("type") == "select" and subject_prop.get("select"):
             subject_val = subject_prop["select"]["name"]
        elif subject_prop.get("type") == "multi_select" and subject_prop.get("multi_select"):
             subject_val = ", ".join([s["name"] for s in subject_prop["multi_select"]])
        elif subject_prop.get("type") == "title" and subject_prop.get("title"):
             subject_text = [t.get("plain_text", "") for t in subject_prop.get("title", [])]
             subject_val = "".join(subject_text)

        # Extraer Contenido (Rich Text)
        content_prop = properties.get(self.prop_content, {})
        content_val = ""
        if content_prop.get("type") == "rich_text" and content_prop.get("rich_text"):
            content_text = [t.get("plain_text", "") for t in content_prop.get("rich_text", [])]
            content_val = "".join(content_text)
        
        return {
            "titulo": title_val,
            "fecha": date_val,
            "materia": subject_val,
            "contenido": content_val,
            "url": page.get("url", "")
        }
