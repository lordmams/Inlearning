#!/usr/bin/env python3
"""
Serveur HTTP simple pour les vérifications de santé de l'orchestrateur
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
from datetime import datetime


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            response = {
                "status": "healthy",
                "service": "Python Orchestrator",
                "timestamp": datetime.now().isoformat(),
                "uptime": "running",
                "tasks_registered": 4,
            }

            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def start_health_server():
    """Démarre le serveur de santé sur le port 8000"""
    server = HTTPServer(("0.0.0.0", 8000), HealthHandler)
    print("Health server started on port 8000")
    server.serve_forever()


if __name__ == "__main__":
    start_health_server()
