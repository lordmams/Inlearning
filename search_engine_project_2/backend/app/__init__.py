from flask import Flask
from .routes import main_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(main_bp)
    return app

if __name__ == '__main__':
    # Lancer l'application sur toutes les interfaces réseau (0.0.0.0) pour que Docker l'accepte
    app.run(debug=True, host="0.0.0.0", port=5000)