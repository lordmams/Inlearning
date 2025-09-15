from app.routes import routes
from flask import Flask


def create_app():
    app = Flask(__name__)

    # Enregistrement des routes
    app.register_blueprint(routes)

    return app
