"""SQLite temporal: ningún dato del taller se abre o modifica."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sistema_almacen.main import create_app
from sistema_almacen.database import configure,Base
from sistema_almacen import auth

HEADERS={'X-TintaStock-Client':'1'}
PASSWORD='test-password-123'
def bootstrap(url):
    engine,S=configure(url);Base.metadata.create_all(engine)
    with S() as db: auth.create_user(db,auth.UserInput(username='admin',displayName='Administración de prueba',role='administracion',password=PASSWORD),first=True);db.commit()
    engine.dispose()

def login(c,username='admin',password=PASSWORD):
    r=c.post('/api/auth/login',headers=HEADERS,json={'username':username,'password':password});assert r.status_code==200,r.text;return r



@pytest.fixture()
def client(tmp_path):
    url=f'sqlite:///{tmp_path / "test.db"}';bootstrap(url)
    with TestClient(create_app(url)) as c:
        login(c);yield c


def write(c,path,data,revision=None,method='POST'):
    if revision is None: revision=c.get('/api/state').json()['revision']
    return c.request(method,path,json=data,headers={**HEADERS,'X-Inventory-Revision':str(revision)})


def product(c,**kw):
    return write(c,'/api/products',dict(code='VIN-001',name='Vinilo',category='Vinilo',unit='m',stock=10,min=1,cost=12.34,location='B-01',**kw))


def test_persistence_and_same_origin(tmp_path):
    url=f'sqlite:///{tmp_path / "persistent.db"}'
    bootstrap(url)
    with TestClient(create_app(url)) as c:
        login(c)
        assert c.get('/api/state').json()['products']==[]
        assert 'name="tintastock-mode" content="server"' in c.get('/').text
        assert c.get('/api/state').headers['cache-control']=='no-store'
        assert c.get('/api/state?since=0').status_code==204
        assert product(c).status_code==201
    with TestClient(create_app(url)) as c:
        login(c)
        assert c.get('/api/state').json()['products'][0]['stock']==10
        assert c.get('/api/products?code=vin-001').json()[0]['code']=='VIN-001'


def test_movement_atomic_and_precise(client):
    c=client;r=product(c);assert r.status_code==201
    key=r.json()['products'][0]['id']
    for _ in range(3): assert write(c,'/api/movements',{'productId':key,'type':'salida','qty':0.1}).status_code==201
    after=c.get('/api/state').json();assert after['products'][0]['stock']==9.7
    assert write(c,'/api/movements',{'productId':key,'type':'salida','qty':99}).status_code==409
    assert c.get('/api/state').json()==after
    assert write(c,'/api/movements',{'productId':key,'type':'entrada','qty':0.0001}).status_code==422
    assert write(c,'/api/movements',{'productId':key,'type':'entrada','qty':-1}).status_code==422
    assert write(c,'/api/movements',{'productId':key,'type':'traslado','location':'D-02'}).json()['products'][0]['location']=='D-02'
    assert write(c,'/api/movements',{'productId':key,'type':'ajuste','qty':0}).json()['products'][0]['stock']==0


def test_concurrent_devices(client):
    c=client;result=product(c).json();key=result['products'][0]['id'];rev=result['revision']
    def leave(): return write(c,'/api/movements',{'productId':key,'type':'salida','qty':6},rev)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:leave(),range(2)))
    assert sorted(r.status_code for r in results)==[201,409]
    state=c.get('/api/state').json();assert state['products'][0]['stock']==4
    assert len(state['movements'])==2


def test_duplicates_orders_suppliers_remnants_backup(client):
    c=client;r=product(c).json();p=r['products'][0];key=p['id'];
    assert write(c,'/api/products',{**p,'code':'vin-001'}).status_code==409
    s=write(c,'/api/suppliers',{'name':'Insumos'}).json()['suppliers'][0]
    assert write(c,f'/api/products/{key}',{**p,'supplier':'Insumos'},method='PUT').status_code==200
    assert write(c,f'/api/suppliers/{s["id"]}',{'name':'Insumos SA'},method='PUT').json()['products'][0]['supplier']=='Insumos SA'
    assert write(c,'/api/orders',{'code':'OT-001','name':'Carteles','state':'Pendiente','budget':150}).status_code==201
    assert write(c,'/api/movements',{'productId':key,'type':'salida','qty':1,'order':'OT-001'}).status_code==201
    r=write(c,f'/api/products/{key}/remnants',{'code':'VIN-002','qty':2,'detail':'Sobrante','location':'D-01'})
    assert r.status_code==201;state=r.json();assert sum(x['stock'] for x in state['products'])==9
    assert write(c,f'/api/products/{key}',{**state['products'][0],'stock':100},method='PUT').status_code==409
    # invalid import leaves all rows intact
    bad={**state,'movements':[{**state['movements'][0],'productId':'inexistente'}]}
    assert write(c,'/api/backup/restore',bad,method='PUT').status_code==400
    assert c.get('/api/state').json()==state
    assert write(c,'/api/backup/restore',{'products':[],'orders':[],'movements':[],'suppliers':[]},method='PUT').status_code==200
    restored=write(c,'/api/backup/restore',state,method='PUT');assert restored.status_code==200
    assert restored.json()['products']==state['products']
    assert restored.json()['movements']==state['movements']


def test_roles_and_sessions(client):
    c=client
    unauth=TestClient(c.app)
    assert unauth.get('/api/state').status_code==401
    assert unauth.get('/api/products').status_code==401
    assert unauth.get('/api/users').status_code==401
    assert c.post('/api/auth/logout').status_code==403 # missing same-origin client header
    creation=product(c).json();p=creation['products'][0];key=p['id']
    accounts={}
    for r in ('almacen','produccion','gerencia'):
        v=c.post('/api/users',headers=HEADERS,json={'username':r,'displayName':r.title(),'role':r,'password':PASSWORD})
        assert v.status_code==201,v.text;accounts[r]=v.json();assert 'password_hash' not in v.json()
    prod=TestClient(c.app);warehouse=TestClient(c.app);manager=TestClient(c.app)
    for r,other in [('produccion',prod),('almacen',warehouse),('gerencia',manager)]:login(other,r)
    assert prod.get('/api/state').json()['products'][0]['cost']==0
    assert prod.get('/api/products').json()[0]['cost']==0
    assert manager.get('/api/state').json()['products'][0]['cost']==12.34
    assert prod.get('/api/users').status_code==403
    assert warehouse.get('/api/users').status_code==403
    assert manager.get('/api/users').status_code==403
    assert write(prod,'/api/products',{**p,'code':'NEW-1'}).status_code==403
    assert write(prod,'/api/movements',{'productId':key,'type':'entrada','qty':1}).status_code==403
    assert write(prod,'/api/movements',{'productId':key,'type':'ajuste','qty':1}).status_code==403
    out=write(prod,'/api/movements',{'productId':key,'type':'salida','qty':2,'operator':'otro'});assert out.status_code==201
    assert out.json()['movements'][0]['operator']=='produccion'
    assert write(manager,'/api/movements',{'productId':key,'type':'salida','qty':1}).status_code==403
    assert write(warehouse,f'/api/products/{key}',{**p,'stock':8,'cost':0,'name':'Editado'},method='PUT').status_code==200
    assert c.get('/api/state').json()['products'][0]['cost']==12.34
    assert write(warehouse,'/api/backup/restore',{'products':[],'orders':[],'movements':[],'suppliers':[]},method='PUT').status_code==403
    # Desactivar cuenta revoca sesión; la administración activa final se conserva.
    u=accounts['produccion'];res=c.put('/api/users/'+u['id'],headers=HEADERS,json={**u,'active':False});assert res.status_code==200
    assert prod.get('/api/state').status_code==401
    admin=c.get('/api/auth/me').json();assert c.put('/api/users/'+admin['id'],headers=HEADERS,json={**admin,'active':False}).status_code==409
    assert manager.post('/api/auth/logout',headers=HEADERS).status_code==200
    assert manager.get('/api/state').status_code==401
    assert warehouse.post('/api/auth/password',headers=HEADERS,json={'currentPassword':PASSWORD,'newPassword':'another-test-password'}).status_code==200
    assert warehouse.get('/api/state').status_code==401
    login(warehouse,'almacen','another-test-password')
