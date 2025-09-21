from flask import Blueprint, render_template
from app.models import PersonnelDepartment, PersonnelEmployee
from app import db
from sqlalchemy import func

# Creamos el Blueprint para el módulo de departamentos
departamentos_bp = Blueprint('departamentos', __name__)


@departamentos_bp.route('/departamentos')
def listar_departamentos():
    """
    Esta ruta consulta los departamentos permitidos y cuenta
    el número de empleados en cada uno para mostrarlos en la vista.
    """
    # Definimos los únicos departamentos que queremos mostrar
    departamentos_permitidos = ['Callcenter', 'Guayaquil', 'Administracion']

    # Creamos una consulta a la base de datos para obtener los departamentos
    # y, al mismo tiempo, contar los empleados de cada uno.
    # Usamos un "left join" para asegurarnos de que se muestren los departamentos
    # incluso si tienen cero empleados.
    query = db.session.query(
        PersonnelDepartment,
        func.count(PersonnelEmployee.id).label('employee_count')
    ).outerjoin(PersonnelEmployee, PersonnelDepartment.id == PersonnelEmployee.department_id)\
    .filter(PersonnelDepartment.dept_name.in_(departamentos_permitidos))\
    .group_by(PersonnelDepartment.id)\
    .order_by(PersonnelDepartment.dept_name)

    # El resultado es una lista de tuplas, donde cada tupla contiene:
    # (objeto_departamento, conteo_de_empleados)
    departamentos_con_conteo = query.all()

    # Renderizamos la nueva plantilla, pasando la lista con los datos
    return render_template(
        'departamentos/lista.html',
        departamentos=departamentos_con_conteo
    )
