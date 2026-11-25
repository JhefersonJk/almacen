"""Prueba end-to-end con dos navegadores independientes y una SQLite temporal."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
PORT=18082
BASE=f'http://127.0.0.1:{PORT}'
with TemporaryDirectory() as temp:
    dburl=f'sqlite:///{Path(temp)/"browser.db"}'
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
                page.goto(BASE);page.wait_for_function("document.querySelector('#connection-status').dataset.connection==='online'")
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
            assert not errors,errors
            print('OK: two isolated devices, actual 10-second sync, API-backed creation, concurrent stale movement rejected, labels, reload persistence, no localStorage inventory or JS errors')
            b.close()
    finally:
        server.terminate();server.wait(timeout=5)
