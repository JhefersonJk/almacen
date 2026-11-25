"""SQLite temporal: ningún dato del taller se abre o modifica."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sistema_almacen.main import create_app


@pytest.fixture()
def client(tmp_path):
    with TestClient(create_app(f'sqlite:///{tmp_path / "test.db"}')) as c:
        yield c


def write(c,path,data,revision=None,method='POST'):
    if revision is None: revision=c.get('/api/state').json()['revision']
    return c.request(method,path,json=data,headers={'X-Inventory-Revision':str(revision)})


def product(c,**kw):
    return write(c,'/api/products',dict(code='VIN-001',name='Vinilo',category='Vinilo',unit='m',stock=10,min=1,cost=12.34,location='B-01',**kw))


def test_persistence_and_same_origin(tmp_path):
    url=f'sqlite:///{tmp_path / "persistent.db"}'
    with TestClient(create_app(url)) as c:
        assert c.get('/api/state').json()['products']==[]
        assert 'name="tintastock-mode" content="server"' in c.get('/').text
        assert c.get('/api/state').headers['cache-control']=='no-store'
        assert c.get('/api/state?since=0').status_code==204
        assert product(c).status_code==201
    with TestClient(create_app(url)) as c:
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
