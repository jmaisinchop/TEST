from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app import db
from app.models import Grupos, Carteras, GrupoEmpleados, PersonnelEmployee, PersonnelDepartment

# El url_prefix es clave para que las URLs funcionen
grupos_bp = Blueprint('grupos', __name__, url_prefix='/grupos')


@grupos_bp.route('/')
def index():
    """Muestra una lista de grupos con el conteo de empleados en cada uno."""
    employee_count_subquery = db.session.query(
        GrupoEmpleados.grupo_id,
        func.count(GrupoEmpleados.id).label('employee_count')
    ).group_by(GrupoEmpleados.grupo_id).subquery()

    lista_grupos_query = db.session.query(
        Grupos,
        employee_count_subquery.c.employee_count
    ).outerjoin(employee_count_subquery, Grupos.id == employee_count_subquery.c.grupo_id) \
        .options(joinedload(Grupos.cartera)) \
        .order_by(Grupos.name)

    lista_grupos = lista_grupos_query.all()
    lista_carteras = Carteras.query.filter_by(anulada=False).order_by(Carteras.name).all()

    return render_template(
        'grupos/index.html',
        grupos_data=lista_grupos,
        carteras=lista_carteras
    )


@grupos_bp.route('/crear', methods=['POST'])
def crear():
    """Crea un nuevo grupo con un código autogenerado."""
    name = request.form['name']
    hora_entrada = request.form['hora_entrada']
    hora_salida = request.form['hora_salida']
    cartera_id = request.form['cartera_id']

    last_grupo = Grupos.query.order_by(Grupos.id.desc()).first()
    new_id = (last_grupo.id + 1) if last_grupo else 1
    code = f"GRP-{new_id:04d}"

    nuevo_grupo = Grupos(
        code=code, name=name, hora_entrada=hora_entrada,
        hora_salida=hora_salida, cartera_id=cartera_id
    )
    db.session.add(nuevo_grupo)
    db.session.commit()
    flash('¡Grupo creado exitosamente!', 'success')
    return redirect(url_for('grupos.index'))


@grupos_bp.route('/editar/<int:grupo_id>', methods=['POST'])
def editar(grupo_id):
    """Actualiza la información de un grupo existente."""
    grupo_a_editar = db.get_or_404(Grupos, grupo_id)

    grupo_a_editar.name = request.form['name']
    grupo_a_editar.hora_entrada = request.form['hora_entrada']
    grupo_a_editar.hora_salida = request.form['hora_salida']
    grupo_a_editar.cartera_id = request.form['cartera_id']

    db.session.commit()
    flash('¡Grupo actualizado correctamente!', 'success')
    return redirect(url_for('grupos.index'))


@grupos_bp.route('/eliminar/<int:grupo_id>', methods=['POST'])
def eliminar(grupo_id):
    """Elimina un grupo y todas sus dependencias."""
    from app.models import GrupoHorariosEspeciales
    grupo_a_eliminar = db.get_or_404(Grupos, grupo_id)

    GrupoEmpleados.query.filter_by(grupo_id=grupo_id).delete()
    GrupoHorariosEspeciales.query.filter_by(grupo_id=grupo_id).delete()

    db.session.delete(grupo_a_eliminar)
    db.session.commit()
    flash('Grupo y todas sus asignaciones han sido eliminados correctamente.', 'success')
    return redirect(url_for('grupos.index'))


@grupos_bp.route('/<int:grupo_id>/detalle')
def detalle(grupo_id):
    grupo = db.get_or_404(Grupos, grupo_id)
    pasaportes_en_grupo = db.session.query(GrupoEmpleados.employee_passport) \
        .filter_by(grupo_id=grupo_id).scalar_subquery()
    empleados_en_grupo = PersonnelEmployee.query \
        .join(PersonnelDepartment) \
        .filter(PersonnelEmployee.passport.in_(pasaportes_en_grupo)).all()
    todos_los_pasaportes_asignados = db.session.query(GrupoEmpleados.employee_passport).distinct()
    departamentos_permitidos = ['Callcenter', 'Administracion', 'Guayaquil']
    empleados_disponibles = PersonnelEmployee.query \
        .join(PersonnelDepartment) \
        .filter(
        PersonnelDepartment.dept_name.in_(departamentos_permitidos),
        PersonnelEmployee.passport.notin_(todos_los_pasaportes_asignados)
    ).all()
    return render_template(
        'grupos/detalle.html',
        grupo=grupo,
        empleados_en_grupo=empleados_en_grupo,
        empleados_disponibles=empleados_disponibles
    )


# --- Rutas para acciones de un solo empleado (usadas por Drag and Drop) ---
@grupos_bp.route('/<int:grupo_id>/agregar_empleado', methods=['POST'])
def agregar_empleado(grupo_id):
    passport = request.form.get('employee_passport')
    if not passport:
        return jsonify({'success': False, 'error': 'No se recibió el pasaporte.'}), 400
    existe = GrupoEmpleados.query.filter_by(grupo_id=grupo_id, employee_passport=passport).first()
    if not existe:
        nueva_asignacion = GrupoEmpleados(grupo_id=grupo_id, employee_passport=passport)
        db.session.add(nueva_asignacion)
        db.session.commit()
    return jsonify({'success': True})


@grupos_bp.route('/<int:grupo_id>/quitar_empleado', methods=['POST'])
def quitar_empleado(grupo_id):
    passport = request.form.get('employee_passport')
    if not passport:
        return jsonify({'success': False, 'error': 'No se recibió el pasaporte.'}), 400
    asignacion = GrupoEmpleados.query.filter_by(grupo_id=grupo_id, employee_passport=passport).first()
    if asignacion:
        db.session.delete(asignacion)
        db.session.commit()
    return jsonify({'success': True})


# --- ✨ RUTAS PARA ACCIONES EN LOTE (USADAS POR LOS BOTONES) ✨ ---
# Estas son las rutas que faltaban en tu aplicación en ejecución.

@grupos_bp.route('/<int:grupo_id>/agregar_empleados_bulk', methods=['POST'])
def agregar_empleados_bulk(grupo_id):
    """Agrega una lista de empleados al grupo."""
    passports = request.json.get('passports', [])
    if not passports:
        return jsonify({'success': False, 'error': 'No se recibieron pasaportes.'}), 400

    for passport in passports:
        existe = GrupoEmpleados.query.filter_by(grupo_id=grupo_id, employee_passport=passport).first()
        if not existe:
            nueva_asignacion = GrupoEmpleados(grupo_id=grupo_id, employee_passport=passport)
            db.session.add(nueva_asignacion)

    db.session.commit()
    return jsonify({'success': True})


@grupos_bp.route('/<int:grupo_id>/quitar_empleados_bulk', methods=['POST'])
def quitar_empleados_bulk(grupo_id):
    """Quita una lista de empleados del grupo."""
    passports = request.json.get('passports', [])
    if not passports:
        return jsonify({'success': False, 'error': 'No se recibieron pasaportes.'}), 400

    # Usamos .in_() para una consulta de borrado en lote más eficiente
    GrupoEmpleados.query.filter(
        GrupoEmpleados.grupo_id == grupo_id,
        GrupoEmpleados.employee_passport.in_(passports)
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({'success': True})
