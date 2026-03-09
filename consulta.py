from werkzeug.security import generate_password_hash
from app import db, Usuario  # Asegúrate de que el modelo Usuario esté importado

# Crear un usuario con un nombre de usuario y una contraseña
usuario = Usuario(username="admin", password=generate_password_hash("admin123"))
db.session.add(usuario)
db.session.commit()
