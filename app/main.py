"""
Entry point para Render. Corre desde el directorio hackmty26/ (no muevas
este archivo ni los módulos que importa).
 
Localmente:
    uvicorn app.main:app --reload --port 8000
 
En Render (Start Command):
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
 
import os
import sys
 
# Asegura que hackmty26/ (el directorio padre de app/) esté en el path,
# para poder importar api.py, hackmty_common.py, routing.py, etc. sin
# moverlos ni duplicarlos.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
 
from api import app  # noqa: E402  (re-exporta la app completa de api.py)
 
__all__ = ["app"]
 