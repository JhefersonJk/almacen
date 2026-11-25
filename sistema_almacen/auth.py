"""Cuentas por rol y sesiones opacas revocables, sin contraseñas predeterminadas."""
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select, text
from typing import Literal

from . import models as m

Role = Literal['administracion','almacen','produccion','gerencia']
COOKIE='tintastock_session'
TTL=12*60*60
ROLES={'administracion','almacen','produccion','gerencia'}
STOCK_ROLES={'administracion','almacen'}
FINANCE_ROLES={'administracion','gerencia'}
MOVE_ROLES={'administracion','almacen','produccion'}


def password_hash(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=2**15,r=8,p=3,maxmem=64*1024*1024,dklen=32)
    return f'scrypt$32768$8$3${salt.hex()}${digest.hex()}'


def check_password(password, stored):
    try:
        scheme,n,r,p,salt,digest=stored.split('$')
        if (scheme,n,r,p)!=('scrypt','32768','8','3'): return False
        actual=hashlib.scrypt(password.encode('utf-8'),salt=bytes.fromhex(salt),n=int(n),r=int(r),p=int(p),maxmem=64*1024*1024,dklen=32)
        return hmac.compare_digest(actual,bytes.fromhex(digest))
    except (ValueError,TypeError): return False


def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()


def public_user(user):
    return {'id':user.id,'username':user.username,'displayName':user.display_name,'role':user.role,'active':user.active}


@dataclass(frozen=True)
class Actor:
    id:str
    username:str
    display_name:str
    role:str


def actor_from_session(db,token):
    if not token or len(token)>150: return None
    row=db.get(m.UserSession,token_hash(token))
    if not row or row.expires_at<=int(time.time()): return None
    u=db.get(m.User,row.user_id)
    return Actor(u.id,u.username,u.display_name,u.role) if u and u.active else None


def require(actor,roles):
    if actor.role not in roles: raise HTTPException(403,'Tu rol no tiene permiso para esta operación.')
    return actor


class Login(BaseModel):
    username:str=Field(min_length=1,max_length=40)
    password:str=Field(min_length=1,max_length=128)


class UserInput(BaseModel):
    username:str=Field(min_length=3,max_length=40,pattern=r'^[A-Za-z0-9._-]+$')
    displayName:str=Field(min_length=1,max_length=120)
    role:Role
    active:bool=True
    password:str|None=Field(default=None,min_length=10,max_length=128,examples=['contraseña de al menos 10 caracteres'])

    @field_validator('displayName')
    @classmethod
    def display_clean(cls,v):
        if not v.strip(): raise ValueError('Ingresa el nombre.')
        return v.strip()

    @field_validator('username')
    @classmethod
    def lower(cls,v): return v.lower()

    # No quitar espacios de una contraseña. Usamos un validador previo separado en create/update.


class PasswordChange(BaseModel):
    currentPassword:str=Field(min_length=1,max_length=128)
    newPassword:str=Field(min_length=10,max_length=128)


def prepare_password(value):
    if not isinstance(value,str) or len(value)<10 or len(value)>128 or not value.strip():
        raise HTTPException(422,'Usa una contraseña de 10 a 128 caracteres.')
    return password_hash(value)


def create_user(db,v,*,first=False):
    if first and db.scalar(select(func.count()).select_from(m.User)):
        raise HTTPException(409,'Ya existen cuentas. Usa el gestor de usuarios.')
    if not v.password: raise HTTPException(422,'Es necesaria una contraseña inicial.')
    if db.scalar(select(m.User.id).where(m.User.username==v.username)):
        raise HTTPException(409,'Ese usuario ya existe.')
    user=m.User(id=str(uuid4()),username=v.username,display_name=v.displayName,role=v.role,active=v.active,password_hash=prepare_password(v.password))
    db.add(user);db.flush();return user


def update_user(db,key,v):
    user=db.get(m.User,key)
    if not user: raise HTTPException(404,'Usuario no encontrado.')
    existing=db.scalar(select(m.User.id).where(m.User.username==v.username,m.User.id!=key))
    if existing: raise HTTPException(409,'Ese usuario ya existe.')
    if user.role=='administracion' and user.active and (v.role!='administracion' or not v.active):
        others=db.scalar(select(func.count()).select_from(m.User).where(m.User.role=='administracion',m.User.active==True,m.User.id!=key))
        if not others: raise HTTPException(409,'Debe quedar al menos una cuenta de administración activa.')
    # Una cuenta editada debe iniciar sesión otra vez para recoger los permisos nuevos.
    if v.password: user.password_hash=prepare_password(v.password)
    user.username=v.username;user.display_name=v.displayName;user.role=v.role;user.active=v.active
    db.execute(delete(m.UserSession).where(m.UserSession.user_id==key));db.flush();return user


def apply_visibility(state,actor):
    if actor.role not in FINANCE_ROLES:
        for p in state['products']: p['cost']=0
        for x in state['movements']: x['cost']=0
        for o in state['orders']: o['budget']=0
    if actor.role=='produccion': state['suppliers']=[]
    return state


class LoginLimiter:
    """Límite de intentos por origen y usuario, con memoria acotada (un proceso local)."""
    def __init__(self): self.entries={};self.lock=Lock()
    def attempt(self,origin,username):
        now=time.monotonic();keys=[('ip',origin),('user',username.casefold())]
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if v[0]>now-300}
            if any(self.entries.get(k,(now,0))[1]>= (30 if k[0]=='ip' else 8) for k in keys):
                raise HTTPException(429,'Demasiados intentos. Espera unos minutos antes de reintentar.')
            if len(self.entries)>4096: raise HTTPException(429,'Demasiados intentos. Reintenta más tarde.')
            for k in keys:
                start,count=self.entries.get(k,(now,0));self.entries[k]=(start,count+1)
    def success(self,origin,username):
        with self.lock: self.entries.pop(('user',username.casefold()),None)


# Un hash de comparación fijo se usa al validar cuentas inexistentes para no revelar su existencia.
DUMMY_HASH='scrypt$32768$8$3$00000000000000000000000000000000$0000000000000000000000000000000000000000000000000000000000000000'
