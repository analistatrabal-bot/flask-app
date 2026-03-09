from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
import re
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import flash, redirect, url_for

ZONA_MX = pytz.timezone("America/Mexico_City")
# =========================
# CONFIGURACIÓN GENERAL
# =========================

app = Flask(__name__)
app.secret_key = "mi_clave_super_secreta_2026"


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

ZONA_MX = pytz.timezone("America/Mexico_City")

# =========================
# MODELOS
# =========================

class Unidad(db.Model):
    __tablename__ = "unidades"

    unidad_id = db.Column(db.String(20), primary_key=True)
    placas_unidad = db.Column(db.String(20))
    operador = db.Column(db.String(100))
    licencia = db.Column(db.String(50))
    caja1 = db.Column(db.String(50))
    placas_caja1 = db.Column(db.String(20))
    caja2 = db.Column(db.String(50))
    placas_caja2 = db.Column(db.String(20))
    dolly = db.Column(db.String(50))
    coordinador = db.Column(db.String(50))  # Agregado el campo coordinador

    viajes = db.relationship("Viaje", backref="unidad", lazy=True)

 # Modelo de la clase Viaje

class Viaje(db.Model):
    __tablename__ = "viajes"
    id = db.Column(db.Integer, primary_key=True)
    fecha_registro = db.Column(db.DateTime, nullable=False)
    unidad_id = db.Column(db.String(20), db.ForeignKey("unidades.unidad_id"))
    folio = db.Column(db.String(50))
    origen = db.Column(db.String(100))
    destino = db.Column(db.String(100))
    tipo_movimiento = db.Column(db.String(20))  # CARGA / DESCARGA / ARRIBO_DESCARGA
    cliente = db.Column(db.String(100))
    fecha_descarga = db.Column(db.DateTime, nullable=True)
    fecha_arribo_descarga = db.Column(db.DateTime, nullable=True) 
    fecha_retorno_descarga = db.Column(db.DateTime, nullable=True)# Nueva columna
    fecha_baja = db.Column(db.DateTime, nullable=True)# Nueva columna
    coordinador = db.Column(db.String(100))   # ← NUEVO CAMPO
    ultimo_editado_por = db.Column(db.String(100))
    fecha_ultima_edicion = db.Column(db.DateTime)

from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    rol = db.Column(db.String(20))  # ADMIN o COORDINADOR

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Notificacion(db.Model):
    __tablename__ = "notificaciones"

    id = db.Column(db.Integer, primary_key=True)

    mensaje = db.Column(db.String(500), nullable=False)

    leida = db.Column(db.Boolean, default=False)

    fecha = db.Column(db.DateTime, default=lambda: datetime.now(ZONA_MX))

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),  # 👈 CORREGIDO
        nullable=True
    )

    usuario = db.relationship("Usuario", backref="notificaciones")
# =========================
# RUTAS
# =========================
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("rol") != "ADMIN":
            return "⛔ No autorizado", 403
        return f(*args, **kwargs)
    return decorated_function

from flask import request

@app.before_request
def require_login():
    rutas_publicas = ["login", "static"]

    if request.endpoint not in rutas_publicas and "user_id" not in session:
        return redirect(url_for("login"))

from flask import session

@app.route("/usuarios")
@login_required
@admin_required
def usuarios():
    usuarios = Usuario.query.all()
    return render_template("usuarios.html", usuarios=usuarios)

@app.route("/crear_usuario", methods=["GET", "POST"])
@login_required
@admin_required
def crear_usuario():

    if request.method == "POST":

        username = request.form["username"]

        # Verificar que no exista
        if Usuario.query.filter_by(username=username).first():
            return render_template("crear_usuario.html", error="❌ Usuario ya existe")

        nuevo = Usuario(
            nombre=request.form["nombre"],
            username=username,
            rol=request.form["rol"]
        )

        nuevo.set_password(request.form["password"])

        db.session.add(nuevo)
        db.session.commit()

        return redirect(url_for("usuarios"))

    return render_template("crear_usuario.html")


