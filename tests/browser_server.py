"""Prueba end-to-end con dos navegadores independientes y una SQLite temporal."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sistema_almacen.database import configure,Base
from sistema_almacen import auth,models
PORT=18082
BASE=f'http://127.0.0.1:{PORT}'
with TemporaryDirectory() as temp:
    dburl=f'sqlite:///{Path(temp)/"browser.db"}'
    engine,S=configure(dburl);Base.metadata.create_all(engine)
    with S() as db: auth.create_user(db,auth.UserInput(username='admin',displayName='Administrador',role='administracion',password='test-password-123'),first=True);db.commit()
    engine.dispose()
    env={**os.environ,'ALMACEN_DATABASE_URL':dburl}
    server=subprocess.Popen([sys.executable,'-m','uvicorn','sistema_almacen.main:app','--host','127.0.0.1','--port',str(PORT)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try: urllib.request.urlopen(BASE+'/api/health',timeout=1).close();break
            except OSError: time.sleep(.1)
        else: raise RuntimeError('No inició FastAPI')
        with sync_playwright() as p:
            b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),headless=True,args=['--no-sandbox'])
            one=b.new_page(viewport={'width':1440,'height':900},reduced_motion='reduce');two=b.new_page(viewport={'width':375,'height':812},reduced_motion='reduce');errors=[]
            for page in (one,two):
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(BASE);page.locator('#login-form input[name=username]').fill('admin');page.locator('#login-form input[name=password]').fill('test-password-123');page.locator('#login-form button').click();page.wait_for_function("document.querySelector('#connection-status').dataset.connection==='online'")
                assert page.evaluate('serverMode');assert page.evaluate('data.products.length')==0
            one.locator('[data-action=new-product]').click();one.locator('#product-form input[name=name]').fill('Vinilo compartido');one.locator('#product-form input[name=code]').fill('VIN-TEST');one.locator('#product-form input[name=stock]').fill('10');one.locator('#product-form input[name=cost]').fill('12.50');one.locator('#product-form button[type=submit]').click();one.locator('.inventory-table').get_by_text('Vinilo compartido').wait_for()
            # Polling real: no cookie, session or localStorage data is shared between browser contexts.
            two.wait_for_function("data.products.some(x=>x.code==='VIN-TEST')",timeout=18000)
            for page in (one,two):
                page.locator('.top-scan').click();page.locator('#scan-form input').fill('VIN-TEST');page.locator('#scan-form button').click();page.locator('#modal-body [data-action=move]').click();page.locator('#movement-form select[name=type]').select_option('salida');page.locator('#movement-form input[name=qty]').fill('7')
            one.locator('#movement-form button[type=submit]').click();one.wait_for_function('data.products[0].stock===3')
            two.locator('#movement-form button[type=submit]').click();two.wait_for_function("document.querySelector('#toast').textContent.includes('inventario cambió')")
            two.wait_for_function('data.products[0].stock===3');two.keyboard.press('Escape');two.evaluate("go('inventory')");assert two.locator('.inventory-table tbody tr').get_by_text('3 unidades').count()==1
            # A stale request did not create an extra movement.
            assert one.request.get(BASE+'/api/state').json()['movements'].__len__()==2
            two.locator('.top-scan').click();two.locator('#scan-form input').fill('VIN-TEST');two.locator('#scan-form button').click();two.locator('#modal-body [data-action=one-label]').click();assert two.locator('#label-preview svg rect').count()>0;two.locator('#label-type').select_option('qr');assert two.locator('#label-preview canvas').count()==1
            assert one.evaluate("localStorage.getItem('tintastock-v1')") is None
            assert two.evaluate("localStorage.getItem('tintastock-v1')") is None
            two.reload();two.wait_for_function('data.products.length===1');assert two.evaluate('data.products[0].stock')==3
            # Administration creates a real production user via the interface.
            one.locator('#nav-more').click();one.locator('[data-go=users]').click();one.locator('[data-action=new-user]').click();one.locator('#user-form input[name=displayName]').fill('Operario de producción');one.locator('#user-form input[name=username]').fill('produccion1');one.locator('#user-form select[name=role]').select_option('produccion');one.locator('#user-form input[name=password]').fill('test-password-123');one.locator('#user-form button[type=submit]').click();one.locator('#users-list').get_by_text('produccion1').wait_for()
            two.locator('#account summary').click();two.locator('[data-action=logout]').click();two.locator('#login-form').wait_for();two.locator('#login-form input[name=username]').fill('produccion1');two.locator('#login-form input[name=password]').fill('test-password-123');two.locator('#login-form button').click();two.wait_for_function("currentUser?.role==='produccion' && data.products.length===1")
            assert two.locator('[data-go=users]').count()==0 and two.locator('[data-go=reports]').count()==0
            assert two.get_by_role('button',name='Retirar material').is_visible()
            assert two.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert two.locator('#search').is_visible()
            two.locator('.top-scan').click();two.locator('#scan-form input').fill('VIN-TEST');two.locator('#scan-form button').click();two.locator('#modal-body [data-action=exit]').click();assert two.locator('#movement-form input[name=type]').input_value()=='salida';assert two.locator('#movement-form select[name=productId]').count()==0;assert two.locator('#movement-form input[name=qty]').evaluate('(el)=>el===document.activeElement');two.locator('#movement-form input[name=qty]').fill('1');two.locator('#movement-form button[type=submit]').click();two.wait_for_function('data.products[0].stock===2');assert two.evaluate('data.movements[0].operator')=='produccion1'
            assert not errors,errors
            print('OK: two isolated devices, actual 10-second sync, API-backed creation, concurrent stale movement rejected, labels, reload persistence, user manager, logout/login, production-specific view and withdrawal, no localStorage inventory or JS errors')
            b.close()
    finally:
        server.terminate();server.wait(timeout=5)
