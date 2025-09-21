from collections import defaultdict
from datetime import timedelta, datetime, time
from sqlalchemy import text
from app import db
from app.models import (PersonnelEmployee, PersonnelDepartment, Justificaciones,
                        IClockTransaction, Permisos, GrupoHorariosEspeciales, DepartmentHorariosEspeciales,
                        Grupos, GrupoEmpleados)


def build_report(start_date, end_date, department_id=None):
    """
    Construye el reporte de asistencia con todos los cálculos detallados,
    incluyendo la identificación de marcaciones de almuerzo.
    """
    # --- Consultas a la base de datos (sin cambios) ---
    departamentos_permitidos = ['Callcenter', 'Guayaquil', 'Administracion']
    query_empleados = PersonnelEmployee.query.join(PersonnelDepartment).filter(
        PersonnelDepartment.dept_name.in_(departamentos_permitidos)
    )
    if department_id and department_id.isdigit():
        query_empleados = query_empleados.filter(PersonnelDepartment.id == int(department_id))
    empleados_a_reportar = query_empleados.order_by(PersonnelEmployee.last_name).all()
    if not empleados_a_reportar: return []

    pasaportes = [e.passport for e in empleados_a_reportar]
    ids_empleados = [e.id for e in empleados_a_reportar]

    sql = text("""
        SELECT p.passport, (t.punch_time AT TIME ZONE 'America/Guayaquil')::date AS fecha_local,
               (t.punch_time AT TIME ZONE 'America/Guayaquil')::time AS hora_local
        FROM iclock_transaction t JOIN personnel_employee p ON t.emp_id = p.id
        WHERE t.emp_id = ANY(:ids_empleados) AND t.punch_time >= :start_date AND t.punch_time < :end_date_plus_one
    """)
    marcaciones_q = db.session.execute(sql, {"ids_empleados": ids_empleados, "start_date": start_date,
                                             "end_date_plus_one": end_date + timedelta(days=1)}).fetchall()

    # Resto de consultas y mapeos...
    justificaciones_q = Justificaciones.query.filter(Justificaciones.employee_passport.in_(pasaportes),
                                                     Justificaciones.anulada == False,
                                                     Justificaciones.date_start <= end_date,
                                                     Justificaciones.date_end >= start_date).all()
    permisos_q = Permisos.query.filter(Permisos.employee_passport.in_(pasaportes),
                                       Permisos.fecha.between(start_date, end_date)).all()
    grupo_horarios_q = GrupoHorariosEspeciales.query.filter(
        GrupoHorariosEspeciales.fecha.between(start_date, end_date)).all()
    depto_horarios_q = DepartmentHorariosEspeciales.query.filter(
        DepartmentHorariosEspeciales.fecha.between(start_date, end_date)).all()

    empleado_grupo_map = {ge.employee_passport: ge.grupo_id for ge, g in
                          db.session.query(GrupoEmpleados, Grupos).join(Grupos).all()}
    marcaciones_map = defaultdict(lambda: defaultdict(list))
    for m in marcaciones_q: marcaciones_map[m.passport][m.fecha_local.strftime('%Y-%m-%d')].append(m.hora_local)
    justificaciones_map = defaultdict(list)
    for j in justificaciones_q:
        d = j.date_start
        while d <= j.date_end: justificaciones_map[j.employee_passport].append(d); d += timedelta(days=1)
    permisos_map = defaultdict(dict)
    for p in permisos_q: permisos_map[p.employee_passport][p.fecha] = p

    horarios_especiales_map = defaultdict(dict)
    for dh in depto_horarios_q:
        horarios_especiales_map[('depto', dh.dept_name, dh.fecha)] = {'extras': dh.horas_extras, 'feriado': dh.feriado,
                                                                      'entrada': dh.hora_entrada_especial,
                                                                      'salida': dh.hora_salida_especial}
    for gh in grupo_horarios_q:
        horarios_especiales_map[('grupo', gh.grupo_id, gh.fecha)] = {'extras': gh.horas_extras, 'feriado': gh.feriado,
                                                                     'entrada': gh.hora_entrada_especial,
                                                                     'salida': gh.hora_salida_especial}

    reporte_final = []
    dias_del_periodo = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1) if
                        (start_date + timedelta(days=i)).weekday() != 6]

    for empleado in empleados_a_reportar:
        # ✨ DICCIONARIO DE RESUMEN CORREGIDO Y COMPLETO
        resumen = {
            'total_asistencias': 0,
            'total_atrasos_normal': 0, 'total_atrasos_sabfer': 0,
            'total_minutos_atraso_normal': 0, 'total_minutos_atraso_sabfer': 0,
            'total_faltas_normal': 0, 'total_faltas_sabfer': 0,
            'total_faltas_injustificadas_normal': 0, 'total_faltas_injustificadas_sabfer': 0,
            'total_faltas_justificadas': 0,
            'total_horas_extras_normal': timedelta(), 'total_horas_extras_sabfer': timedelta()
        }

        registros_diarios_emp = []
        for dia in dias_del_periodo:
            lunch_duration = timedelta(hours=1 if empleado.department.dept_name != 'Administracion' else 2)
            grupo_id = empleado_grupo_map.get(empleado.passport)

            regla_depto = horarios_especiales_map.get(('depto', empleado.department.dept_name, dia), {})
            regla_grupo = horarios_especiales_map.get(('grupo', grupo_id, dia), {})

            horas_extras_aprobadas_int = max(regla_depto.get('extras', 0), regla_grupo.get('extras', 0))
            es_feriado = regla_depto.get('feriado', False) or regla_grupo.get('feriado', False)
            horario_entrada_prog = regla_grupo.get('entrada') or regla_depto.get('entrada') or time(8, 0, 0)
            horario_salida_prog = regla_grupo.get('salida') or regla_depto.get('salida') or time(18, 0, 0)

            permiso_del_dia = permisos_map[empleado.passport].get(dia)
            if permiso_del_dia:
                if permiso_del_dia.hora_desde <= horario_entrada_prog: horario_entrada_prog = permiso_del_dia.hora_hasta
                if permiso_del_dia.hora_hasta >= horario_salida_prog: horario_salida_prog = permiso_del_dia.hora_desde

            hora_limite_entrada = (datetime.combine(dia, horario_entrada_prog) + timedelta(minutes=5)).time()

            es_sabado = dia.weekday() == 5
            es_feriado_laborable = es_feriado and horas_extras_aprobadas_int > 0

            tipo_dia_laborable = 'Normal'
            if es_sabado or es_feriado_laborable:
                tipo_dia_laborable = 'Sabado/Feriado'

            registro = {
                'fecha': dia, 'estado': '-',
                'horario_prog': f"{horario_entrada_prog.strftime('%H:%M')} - {horario_salida_prog.strftime('%H:%M')}",
                'marcaciones': '-', 'minutos_atraso': 0, 'tiempo_trabajado': '00:00',
                'horas_extras_trabajadas': '00:00', 'es_falta': 0, 'es_atraso': 0,
                'tipo_dia_laborable': tipo_dia_laborable, 'es_feriado_laborable': es_feriado_laborable,
                'hora_ingreso': None, 'hora_salida_almuerzo': None,
                'hora_regreso_almuerzo': None, 'hora_salida_final': None,
                'tiempo_almuerzo': '00:00'
            }

            if es_feriado and not es_feriado_laborable:
                registro['estado'] = 'Feriado'
            elif dia in justificaciones_map[empleado.passport]:
                registro['estado'] = 'Justificado'
                resumen['total_faltas_justificadas'] += 1
            elif sorted(marcaciones_map[empleado.passport][dia.strftime('%Y-%m-%d')]):
                resumen['total_asistencias'] += 1
                marcaciones_dia = sorted(marcaciones_map[empleado.passport][dia.strftime('%Y-%m-%d')])

                if len(marcaciones_dia) >= 1: registro['hora_ingreso'] = marcaciones_dia[0]
                if len(marcaciones_dia) >= 2: registro['hora_salida_final'] = marcaciones_dia[-1]
                if len(marcaciones_dia) == 4:
                    registro['hora_salida_almuerzo'] = marcaciones_dia[1]
                    registro['hora_regreso_almuerzo'] = marcaciones_dia[2]
                    almuerzo_delta = datetime.combine(dia, marcaciones_dia[2]) - datetime.combine(dia,
                                                                                                  marcaciones_dia[1])
                    h_a, rem_a = divmod(int(almuerzo_delta.total_seconds()), 3600)
                    m_a, _ = divmod(rem_a, 60)
                    registro['tiempo_almuerzo'] = f'{h_a:02d}:{m_a:02d}'

                entrada_real = registro['hora_ingreso']
                salida_real = registro['hora_salida_final']

                if entrada_real:
                    registro['marcaciones'] = entrada_real.strftime("%H:%M")
                    if salida_real and salida_real != entrada_real:
                        registro['marcaciones'] += f' - {salida_real.strftime("%H:%M")}'

                if entrada_real > hora_limite_entrada:
                    atraso_delta = datetime.combine(dia, entrada_real) - datetime.combine(dia, hora_limite_entrada)
                    registro['minutos_atraso'] = int(atraso_delta.total_seconds() // 60)
                    registro['estado'] = 'Atraso';
                    registro['es_atraso'] = 1
                    if tipo_dia_laborable == 'Normal':
                        resumen['total_atrasos_normal'] += 1
                        resumen['total_minutos_atraso_normal'] += registro['minutos_atraso']
                    else:
                        resumen['total_atrasos_sabfer'] += 1
                        resumen['total_minutos_atraso_sabfer'] += registro['minutos_atraso']
                else:
                    registro['estado'] = 'Presente'

                if permiso_del_dia and registro['estado'] != 'Atraso': registro['estado'] = 'Permiso'

                if len(marcaciones_dia) >= 2:
                    lunch_duration = timedelta()
                    if registro['hora_salida_almuerzo'] and registro['hora_regreso_almuerzo']:
                        lunch_duration = datetime.combine(dia, registro['hora_regreso_almuerzo']) - datetime.combine(
                            dia, registro['hora_salida_almuerzo'])

                    duracion_neta = (datetime.combine(dia, salida_real) - datetime.combine(dia,
                                                                                           entrada_real)) - lunch_duration
                    if duracion_neta.total_seconds() < 0: duracion_neta = timedelta(seconds=0)

                    es_dia_laboral_especial = es_sabado or es_feriado_laborable
                    extras_reales_delta = timedelta()
                    if es_dia_laboral_especial:
                        extras_reales_delta = duracion_neta
                    elif salida_real > horario_salida_prog:
                        extras_reales_delta = datetime.combine(dia, salida_real) - datetime.combine(dia,
                                                                                                    horario_salida_prog)

                    extras_a_reportar_delta = min(extras_reales_delta, timedelta(hours=horas_extras_aprobadas_int))
                    if extras_a_reportar_delta.total_seconds() > 0:
                        h_e, rem_e = divmod(int(extras_a_reportar_delta.total_seconds()), 3600)
                        m_e, _ = divmod(rem_e, 60)
                        registro['horas_extras_trabajadas'] = f'{h_e:02d}:{m_e:02d}'
                        if tipo_dia_laborable == 'Normal':
                            resumen['total_horas_extras_normal'] += extras_a_reportar_delta
                        else:
                            resumen['total_horas_extras_sabfer'] += extras_a_reportar_delta

                    h, rem = divmod(int(duracion_neta.total_seconds()), 3600)
                    m, _ = divmod(rem, 60)
                    registro['tiempo_trabajado'] = f'{h:02d}:{m:02d}'
            else:
                es_laborable = (dia.weekday() < 5 and not es_feriado) or dia.weekday() == 5 or es_feriado_laborable
                if es_laborable:
                    registro['estado'] = 'Falta';
                    registro['es_falta'] = 1
                    if tipo_dia_laborable == 'Normal':
                        resumen['total_faltas_normal'] += 1
                        resumen['total_faltas_injustificadas_normal'] += 1
                    else:
                        resumen['total_faltas_sabfer'] += 1
                        resumen['total_faltas_injustificadas_sabfer'] += 1
                else:
                    registro['estado'] = 'Fin de Semana'

            registros_diarios_emp.append(registro)

        reporte_final.append({'empleado': empleado, 'registros': registros_diarios_emp, 'resumen': resumen})

    return reporte_final
