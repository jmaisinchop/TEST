from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import (Grupos, PersonnelDepartment, GrupoHorariosEspeciales,
                        DepartmentHorariosEspeciales)
from datetime import datetime
from sqlalchemy.orm import joinedload

horarios_bp = Blueprint('horarios', __name__, url_prefix='/horarios')


@horarios_bp.route('/')
def index():
    """Muestra la lista paginada de horarios especiales y los formularios."""
    page = request.args.get('page', 1, type=int)
    fecha_desde_str = request.args.get('desde', '', type=str)
    fecha_hasta_str = request.args.get('hasta', '', type=str)

    # Consulta mejorada para cargar los datos del grupo de forma eficiente
    query_grupos = GrupoHorariosEspeciales.query.options(
        joinedload(GrupoHorariosEspeciales.grupo)
    ).order_by(GrupoHorariosEspeciales.fecha.desc())

    query_deptos = DepartmentHorariosEspeciales.query.order_by(DepartmentHorariosEspeciales.fecha.desc())

    # Aplicamos filtros de fecha si existen
    if fecha_desde_str:
        query_grupos = query_grupos.filter(GrupoHorariosEspeciales.fecha >= fecha_desde_str)
        query_deptos = query_deptos.filter(DepartmentHorariosEspeciales.fecha >= fecha_desde_str)
    if fecha_hasta_str:
        query_grupos = query_grupos.filter(GrupoHorariosEspeciales.fecha <= fecha_hasta_str)
        query_deptos = query_deptos.filter(DepartmentHorariosEspeciales.fecha <= fecha_hasta_str)

    # Aplicamos paginación
    per_page = 10  # Registros por página
    horarios_grupos_paginados = query_grupos.paginate(page=page, per_page=per_page, error_out=False)
    horarios_deptos_paginados = query_deptos.paginate(page=page, per_page=per_page, error_out=False)

    # Datos para los formularios
    grupos = Grupos.query.order_by(Grupos.name).all()
    departamentos = PersonnelDepartment.query.filter(
        PersonnelDepartment.dept_name.in_(['Callcenter', 'Guayaquil', 'Administracion'])).order_by(
        PersonnelDepartment.dept_name).all()

    return render_template(
        'horarios/index.html',
        grupos=grupos,
        departamentos=departamentos,
        horarios_grupos=horarios_grupos_paginados,
        horarios_departamentos=horarios_deptos_paginados,
        desde=fecha_desde_str,
        hasta=fecha_hasta_str
    )


def procesar_horario(form_data, updates):
    """Función auxiliar mejorada para procesar los formularios de horarios."""
    tipo = form_data.get('tipo')
    fecha_str = form_data.get('fecha')
    objeto_id = form_data.get('objeto_id')

    if not all([tipo, fecha_str, objeto_id]):
        flash('Faltan datos (tipo, fecha u objeto).', 'danger')
        return redirect(url_for('horarios.index'))

    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de fecha inválido.', 'danger')
        return redirect(url_for('horarios.index'))

    registro = None
    if tipo == 'grupo':
        registro = GrupoHorariosEspeciales.query.filter_by(grupo_id=objeto_id, fecha=fecha_obj).first()
        if not registro:
            registro = GrupoHorariosEspeciales(grupo_id=objeto_id, fecha=fecha_obj)
            db.session.add(registro)
    elif tipo == 'departamento':
        depto = db.session.get(PersonnelDepartment, objeto_id)
        if not depto:
            flash('Departamento no encontrado.', 'danger')
            return redirect(url_for('horarios.index'))
        registro = DepartmentHorariosEspeciales.query.filter_by(dept_name=depto.dept_name, fecha=fecha_obj).first()
        if not registro:
            registro = DepartmentHorariosEspeciales(dept_name=depto.dept_name, fecha=fecha_obj)
            db.session.add(registro)
    else:
        flash('Tipo de asignación desconocido.', 'danger')
        return redirect(url_for('horarios.index'))

    for key, value in updates.items():
        setattr(registro, key, value)

    db.session.commit()
    flash('Horario especial guardado correctamente.', 'success')
    return redirect(url_for('horarios.index'))


@horarios_bp.route('/asignar', methods=['POST'])
def asignar():
    """Ruta unificada para manejar todas las asignaciones."""
    action = request.form.get('action')
    updates = {}

    if action == 'asignar_entrada':
        updates = {'hora_entrada_especial': request.form.get('hora_entrada') or None}
    elif action == 'asignar_salida':
        updates = {'hora_salida_especial': request.form.get('hora_salida') or None}
    elif action == 'asignar_extras':
        updates = {'horas_extras': int(request.form.get('horas_extras', 0))}
    elif action == 'marcar_feriado':
        updates = {'feriado': True}
    else:
        flash('Acción desconocida.', 'danger')
        return redirect(url_for('horarios.index'))

    return procesar_horario(request.form, updates)


@horarios_bp.route('/eliminar/<string:tipo>/<int:registro_id>', methods=['POST'])
def eliminar(tipo, registro_id):
    """Elimina un registro de horario especial."""
    if tipo == 'grupo':
        registro = db.get_or_404(GrupoHorariosEspeciales, registro_id)
    elif tipo == 'departamento':
        registro = db.get_or_404(DepartmentHorariosEspeciales, registro_id)
    else:
        flash('Tipo de registro no válido.', 'danger')
        return redirect(url_for('horarios.index'))

    db.session.delete(registro)
    db.session.commit()
    flash('Registro de horario especial eliminado correctamente.', 'success')
    return redirect(url_for('horarios.index'))
