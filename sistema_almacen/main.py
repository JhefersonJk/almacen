"""FastAPI: almacén con SQLite, sesiones y permisos, separado de Gráfica Ali."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
import secrets
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from . import auth, models as m, operations as op, schemas as s
from .database import Base, configure

DIST = Path(__file__).resolve().parents[1] / 'dist'
Revision = Annotated[int, Header(alias='X-Inventory-Revision', ge=0)]


def create_app(database_url=None):
    engine,sessions=configure(database_url)
    limiter=auth.LoginLimiter()

    @asynccontextmanager
    async def lifespan(_app):
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(text('INSERT OR IGNORE INTO inventory_revision (id,revision) VALUES (1,0)'))
        yield
        engine.dispose()

    app=FastAPI(title='TintaStock · API de almacén',version='0.4.0',lifespan=lifespan)

    @app.middleware('http')
    async def security_headers(request,call_next):
        if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            # Las escrituras requieren un encabezado no simple del cliente de la misma procedencia.
            # No se habilita CORS de terceros. La cookie de sesión es SameSite=Strict.
            if request.headers.get('X-TintaStock-Client')!='1':
                return JSONResponse(status_code=403,content={'detail':'Solicitud no autorizada por el cliente.'},headers={'Cache-Control':'no-store'})
        response=await call_next(request)
        if request.url.path.startswith('/api/') or request.url.path in ('/','/index.html','/sw.js'):
            response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request,exc):
        return JSONResponse(status_code=422,content={'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in exc.errors()]})

    @app.exception_handler(OperationalError)
    async def database_busy(_request,_exc):
        return JSONResponse(status_code=503,content={'detail':'Base temporalmente no disponible. Reintenta.'})

    def current(request:Request):
        with sessions() as db: actor=auth.actor_from_session(db,request.cookies.get(auth.COOKIE))
        if not actor: raise HTTPException(401,'Inicia sesión para continuar.')
        return actor

    Actor=Annotated[auth.Actor,Depends(current)]

    def admin(actor:Actor): return auth.require(actor,{'administracion'})
    Admin=Annotated[auth.Actor,Depends(admin)]

    @app.get('/api/health')
    def health(): return {'status':'ok','mode':'server','database':'sqlite'}

    @app.get('/api/auth/status')
    def auth_status():
        with sessions() as db: return {'setupRequired':not bool(db.scalar(select(func.count()).select_from(m.User)))}

    @app.post('/api/auth/login')
    def login(v:auth.Login,request:Request):
        username=v.username.strip().lower();origin=request.client.host if request.client else 'local'
        limiter.attempt(origin,username)
        with sessions() as db:
            u=db.scalar(select(m.User).where(m.User.username==username));stored=u.password_hash if u else auth.DUMMY_HASH
            if not auth.check_password(v.password,stored) or not u or not u.active:
                raise HTTPException(401,'Usuario o contraseña incorrectos.')
            key=u.id
        with sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'));u=db.get(m.User,key)
            if not u or not u.active or u.password_hash!=stored: raise HTTPException(401,'Usuario o contraseña incorrectos.')
            token=secrets.token_urlsafe(32)
            db.execute(delete(m.UserSession).where(m.UserSession.expires_at<=int(time.time())))
            old=request.cookies.get(auth.COOKIE)
            if old: db.execute(delete(m.UserSession).where(m.UserSession.token_hash==auth.token_hash(old)))
            db.add(m.UserSession(token_hash=auth.token_hash(token),user_id=u.id,expires_at=int(time.time())+auth.TTL))
            body=auth.public_user(u);db.commit()
        limiter.success(origin,username)
        response=JSONResponse(body)
        response.set_cookie(auth.COOKIE,token,max_age=auth.TTL,httponly=True,secure=request.url.scheme=='https',samesite='strict',path='/')
        return response

    @app.get('/api/auth/me')
    def me(actor:Actor):
        return {'id':actor.id,'username':actor.username,'displayName':actor.display_name,'role':actor.role,'active':True}

    @app.post('/api/auth/logout')
    def logout(request:Request):
        token=request.cookies.get(auth.COOKIE)
        if token:
            with sessions() as db: db.execute(delete(m.UserSession).where(m.UserSession.token_hash==auth.token_hash(token)));db.commit()
        response=JSONResponse({'ok':True});response.delete_cookie(auth.COOKIE,path='/',secure=request.url.scheme=='https',httponly=True,samesite='strict');return response

    @app.post('/api/auth/password')
    def change_password(v:auth.PasswordChange,actor:Actor):
        with sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'));u=db.get(m.User,actor.id)
            if not u or not u.active or not auth.check_password(v.currentPassword,u.password_hash):raise HTTPException(400,'Contraseña actual incorrecta.')
            u.password_hash=auth.prepare_password(v.newPassword)
            db.execute(delete(m.UserSession).where(m.UserSession.user_id==actor.id));db.commit()
        return {'ok':True}

    @app.get('/api/users')
    def users(actor:Admin):
        with sessions() as db: return [auth.public_user(u) for u in db.scalars(select(m.User).order_by(m.User.username))]

    @app.post('/api/users',status_code=201)
    def add_user(v:auth.UserInput,actor:Admin):
        with sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'));u=auth.create_user(db,v);result=auth.public_user(u);db.commit();return result

    @app.put('/api/users/{key}')
    def edit_user(key:str,v:auth.UserInput,actor:Admin):
        with sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'));u=auth.update_user(db,key,v);result=auth.public_user(u);db.commit();return result

    @app.get('/api/state')
    def state(actor:Actor,since:Annotated[int|None,Query(ge=0)]=None):
        with sessions() as db:
            db.execute(text('BEGIN'))
            if since is not None and db.get(m.InventoryRevision,1).revision==since:return Response(status_code=204)
            return auth.apply_visibility(op.snapshot(db),actor)

    @app.get('/api/products')
    def products(actor:Actor,code:Annotated[str|None,Query(max_length=48)]=None):
        with sessions() as db:
            query=select(m.Product).order_by(m.Product.code)
            if code:query=query.where(m.Product.code==code.strip())
            result=[op.product_dict(p) for p in db.scalars(query)]
            if actor.role not in auth.FINANCE_ROLES:
                for p in result:p['cost']=0
            return result

    def write(revision,operation,actor):
        with sessions() as db:
            try:
                db.execute(text('BEGIN IMMEDIATE'));counter=db.get(m.InventoryRevision,1)
                if counter.revision!=revision:raise HTTPException(409,'El inventario cambió en otro dispositivo. Actualiza y confirma nuevamente.')
                operation(db);counter.revision+=1;db.flush();result=auth.apply_visibility(op.snapshot(db),actor);db.commit();return result
            except IntegrityError as exc:
                db.rollback();raise HTTPException(409,'Registro duplicado o relación inválida.') from exc

    @app.post('/api/products',status_code=201)
    def add_product(v:s.ProductInput,revision:Revision,actor:Actor):
        auth.require(actor,auth.STOCK_ROLES)
        if actor.role not in auth.FINANCE_ROLES:v=v.model_copy(update={'cost':0})
        return write(revision,lambda db:op.create_product(db,v,actor.username),actor)

    @app.put('/api/products/{key}')
    def update_product(key:str,v:s.ProductInput,revision:Revision,actor:Actor):
        auth.require(actor,auth.STOCK_ROLES)
        return write(revision,lambda db:op.edit_product(db,key,v,actor.role in auth.FINANCE_ROLES),actor)

    @app.post('/api/movements',status_code=201)
    def add_movement(v:s.MovementInput,revision:Revision,actor:Actor):
        auth.require(actor,auth.MOVE_ROLES)
        if actor.role=='produccion' and v.type not in ('salida','devolucion'):raise HTTPException(403,'Producción solo puede registrar retiros y devoluciones.')
        v=v.model_copy(update={'operator':actor.username})
        return write(revision,lambda db:op.move(db,v),actor)

    @app.post('/api/products/{key}/remnants',status_code=201)
    def add_remnant(key:str,v:s.RemnantInput,revision:Revision,actor:Actor):
        auth.require(actor,auth.STOCK_ROLES)
        return write(revision,lambda db:op.remnant(db,key,v,actor.username),actor)

    @app.post('/api/orders',status_code=201)
    def add_order(v:s.OrderInput,revision:Revision,actor:Admin):return write(revision,lambda db:op.create_order(db,v),actor)

    @app.put('/api/orders/{key}')
    def update_order(key:str,v:s.OrderInput,revision:Revision,actor:Admin):return write(revision,lambda db:op.edit_order(db,key,v),actor)

    @app.post('/api/suppliers',status_code=201)
    def add_supplier(v:s.SupplierInput,revision:Revision,actor:Actor):
        auth.require(actor,auth.STOCK_ROLES);return write(revision,lambda db:op.save_supplier(db,v),actor)

    @app.put('/api/suppliers/{key}')
    def update_supplier(key:str,v:s.SupplierInput,revision:Revision,actor:Actor):
        auth.require(actor,auth.STOCK_ROLES);return write(revision,lambda db:op.save_supplier(db,v,key),actor)

    @app.put('/api/backup/restore')
    def restore(v:s.Backup,revision:Revision,actor:Admin):return write(revision,lambda db:op.restore(db,v),actor)

    @app.get('/',response_class=HTMLResponse,include_in_schema=False)
    @app.get('/index.html',response_class=HTMLResponse,include_in_schema=False)
    def index():
        html=(DIST/'index.html').read_text(encoding='utf-8')
        return HTMLResponse(html.replace('<head>','<head><meta name="tintastock-mode" content="server">',1).replace('<html lang="es"','<html data-auth="required" lang="es"',1))

    app.mount('/',StaticFiles(directory=DIST),name='assets')
    return app

app=create_app()
