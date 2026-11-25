"""Creación local de la primera cuenta administradora: python -m sistema_almacen.users."""
from getpass import getpass
import sys
from sqlalchemy import func,select,text
from .database import Base,configure
from . import auth,models  # registra todas las tablas


def main():
    engine,sessions=configure();Base.metadata.create_all(engine)
    if '--ensure' in sys.argv:
        with sessions() as db:
            if db.scalar(select(func.count()).select_from(models.User)):
                engine.dispose();return
    print('Crear primera cuenta de administración de TintaStock')
    username=input('Usuario (letras/números, punto, guion): ').strip()
    display=input('Nombre visible: ').strip()
    password=getpass('Contraseña (mínimo 10 caracteres): ')
    if password!=getpass('Repite la contraseña: '): raise SystemExit('Las contraseñas no coinciden.')
    try:
        v=auth.UserInput(username=username,displayName=display,role='administracion',password=password)
        with sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'));auth.create_user(db,v,first=True);db.commit()
    except Exception:
        raise SystemExit('No se pudo crear la cuenta. Comprueba los datos o usa el gestor si ya hay usuarios.') from None
    finally: engine.dispose()
    print('Cuenta creada. Inicia el servidor y entra con tu usuario.')

if __name__=='__main__': main()