@app.route("/editar_usuario/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_usuario(id):

    usuario = Usuario.query.get_or_404(id)

    if request.method == "POST":

        usuario.nombre = request.form["nombre"]
        usuario.username = request.form["username"]
        usuario.rol = request.form["rol"]

        # Solo cambiar contraseña si escriben algo
        if request.form["password"]:
            usuario.set_password(request.form["password"])

        db.session.commit()
        return redirect(url_for("usuarios"))

    return render_template("editar_usuario.html", usuario=usuario)

@app.route("/eliminar_usuario/<int:id>")
@login_required
@admin_required
def eliminar_usuario(id):

    usuario = Usuario.query.get_or_404(id)

    # Evitar que el admin se borre a sí mismo
    if usuario.id == session.get("user_id"):
        return "❌ No puedes eliminarte a ti mismo"

    db.session.delete(usuario)
    db.session.commit()

    return redirect(url_for("usuarios"))


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = Usuario.query.filter_by(username=username).first()

        if user and user.check_password(password):

            session["user_id"] = user.id
            session["rol"] = user.rol
            session["nombre"] = user.nombre

            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/")
def inicio():

    if "user_id" in session:
        return redirect(url_for("registrar_viaje"))
    else:
        return redirect(url_for("login"))

def convertir_fecha(valor):
    if valor and valor.strip() != "":
        return datetime.strptime(valor, "%Y-%m-%dT%H:%M")
    return None



# -------------------------
# REGISTRAR UNIDAD
# -------------------------
@app.route("/unidades", methods=["GET", "POST"])
def unidades():
    if request.method == "POST":
        unidad_id = request.form["unidad_id"]
        
        # Verificar si ya existe una unidad con el mismo unidad_id
        unidad_existente = Unidad.query.filter_by(unidad_id=unidad_id).first()
        if unidad_existente:
            # Si la unidad ya existe, mostrar un mensaje de error
            return render_template("unidades.html", error="❌ El Unidad ID ya existe. Por favor, ingresa otro.", unidades=Unidad.query.all())

        # Si no existe, agregar la nueva unidad
        unidad = Unidad(
            unidad_id=request.form["unidad_id"],
            placas_unidad=request.form["placas_unidad"],
            operador=request.form["operador"],
            licencia=request.form["licencia"],
            caja1=request.form["caja1"],
            placas_caja1=request.form["placas_caja1"],
            caja2=request.form["caja2"],
            placas_caja2=request.form["placas_caja2"],
            dolly=request.form["dolly"],
            coordinador=request.form["coordinador"],
        )
        db.session.add(unidad)
        db.session.commit()
        return redirect(url_for("unidades"))

    unidades = Unidad.query.all()
    return render_template("unidades.html", unidades=unidades)

# -------------------------
# REGISTRAR VIAJE
# -------------------------
@app.route("/registrar_viaje", methods=["GET", "POST"])
@login_required
def registrar_viaje():

    unidades = Unidad.query.all()

    ultimo_folio = ""
    ultimo_origen = ""
    ultimo_destino = ""
    ultimo_cliente = ""

    if request.method == "POST":

        tipo_movimiento = request.form.get("tipo_movimiento")

        if not tipo_movimiento:
            return render_template(
                "registrar_viaje.html",
                unidades=unidades,
                error="❌ El tipo de movimiento es obligatorio."
            )

        folio_usuario = request.form.get("folio") if tipo_movimiento != "BAJA" else None

        # 🔹 Validar folio duplicado
        if folio_usuario:
            # 🔹 Validar folio duplicado por tipo de movimiento
            if folio_usuario:

               folio_existente = Viaje.query.filter_by(
                    folio=folio_usuario,
                    tipo_movimiento=tipo_movimiento
                ).first()

            if folio_existente:
                    flash("❌ Este folio ya tiene registrado este tipo de movimiento.")
                    return redirect(url_for("registrar_viaje"))

        unidad_id = request.form.get("unidad_id")

        def convertir_fecha(valor):
            if valor and valor.strip() != "":
                return datetime.strptime(valor, "%Y-%m-%dT%H:%M")
            return None

        fecha_descarga = convertir_fecha(request.form.get("fecha_descarga"))
        fecha_arribo_descarga = convertir_fecha(request.form.get("fecha_arribo_descarga"))
        fecha_retorno_descarga = convertir_fecha(request.form.get("fecha_retorno_descarga"))
        fecha_baja = convertir_fecha(request.form.get("fecha_baja"))

        # 🔹 Buscar último viaje CARGA
        if tipo_movimiento in ["DESCARGA", "ARRIBO_DESCARGA", "RETORNO"]:

            ultimo_viaje = (
                Viaje.query
                .filter_by(unidad_id=unidad_id, tipo_movimiento="CARGA")
                .order_by(Viaje.fecha_registro.desc())
                .first()
            )

            if ultimo_viaje:
                ultimo_folio = ultimo_viaje.folio
                ultimo_origen = ultimo_viaje.origen
                ultimo_destino = ultimo_viaje.destino
                ultimo_cliente = ultimo_viaje.cliente

        unidad = Unidad.query.get(unidad_id)

        viaje = Viaje(
            fecha_registro=datetime.now(ZONA_MX),
            unidad_id=unidad_id,
            folio=folio_usuario,
            origen=request.form.get("origen"),
            destino=request.form.get("destino"),
            tipo_movimiento=tipo_movimiento,
            cliente=(
                ultimo_cliente
                if tipo_movimiento in ["DESCARGA", "ARRIBO_DESCARGA", "RETORNO"]
                else request.form.get("cliente")
            ),
            fecha_descarga=fecha_descarga if tipo_movimiento == "DESCARGA" else None,
            fecha_arribo_descarga=fecha_arribo_descarga if tipo_movimiento == "ARRIBO_DESCARGA" else None,
            fecha_retorno_descarga=fecha_retorno_descarga if tipo_movimiento == "RETORNO" else None,
            fecha_baja=fecha_baja if tipo_movimiento == "BAJA" else None,
            coordinador=session.get("nombre"),
            ultimo_editado_por=session.get("nombre"),
            fecha_ultima_edicion=datetime.now(ZONA_MX)
        )

        db.session.add(viaje)
        db.session.commit()

        # =====================================
        # 🔔 CREAR NOTIFICACIÓN AUTOMÁTICA
        # =====================================

        operador = unidad.operador if unidad and unidad.operador else "SIN OPERADOR"

        mensaje = f"""
        🚛 {tipo_movimiento}
        Unidad: {unidad.unidad_id if unidad else 'N/A'}
        Operador: {operador}
        Origen: {viaje.origen}
        Destino: {viaje.destino}
        Registrado por: {session.get('nombre')}
        """

        nueva_notificacion = Notificacion(
            mensaje=mensaje,
            leida=False,
            fecha=datetime.now(ZONA_MX)
        )

        db.session.add(nueva_notificacion)
        db.session.commit()

        return redirect(url_for("registrar_viaje"))

    return render_template(
        "registrar_viaje.html",
        unidades=unidades,
        ultimo_folio=ultimo_folio,
        ultimo_origen=ultimo_origen,
        ultimo_destino=ultimo_destino,
        ultimo_cliente=ultimo_cliente
    )

# DISPONIBILIDAD
# -------------------------
@app.route("/disponibilidad")
def disponibilidad():

    unidades = Unidad.query.all()
    ahora = datetime.now(ZONA_MX)

    disponibles = []
    arribaron_a_descargar = []


    # =========================
    # función para corregir timezone
    # =========================
    def fix(fecha):
        if fecha and fecha.tzinfo is None:
            return ZONA_MX.localize(fecha)
        return fecha


    for unidad in unidades:

        # =====================================
        # OBTENER EL ULTIMO MOVIMIENTO REAL
        # =====================================
        ultimo = (
            Viaje.query.filter_by(
                unidad_id=unidad.unidad_id
            )
            .order_by(Viaje.fecha_registro.desc())
            .first()
        )

        if not ultimo:
            continue


        tipo = ultimo.tipo_movimiento
        cliente = ultimo.cliente


        # =====================================
        # ARRIBARON A DESCARGAR
        # =====================================
        if tipo == "ARRIBO_DESCARGA" and ultimo.fecha_arribo_descarga:

            fecha_arribo = fix(
                ultimo.fecha_arribo_descarga
            )

            arribaron_a_descargar.append({

                "unidad_id": unidad.unidad_id,
                "operador": unidad.operador,
                "fecha_arribo_descarga": fecha_arribo,
                "cliente": cliente,
                "origen": ultimo.origen,
                "destino": ultimo.destino,
                "coordinador": unidad.coordinador,

            })

            continue


        # =====================================
        # DISPONIBLES
        # =====================================

        fecha_base = None


        # HEINEKEN → SOLO RETORNO
        if cliente == "HEINEKEN":

            if tipo == "RETORNO" and ultimo.fecha_retorno_descarga:

                fecha_base = fix(
                    ultimo.fecha_retorno_descarga
                )


        # OTROS CLIENTES → DESCARGA
        else:

            if tipo == "DESCARGA" and ultimo.fecha_descarga:

                fecha_base = fix(
                    ultimo.fecha_descarga
                )


        if fecha_base:

            tiempo = ahora - fecha_base

            disponibles.append({

                "unidad_id": unidad.unidad_id,
                "operador": unidad.operador,
                "fecha_descarga": fecha_base,
                "dias_disponible": tiempo.days,
                "dias": tiempo.days,
                "horas": tiempo.seconds // 3600,
                "cliente": cliente,
                "origen": ultimo.origen,
                "destino": ultimo.destino,
                "coordinador": unidad.coordinador,

            })


    # =====================================
    # ORDENAR
    # =====================================

    disponibles.sort(
    key=lambda x: (x["dias"], x["horas"]),
    reverse=True
)

    arribaron_a_descargar.sort(
        key=lambda x: x["fecha_arribo_descarga"],
        reverse=False
    )


    # =====================================
    # ENVIAR A HTML
    # =====================================

    return render_template(
        "disponibilidad.html",
        disponibles=disponibles,
        arribaron_a_descargar=arribaron_a_descargar
    )

# -------------------------
# API
# -------------------------
@app.route("/api/unidad/<unidad_id>")
def api_unidad(unidad_id):
    unidad = Unidad.query.filter_by(unidad_id=unidad_id).first()

    if not unidad:
        return jsonify({"error": "Unidad no encontrada"}), 404

    return jsonify({
        "unidad_id": unidad.unidad_id,
        "placas_unidad": unidad.placas_unidad,
        "operador": unidad.operador,
        "licencia": unidad.licencia,
        "caja1": unidad.caja1,
        "placas_caja1": unidad.placas_caja1,
        "caja2": unidad.caja2,
        "placas_caja2": unidad.placas_caja2,
        "dolly": unidad.dolly,
        "coordinador": unidad.coordinador
        
    })

@app.route("/eliminar_viaje/<int:id>", methods=["POST"])
def eliminar_viaje(id):

    if session.get("rol") != "ADMIN":
        flash("❌ No tienes permiso")
        return redirect(url_for("historico_view"))

    viaje = Viaje.query.get_or_404(id)

    db.session.delete(viaje)
    db.session.commit()

    flash("🗑️ Registro eliminado")
    return redirect(url_for("historico_view"))





@app.route("/ocultar_notificacion/<int:id>", methods=["POST"])
@login_required
def ocultar_notificacion(id):

    noti = Notificacion.query.get_or_404(id)
    noti.leida = True
    db.session.commit()

    return "", 204

from flask import g

@app.context_processor
def inject_notificaciones():
    if "user_id" in session:
        hoy = datetime.now(ZONA_MX).date()

        total = Notificacion.query.filter(
            db.func.date(Notificacion.fecha) == hoy,
            Notificacion.leida == False
        ).count()

        return dict(total_notificaciones=total)

    return dict(total_notificaciones=0)

@app.route("/notificaciones")
@login_required
def ver_notificaciones():

    hoy = datetime.now(ZONA_MX).date()

    notificaciones = Notificacion.query.filter(
        db.func.date(Notificacion.fecha) == hoy,
        Notificacion.leida == False
    ).order_by(Notificacion.fecha.desc()).all()

    return render_template(
        "notificaciones.html",
        notificaciones=notificaciones
    )
# -------------------------
# ELIMINAR UNIDAD
# -------------------------
@app.route("/eliminar_unidad/<unidad_id>", methods=["GET"])
def eliminar_unidad(unidad_id):
    unidad = Unidad.query.get(unidad_id)
    if unidad:
        db.session.delete(unidad)
        db.session.commit()
    return redirect(url_for("unidades"))

# -------------------------
# EDITAR UNIDAD
# -------------------------
@app.route("/editar_unidad/<unidad_id>", methods=["GET", "POST"])
def editar_unidad(unidad_id):
    unidad = Unidad.query.get(unidad_id)  # Obtener la unidad por su ID

    if request.method == "POST":
        # Obtener los datos del formulario
        unidad.unidad_id = request.form["unidad_id"]
        unidad.placas_unidad = request.form["placas_unidad"]
        unidad.operador = request.form["operador"]
        unidad.licencia = request.form["licencia"]
        unidad.caja1 = request.form["caja1"]
        unidad.placas_caja1 = request.form["placas_caja1"]
        unidad.caja2 = request.form["caja2"]
        unidad.placas_caja2 = request.form["placas_caja2"]
        unidad.dolly = request.form["dolly"]
        unidad.coordinador = request.form["coordinador"]

        # Guardar los cambios en la base de datos
        db.session.commit()
        return redirect(url_for('unidades'))  # Redirigir de vuelta a la lista de unidades

    return render_template("editar_unidad.html", unidad=unidad)  # Mostrar el formulario con la unidad a editar

@app.route("/api/notificaciones_nuevas")
@login_required
def api_notificaciones_nuevas():

    hoy = datetime.now(ZONA_MX).date()

    notificaciones = Notificacion.query.filter(
        db.func.date(Notificacion.fecha) == hoy,
        Notificacion.leida == False
    ).order_by(Notificacion.id.desc()).limit(5).all()

    resultado = []

    for n in notificaciones:
        resultado.append({
            "id": n.id,
            "mensaje": n.mensaje
        })

    return jsonify(resultado)


@app.route("/editar_viaje/<int:id>", methods=["GET", "POST"])
@login_required
def editar_viaje(id):

    viaje = Viaje.query.get_or_404(id)

    if request.method == "POST":

        viaje.folio = request.form["folio"]
        viaje.unidad_id = request.form["unidad_id"]
        viaje.origen = request.form["origen"]
        viaje.destino = request.form["destino"]
        viaje.tipo_movimiento = request.form["tipo_movimiento"]
        viaje.cliente = request.form["cliente"]

        # 🔥 Siempre registrar quién editó
        viaje.ultimo_editado_por = session["nombre"]

        if session["rol"] == "ADMIN":

            viaje.coordinador = request.form["coordinador"]

            # 🔥 Convertir fechas correctamente
            fecha_registro = request.form.get("fecha_registro")
            fecha_descarga = request.form.get("fecha_descarga")
            fecha_arribo = request.form.get("fecha_arribo_descarga")
            fecha_retorno = request.form.get("fecha_retorno_descarga")
            fecha_baja = request.form.get("fecha_baja")

            viaje.fecha_registro = datetime.strptime(fecha_registro, "%Y-%m-%dT%H:%M") if fecha_registro else None
            viaje.fecha_descarga = datetime.strptime(fecha_descarga, "%Y-%m-%dT%H:%M") if fecha_descarga else None
            viaje.fecha_arribo_descarga = datetime.strptime(fecha_arribo, "%Y-%m-%dT%H:%M") if fecha_arribo else None
            viaje.fecha_retorno_descarga = datetime.strptime(fecha_retorno, "%Y-%m-%dT%H:%M") if fecha_retorno else None
            viaje.fecha_baja = datetime.strptime(fecha_baja, "%Y-%m-%dT%H:%M") if fecha_baja else None

        db.session.commit()
        return redirect(url_for("historico_view"))

    return render_template("editar_viaje.html", viaje=viaje)

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file



# ...
from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
from io import BytesIO


from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy


from sqlalchemy import func


# Ruta para mostrar el historial
@app.route("/historico_view")
def historico_view():
    # Obtener todos los registros de las unidades y los viajes
    unidades = Unidad.query.all()
    viajes = Viaje.query.all()

    return render_template("historico.html", unidades=unidades, viajes=viajes)

# Ruta para exportar el historial a Excel
from flask import Flask, render_template, request, redirect, url_for, send_file


@app.route("/historico")
def historico():
    # Obtener los registros de las unidades y los viajes
    unidades = Unidad.query.all()
    viajes = Viaje.query.all()

    # Convertir las unidades a un DataFrame
    unidades_data = []
    for unidad in unidades:
        unidades_data.append({
            'Unidad ID': unidad.unidad_id,
            'Placas Unidad': unidad.placas_unidad,
            'Operador': unidad.operador,
            'Licencia': unidad.licencia,
            'Caja 1': unidad.caja1,
            'Placas Caja 1': unidad.placas_caja1,
            'Caja 2': unidad.caja2,
            'Placas Caja 2': unidad.placas_caja2,
            'Dolly': unidad.dolly,
            'Coordinador': unidad.coordinador
        })
    
    # Convertir viajes a un DataFrame
    viajes_data = []
    for viaje in viajes:
        viajes_data.append({
            'Folio': viaje.folio,
            'Unidad ID': viaje.unidad_id,
            'Origen': viaje.origen,
            'Destino': viaje.destino,
            'Tipo Movimiento': viaje.tipo_movimiento,
            'Fecha Registro': viaje.fecha_registro,
            'Fecha Descarga': viaje.fecha_descarga
        })

    # Crear DataFrames de pandas
    unidades_df = pd.DataFrame(unidades_data)
    viajes_df = pd.DataFrame(viajes_data)

    # Crear un archivo Excel en memoria
    with BytesIO() as output:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            unidades_df.to_excel(writer, sheet_name='Unidades', index=False)
            viajes_df.to_excel(writer, sheet_name='Viajes', index=False)
        
        # Asegurarse de que el archivo esté en la posición correcta para enviarlo
        output.seek(0)
        
        # Enviar el archivo Excel al cliente
        return send_file(output, as_attachment=True, download_name="historico.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")





@app.route("/api/historial_unidad/<unidad_id>")
def historial_unidad(unidad_id):

    viajes = (
        Viaje.query
        .filter_by(unidad_id=unidad_id)
        .order_by(Viaje.fecha_registro.desc())
        .limit(5)
        .all()
    )

    resultado = []

    for v in viajes:
        resultado.append({
            "tipo": v.tipo_movimiento,
            "fecha": v.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "cliente": v.cliente or "",
            "origen": v.origen or "",
            "destino": v.destino or ""
        })

    return jsonify(resultado)

@app.route("/api/unidades/buscar")
def buscar_unidades():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify([])

    resultados = (
        Unidad.query
        .filter(Unidad.unidad_id.ilike(f"%{q}%"))
        .order_by(Unidad.unidad_id)
        .limit(10)
        .all()
    )

    return jsonify([u.unidad_id for u in resultados])
from flask import send_file



@app.route("/exportar_historico")
def exportar_historico():
    # Obtener los registros de las unidades y los viajes
    unidades = Unidad.query.all()
    viajes = Viaje.query.all()

    # Convertir las unidades a un DataFrame
    unidades_data = []
    for unidad in unidades:
        unidades_data.append({
            'Unidad ID': unidad.unidad_id,
            'Placas Unidad': unidad.placas_unidad,
            'Operador': unidad.operador,
            'Licencia': unidad.licencia,
            'Caja 1': unidad.caja1,
            'Placas Caja 1': unidad.placas_caja1,
            'Caja 2': unidad.caja2,
            'Placas Caja 2': unidad.placas_caja2,
            'Dolly': unidad.dolly,
            'Coordinador': unidad.coordinador
        })
    
    # Convertir viajes a un DataFrame
    viajes_data = []
    for viaje in viajes:
        viajes_data.append({
            'Folio': viaje.folio,
            'Unidad ID': viaje.unidad_id,
            'Origen': viaje.origen,
            'Destino': viaje.destino,
            'Tipo Movimiento': viaje.tipo_movimiento,
            'cliente': viaje.cliente,
            'Fecha Carga': viaje.fecha_registro,
            'Fecha Arribo Descarga' : viaje.fecha_arribo_descarga,
            'Fecha Descarga': viaje.fecha_descarga, 
            'Fecha Retorno Descarga' : viaje.fecha_retorno_descarga,
            'Fecha Baja' : viaje.fecha_baja,
            'Coordinador' : viaje.coordinador
        })

    # Crear DataFrames de pandas
    unidades_df = pd.DataFrame(unidades_data)
    viajes_df = pd.DataFrame(viajes_data)

    # Crear el archivo Excel en memoria
    try:
        output = BytesIO()  # Usar un flujo de bytes en memoria
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            unidades_df.to_excel(writer, sheet_name='Unidades', index=False)
            viajes_df.to_excel(writer, sheet_name='Viajes', index=False)

        # Rewind the output file stream to the beginning
        output.seek(0)

        # Enviar el archivo Excel al cliente
        return send_file(output, as_attachment=True, download_name="historico.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        return jsonify({"error": f"No se pudo generar el archivo Excel. Error: {str(e)}"})

@app.route("/top_rutas")
def top_rutas():

    rutas = (
        db.session.query(
            Viaje.origen,
            Viaje.destino,
            func.count(Viaje.id).label("total"),
            func.max(Viaje.cliente).label("cliente")
        )
        .group_by(Viaje.origen, Viaje.destino)
        .order_by(func.count(Viaje.id).desc())
        .limit(20)
        .all()
    )

    rutas_data = []
    for r in rutas:
        rutas_data.append({
            "origen": r.origen,
            "destino": r.destino,
            "total": r.total,
            "cliente": r.cliente
        })

    return render_template(
        "top_rutas.html",
        rutas=rutas_data
    )


@app.route("/historico_ruta")
def historico_ruta():

    origen = request.args.get("origen")
    destino = request.args.get("destino")

    viajes = (
        db.session.query(Viaje)
        .filter(Viaje.origen == origen, Viaje.destino == destino)
        .order_by(Viaje.fecha_registro.desc())
        .all()
    )

    return render_template(
        "historico_ruta.html",
        origen=origen,
        destino=destino,
        viajes=viajes
    )


@app.route("/api/ultimo_folio_carga/<unidad_id>")
def obtener_ultimo_folio_carga(unidad_id):
    # Buscar el último viaje de tipo "CARGA" para la unidad
    ultimo_viaje = Viaje.query.filter_by(unidad_id=unidad_id, tipo_movimiento="CARGA").order_by(Viaje.fecha_registro.desc()).first()

    if ultimo_viaje:
        return jsonify({
            "folio": ultimo_viaje.folio,
            "origen": ultimo_viaje.origen,
            "destino": ultimo_viaje.destino,
            "cliente": ultimo_viaje.cliente  # Asegúrate de incluir el cliente
        })
    else:
        return jsonify({
            "folio": None,
            "origen": None,
            "destino": None,
            "cliente": None  # Si no hay un viaje CARGA, devolver None
        })





@app.route("/dashboard")
def dashboard():

    hoy = datetime.now(ZONA_MX)
    inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = hoy.replace(hour=23, minute=59, second=59)

    # ==============================
    # 1️⃣ CARGAS DEL DÍA
    # ==============================
    viajes_carga = db.session.query(func.count(Viaje.id)).filter(
        Viaje.tipo_movimiento == "CARGA",
        Viaje.fecha_registro.between(inicio, fin)
    ).scalar() or 0

    # ==============================
    # 2️⃣ ÚLTIMO MOVIMIENTO POR UNIDAD
    # ==============================
    subquery = (
        db.session.query(
            Viaje.unidad_id,
            func.max(Viaje.fecha_registro).label("ultima_fecha")
        )
        .group_by(Viaje.unidad_id)
        .subquery()
    )

    ultimos = (
        db.session.query(Viaje)
        .join(
            subquery,
            (Viaje.unidad_id == subquery.c.unidad_id) &
            (Viaje.fecha_registro == subquery.c.ultima_fecha)
        )
        .all()
    )

    unidades_descargadas = 0
    unidades_arribo = 0

    for v in ultimos:

        if v.tipo_movimiento == "ARRIBO_DESCARGA":
            unidades_arribo += 1

        if (
            (v.cliente == "HEINEKEN" and v.tipo_movimiento == "RETORNO") or
            (v.cliente != "HEINEKEN" and v.tipo_movimiento == "DESCARGA")
        ):
            unidades_descargadas += 1

    # ==============================
    # 3️⃣ VIAJES POR CLIENTE (CARGAS HOY)
    # ==============================
    clientes_query = (
        db.session.query(
            Viaje.cliente,
            func.count(Viaje.id).label("total")
        )
        .filter(
            Viaje.fecha_registro.between(inicio, fin),
            Viaje.tipo_movimiento == "CARGA"
        )
        .group_by(Viaje.cliente)
        .all()
    )

    data_clientes = {
        (c[0] if c[0] else "SIN CLIENTE"): c[1]
        for c in clientes_query
    }

    # ==============================
    # 4️⃣ VIAJES POR COORDINADOR (CARGAS HOY)
    # ==============================
    coordinador_query = (
        db.session.query(
            Viaje.coordinador,
            func.count(Viaje.id).label("total")
        )
        .filter(
            Viaje.fecha_registro.between(inicio, fin),
            Viaje.tipo_movimiento == "CARGA"
        )
        .group_by(Viaje.coordinador)
        .all()
    )

    data_coordinadores = {
        (c[0] if c[0] else "SIN COORDINADOR"): c[1]
        for c in coordinador_query
    }

    # ==============================
    # 5️⃣ TOP CLIENTE DEL DÍA (CARGAS)
    # ==============================
    top_cliente = (
        db.session.query(
            Viaje.cliente,
            func.count(Viaje.id).label("total")
        )
        .filter(
            Viaje.fecha_registro.between(inicio, fin),
            Viaje.tipo_movimiento == "CARGA"
        )
        .group_by(Viaje.cliente)
        .order_by(func.count(Viaje.id).desc())
        .first()
    )

    # ==============================
    # 6️⃣ TOP RUTA DEL DÍA (CARGAS)
    # ==============================
    top_ruta = (
        db.session.query(
            Viaje.origen,
            Viaje.destino,
            func.count(Viaje.id).label("total")
        )
        .filter(
            Viaje.fecha_registro.between(inicio, fin),
            Viaje.tipo_movimiento == "CARGA"
        )
        .group_by(Viaje.origen, Viaje.destino)
        .order_by(func.count(Viaje.id).desc())
        .first()
    )

    # ==============================
    # DATOS PARA GRAFICA ESTADOS
    # ==============================
    data_estados = {
        "Disponibles": unidades_descargadas,
        "Arribo Descarga": unidades_arribo
    }

    return render_template(
        "dashboard.html",
        viajes_carga=viajes_carga,
        unidades_descargadas=unidades_descargadas,
        arribos_descarga=unidades_arribo,
        data_estados=data_estados,
        data_clientes=data_clientes,
        data_coordinadores=data_coordinadores,
        top_cliente=top_cliente,
        top_ruta=top_ruta
    )


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
