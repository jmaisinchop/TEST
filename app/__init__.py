# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# Inicializar extensiones globalmente
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """Fábrica de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)

    # Importar y registrar Blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.departamentos import departamentos_bp
    # Le decimos a la app que todas las rutas de este blueprint
    # empezarán con / (en este caso, /departamentos)
    app.register_blueprint(departamentos_bp)

    from app.routes.carteras import carteras_bp
    app.register_blueprint(carteras_bp)
    from app.routes.grupos import grupos_bp
    app.register_blueprint(grupos_bp)
    from app.routes.justificaciones import justificaciones_bp
    app.register_blueprint(justificaciones_bp)
    from app.routes.horarios import horarios_bp
    app.register_blueprint(horarios_bp)
    from app.routes.reportes import reportes_bp
    app.register_blueprint(reportes_bp)
    from app.routes.permisos import permisos_bp
    app.register_blueprint(permisos_bp)
    from app.routes.asignacion_masiva import asignacion_masiva_bp
    app.register_blueprint(asignacion_masiva_bp)


    return app