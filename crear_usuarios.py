# crear_usuarios.py

from app import app, db, Usuario  # ← cambia "app" si tu archivo principal tiene otro nombre

def crear_usuarios():

    with app.app_context():

        # Verificar si ya existen
        if Usuario.query.filter_by(username="ADMIN").first():
            print("⚠️ El usuario ADMIN ya existe")
            return

        admin = Usuario(
            nombre="JOSIMAR",
            username="ADMIN",
            rol="ADMIN"
        )
        admin.set_password("PAKETAXO32")

        coord = Usuario(
            nombre="XIMENA",
            username="XIMENA",
            rol="COORDINADOR"
        )
        coord.set_password("Ximena2026@")

        db.session.add(admin)
        db.session.add(coord)
        db.session.commit()

        print("✅ Usuarios creados correctamente")

if __name__ == "__main__":
    crear_usuarios()