import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON\'T CHANGE THIS !!!

from flask import Flask, render_template, send_from_directory, url_for, redirect
import logging
import os
from flask_cors import CORS

from src.extensions import db

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas as rotas

# Configurar banco de dados SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///led_inspection.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "led_inspection_secret_key"

# Inicializar SQLAlchemy
db.init_app(app)

# Importar modelos após inicializar db
with app.app_context():
    from src.models.product import Product, ReferenceImage, Inspection
    db.create_all()
    logger.info("Banco de dados inicializado")

# Importar e registrar blueprints APÓS a inicialização do DB
from src.routes.inspection import inspection_bp
from src.routes.products import products_bp
from src.routes.api import api_bp

app.register_blueprint(inspection_bp)
app.register_blueprint(products_bp)
app.register_blueprint(api_bp)

@app.route("/")
def index():
    """Redireciona para a página inicial de produtos"""
    return redirect(url_for("products.index"))

# Rota para servir arquivos estáticos diretamente
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    # Verificar e criar diretórios necessários
    os.makedirs(os.path.join(app.static_folder, "images", "products"), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, "images", "uploads"), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, "images", "results"), exist_ok=True)
    
    # Iniciar servidor de desenvolvimento
    app.run(host="0.0.0.0", port=5000, debug=True)

