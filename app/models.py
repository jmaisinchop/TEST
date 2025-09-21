from datetime import datetime
from app import db


# -----------------------------------------------------------------------------------
# Modelos de Tablas Externas (Solo Lectura)
# -----------------------------------------------------------------------------------

class PersonnelEmployee(db.Model):
    __tablename__ = 'personnel_employee'
    id = db.Column(db.Integer, primary_key=True)
    passport = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    department_id = db.Column(db.Integer, db.ForeignKey('personnel_department.id'))

    def __repr__(self):
        return f'<Employee {self.first_name} {self.last_name}>'


class PersonnelDepartment(db.Model):
    __tablename__ = 'personnel_department'
    id = db.Column(db.Integer, primary_key=True)
    dept_code = db.Column(db.String(20), unique=True)
    dept_name = db.Column(db.String(100), nullable=False)
    employees = db.relationship('PersonnelEmployee', backref='department', lazy=True)

    def __repr__(self):
        return f'<Department {self.dept_name}>'


class IClockTransaction(db.Model):
    __tablename__ = 'iclock_transaction'
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.Integer, db.ForeignKey('personnel_employee.id'), index=True)
    punch_time = db.Column(db.DateTime, nullable=False, index=True)
    empleado = db.relationship('PersonnelEmployee')


# -----------------------------------------------------------------------------------
# Modelos de Tablas de la Aplicación
# -----------------------------------------------------------------------------------

class Carteras(db.Model):
    __tablename__ = 'carteras'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    anulada = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Grupos(db.Model):
    __tablename__ = 'grupos'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    hora_entrada = db.Column(db.Time, nullable=False)
    hora_salida = db.Column(db.Time, nullable=False)
    cartera_id = db.Column(db.Integer, db.ForeignKey('carteras.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cartera = db.relationship('Carteras', backref='grupos', lazy=True)


class GrupoEmpleados(db.Model):
    __tablename__ = 'grupo_empleados'
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=False, index=True)
    employee_passport = db.Column(db.String(50), nullable=False, index=True)


class Justificaciones(db.Model):
    __tablename__ = 'justificaciones'
    id = db.Column(db.Integer, primary_key=True)
    employee_passport = db.Column(db.String(50), nullable=False, index=True)
    justification_type = db.Column(db.String(50), nullable=False)
    date_start = db.Column(db.Date, nullable=False)
    date_end = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    anulada = db.Column(db.Boolean, default=False, nullable=False)
    empleado = db.relationship(
        'PersonnelEmployee',
        foreign_keys=[employee_passport],
        primaryjoin="Justificaciones.employee_passport == PersonnelEmployee.passport"
    )


class Permisos(db.Model):
    __tablename__ = 'permisos'
    id = db.Column(db.Integer, primary_key=True)
    employee_passport = db.Column(db.String(50), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False)
    hora_desde = db.Column(db.Time, nullable=False)
    hora_hasta = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    observacion = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    empleado = db.relationship(
        'PersonnelEmployee',
        foreign_keys=[employee_passport],
        primaryjoin="Permisos.employee_passport == PersonnelEmployee.passport",
        lazy='joined'
    )


class GrupoHorariosEspeciales(db.Model):
    __tablename__ = 'grupo_horarios_especiales'
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_entrada_especial = db.Column(db.Time)
    hora_salida_especial = db.Column(db.Time)
    horas_extras = db.Column(db.Integer, default=0)
    feriado = db.Column(db.Boolean, default=False)

    # ✨ LÍNEA AÑADIDA: Define la relación para poder acceder a los datos del grupo.
    grupo = db.relationship('Grupos', backref='horarios_especiales')


class DepartmentHorariosEspeciales(db.Model):
    __tablename__ = 'department_horarios_especiales'
    id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_entrada_especial = db.Column(db.Time)
    hora_salida_especial = db.Column(db.Time)
    horas_extras = db.Column(db.Integer, default=0)
    feriado = db.Column(db.Boolean, default=False)


class AllowedIP(db.Model):
    __tablename__ = 'allowed_ips'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
