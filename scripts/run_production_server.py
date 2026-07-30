#!/usr/bin/env python3
"""
Production Server Runner.
Launches the Flask Supervisor UI & Swarm Engine using Gunicorn on macOS/Linux or Werkzeug fallback.
"""

import sys
import os
from pathlib import Path

# Ensure src/ is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supervisor_ui.app import app

def run_production():
    port = int(os.environ.get("PORT", 5001))
    print(f"🚀 Iniciando Servidor de Producción Comercial en el puerto {port}...")

    try:
        import gunicorn.app.base

        class StandaloneApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        options = {
            "bind": f"0.0.0.0:{port}",
            "workers": 4,
            "timeout": 120,
            "loglevel": "info"
        }
        StandaloneApplication(app, options).run()
    except ImportError:
        print("⚠️ Gunicorn no instalado. Ejecutando servidor Flask por defecto.")
        app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    run_production()
