from flask import Blueprint, render_template, request, send_file, flash, url_for
from app.models import PersonnelDepartment
from app.services.report_builder import build_report
from app.services.excel_builder import crear_excel_reporte
from datetime import datetime

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')


@reportes_bp.route('/')
def index():
    departamentos_permitidos = ['Callcenter', 'Guayaquil', 'Administracion']
    departamentos = PersonnelDepartment.query.filter(
        PersonnelDepartment.dept_name.in_(departamentos_permitidos)
    ).order_by(PersonnelDepartment.dept_name).all()

    fecha_desde_str = request.args.get('fecha_desde')
    fecha_hasta_str = request.args.get('fecha_hasta')
    departamento_id = request.args.get('departamento_id')

    resultados_reporte = None
    if fecha_desde_str and fecha_hasta_str:
        fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
        fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
        resultados_reporte = build_report(fecha_desde, fecha_hasta, departamento_id)

    return render_template(
        'reportes/index.html',
        departamentos=departamentos,
        departamento_seleccionado=departamento_id,
        resultados=resultados_reporte
    )


@reportes_bp.route('/descargar-excel')
def descargar_excel():
    fecha_desde_str = request.args.get('fecha_desde')
    fecha_hasta_str = request.args.get('fecha_hasta')

    if not fecha_desde_str or not fecha_hasta_str:
        flash('El rango de fechas es obligatorio para descargar el reporte.', 'danger')
        return redirect(url_for('reportes.index'))

    # Recoger todos los parámetros del formulario, convirtiéndolos a float
    params = {
        'fecha_desde': datetime.strptime(fecha_desde_str, '%Y-%m-%d').date(),
        'fecha_hasta': datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date(),
        'departamento_id': request.args.get('departamento_id'),
        'costo_hora_normal': float(request.args.get('costo_hora_normal', 0)),
        'costo_hora_sabfer': float(request.args.get('costo_hora_sabfer', 0)),
        'multa_atraso_normal': float(request.args.get('multa_atraso_normal', 0)),
        'multa_atraso_sabfer': float(request.args.get('multa_atraso_sabfer', 0)),
        'multa_falta_normal': float(request.args.get('multa_falta_normal', 0)),
        'multa_falta_sabfer': float(request.args.get('multa_falta_sabfer', 0))
    }

    # Generar los datos del reporte
    resultados_reporte = build_report(params['fecha_desde'], params['fecha_hasta'], params['departamento_id'])

    # Crear el archivo Excel, pasando tanto los datos como los parámetros de costos/multas
    archivo_excel_en_memoria = crear_excel_reporte(resultados_reporte, params)

    nombre_archivo = f"Reporte_Financiero_{fecha_desde_str}_a_{fecha_hasta_str}.xlsx"
    return send_file(
        archivo_excel_en_memoria,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )