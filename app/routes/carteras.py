from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Carteras
from app import db

# El url_prefix='/carteras' hace que todas las rutas aquí empiecen con /carteras
carteras_bp = Blueprint('carteras', __name__, url_prefix='/carteras')


@carteras_bp.route('/')
def index():
    """Muestra una lista de todas las carteras activas."""
    # Filtramos para mostrar solo las carteras que no están anuladas
    lista_carteras = Carteras.query.filter_by(anulada=False).order_by(Carteras.name).all()
    return render_template('carteras/index.html', carteras=lista_carteras)


@carteras_bp.route('/crear', methods=['POST'])
def crear():
    """Recibe los datos de un formulario y crea una nueva cartera con un código autogenerado."""
    # El código ya no se recibe del formulario.
    name = request.form['name']
    description = request.form.get('description', '')

    # --- Lógica de autogeneración de código ---
    # Buscamos la última cartera por ID para generar el siguiente número.
    last_cartera = Carteras.query.order_by(Carteras.id.desc()).first()
    new_id = (last_cartera.id + 1) if last_cartera else 1

    # Creamos un código con formato (ej. CAR-0001, CAR-0002, etc.)
    code = f"CAR-{new_id:04d}"

    # Verificación de unicidad (aunque es poco probable que falle, es una buena práctica)
    if Carteras.query.filter_by(code=code).first():
        flash(f'Error al generar un código único. Inténtelo de nuevo.', 'danger')
        return redirect(url_for('carteras.index'))

    nueva_cartera = Carteras(code=code, name=name, description=description)
    db.session.add(nueva_cartera)
    db.session.commit()

    flash('¡Cartera creada exitosamente!', 'success')
    return redirect(url_for('carteras.index'))


@carteras_bp.route('/editar/<int:cartera_id>', methods=['POST'])
def editar(cartera_id):
    """Actualiza la información de una cartera existente."""
    cartera_a_editar = db.session.get(Carteras, cartera_id)
    if not cartera_a_editar:
        flash('Cartera no encontrada.', 'danger')
        return redirect(url_for('carteras.index'))

    # El código no se puede editar. Solo el nombre y la descripción.
    cartera_a_editar.name = request.form['name']
    cartera_a_editar.description = request.form.get('description', '')

    db.session.commit()
    flash('¡Cartera actualizada correctamente!', 'success')
    return redirect(url_for('carteras.index'))


@carteras_bp.route('/anular/<int:cartera_id>', methods=['POST'])
def anular(cartera_id):
    """Marca una cartera como anulada (borrado suave)."""
    cartera_a_anular = db.session.get(Carteras, cartera_id)
    if not cartera_a_anular:
        flash('Cartera no encontrada.', 'danger')
        return redirect(url_for('carteras.index'))

    cartera_a_anular.anulada = True
    db.session.commit()
    flash('Cartera anulada correctamente.', 'success')
    return redirect(url_for('carteras.index'))
