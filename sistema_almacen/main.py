"""FastAPI: servidor de almacén con SQLite, separado del taller de Gráfica Ali."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from . import models as m, operations as op, schemas as s
from .database import Base, configure

DIST = Path(__file__).resolve().parents[1] / 'dist'
Revision = Annotated[int, Header(alias='X-Inventory-Revision', ge=0)]


def create_app(database_url=None):
    engine, sessions = configure(database_url)

    @asynccontextmanager
    async def lifespan(_app):
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(text('INSERT OR IGNORE INTO inventory_revision (id,revision) VALUES (1,0)'))
        yield
        engine.dispose()

    app = FastAPI(title='TintaStock · API de almacén',version='0.3.0',lifespan=lifespan)

    @app.middleware('http')
    async def no_cache(request, call_next):
        response=await call_next(request)
        if request.url.path.startswith('/api/') or request.url.path in ('/','/index.html','/sw.js'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.exception_handler(OperationalError)
    async def database_busy(_request,_exc):
        return JSONResponse(status_code=503,content={'detail':'Base de datos temporalmente no disponible. Reintenta.'})

    @app.get('/api/health')
    def health():
        return {'status':'ok','mode':'server','database':'sqlite'}

    @app.get('/api/state')
    def state(since: Annotated[int | None,Query(ge=0)]=None):
        # Snapshot coherente incluso cuando otro dispositivo registra un movimiento.
        with sessions() as db:
            db.execute(text('BEGIN'))
            if since is not None and db.get(m.InventoryRevision,1).revision==since:
                return Response(status_code=204)
            return op.snapshot(db)

    @app.get('/api/products')
    def products(code: Annotated[str | None,Query(max_length=48)]=None):
        with sessions() as db:
            query=select(m.Product).order_by(m.Product.code)
            if code: query=query.where(m.Product.code==code.strip())
            return [op.product_dict(p) for p in db.scalars(query)]

    def write(revision, operation):
        with sessions() as db:
            try:
                # No hay ventana entre leer el saldo y grabar movimiento/stock. SQLite serializa escrituras.
                db.execute(text('BEGIN IMMEDIATE'))
                counter=db.get(m.InventoryRevision,1)
                if counter.revision!=revision:
                    raise HTTPException(409,'El inventario cambió en otro dispositivo. Actualiza y confirma nuevamente.')
                operation(db)
                counter.revision+=1
                db.flush()
                result=op.snapshot(db)
                db.commit()
                return result
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(409,'Registro duplicado o relación inválida.') from exc

    @app.post('/api/products',status_code=201)
    def add_product(v:s.ProductInput,revision:Revision):
        return write(revision,lambda db:op.create_product(db,v))

    @app.put('/api/products/{key}')
    def update_product(key:str,v:s.ProductInput,revision:Revision):
        return write(revision,lambda db:op.edit_product(db,key,v))

    @app.post('/api/movements',status_code=201)
    def add_movement(v:s.MovementInput,revision:Revision):
        return write(revision,lambda db:op.move(db,v))

    @app.post('/api/products/{key}/remnants',status_code=201)
    def add_remnant(key:str,v:s.RemnantInput,revision:Revision):
        return write(revision,lambda db:op.remnant(db,key,v))

    @app.post('/api/orders',status_code=201)
    def add_order(v:s.OrderInput,revision:Revision):
        return write(revision,lambda db:op.create_order(db,v))

    @app.put('/api/orders/{key}')
    def update_order(key:str,v:s.OrderInput,revision:Revision):
        return write(revision,lambda db:op.edit_order(db,key,v))

    @app.post('/api/suppliers',status_code=201)
    def add_supplier(v:s.SupplierInput,revision:Revision):
        return write(revision,lambda db:op.save_supplier(db,v))

    @app.put('/api/suppliers/{key}')
    def update_supplier(key:str,v:s.SupplierInput,revision:Revision):
        return write(revision,lambda db:op.save_supplier(db,v,key))

    @app.put('/api/backup/restore')
    def restore(v:s.Backup,revision:Revision):
        return write(revision,lambda db:op.restore(db,v))

    @app.get('/',response_class=HTMLResponse,include_in_schema=False)
    @app.get('/index.html',response_class=HTMLResponse,include_in_schema=False)
    def index():
        html=(DIST/'index.html').read_text(encoding='utf-8')
        return HTMLResponse(html.replace('<head>','<head><meta name="tintastock-mode" content="server">',1))

    app.mount('/',StaticFiles(directory=DIST),name='assets')
    return app


app=create_app()
