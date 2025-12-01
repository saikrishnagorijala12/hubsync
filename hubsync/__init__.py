import os
from flask import Flask
from dotenv import load_dotenv
from .config.config import Config

from .blueprints import register_routes


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)
    register_routes(app)
    return app


