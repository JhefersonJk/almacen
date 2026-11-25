"""Local browser tests: python -m pip install playwright && python tests/browser-smoke.py."""
from pathlib import Path
import os, subprocess, time, urllib.request
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
port = 18081
server = subprocess.Popen(['node','scripts/serve.mjs'], cwd=ROOT, env={**os.environ,'PORT':str(port)}, stdout=subprocess.DEVNULL)
base = f'http://127.0.0.1:{port}'
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(base, timeout=1).close(); break
        except OSError: time.sleep(.1)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None), headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1440,'height':960}, reduced_motion='reduce')
        errors=[]
        page.on('pageerror', lambda e:errors.append(str(e)))
        page.goto(base); page.get_by_role('heading',name='Mesa de almacén').wait_for()
        assert page.locator('html').get_attribute('data-layout')=='comfort'
        assert page.locator('html').get_attribute('data-theme')=='light'
        assert page.locator('html').get_attribute('data-density')=='compact'
        assert page.locator('#inventory-table .inventory-table tbody tr').count()==10
        assert page.locator('#inventory-table').bounding_box()['y']<460
        page.locator('[data-action=toggle-stock-view]').click();assert page.locator('.stock-column').count()==3
        page.locator('[data-action=toggle-stock-view]').click();assert page.locator('.inventory-table tbody tr').count()==10
        page.locator('.stock-chip[data-status="Stock bajo"]').click();assert page.locator('.inventory-table tbody tr').count()==2
        page.locator('[data-action=clear-filters]').click();assert page.locator('.inventory-table tbody tr').count()==10
        page.locator('#density-toggle').select_option('detailed');assert page.locator('html').get_attribute('data-density')=='detailed'
        page.reload();assert page.locator('html').get_attribute('data-density')=='detailed'
        page.locator('#density-toggle').select_option('compact')
        page.screenshot(path='/tmp/tintastock-workbench-light.png')
        page.locator('#theme-toggle').click(); assert page.locator('html').get_attribute('data-theme')=='dark'
        page.wait_for_timeout(180)
        page.screenshot(path='/tmp/tintastock-workbench-dark.png')
        page.reload(); assert page.locator('html').get_attribute('data-theme')=='dark'
        page.locator('#layout-toggle').click(); assert page.locator('html').get_attribute('data-layout')=='classic'
        page.reload(); assert page.locator('html').get_attribute('data-layout')=='classic'
        page.locator('#layout-toggle').click(); page.locator('#theme-toggle').click()
        page.locator('[data-action="new-product"]').first.click(); assert page.locator('#close').evaluate('(el)=>el===document.activeElement')
        page.locator('#product-form input[name=name]').fill('Papel prueba diseño')
        page.locator('#product-form input[name=stock]').fill('25'); page.locator('#product-form button[type=submit]').click()
        assert page.locator('.inventory-table').get_by_text('Papel prueba diseño').count()==1
        page.locator('#search').fill('couche'); assert page.locator('.inventory-table').get_by_text('Papel couché 150 g').count()==1
        page.locator('[data-action="clear-filters"]').click(); assert page.locator('.inventory-table tbody tr').count()==11
        page.locator('#search').fill('VIN-001');page.locator('#search').press('Enter');assert page.locator('#modal-title').inner_text()=='Ficha del material';page.keyboard.press('Escape');page.locator('[data-action=clear-filters]').click()
        page.locator('.top-scan').click(); page.locator('#scan-form input').fill('VIN-001'); page.locator('#scan-form button').click()
        assert 'Vinilo blanco brillante' in page.locator('#modal-body').inner_text()
        page.locator('#modal-body [data-action=move]').click(); page.locator('#movement-form select[name=type]').select_option('salida'); page.locator('#movement-form input[name=qty]').fill('2.5'); page.locator('#movement-form button[type=submit]').click()
        assert page.evaluate("JSON.parse(localStorage.getItem('tintastock-v1')).products.find(p=>p.code==='VIN-001').stock")==30
        page.locator('[data-go=labels]').click(); page.locator('.label-check').first.check(); assert page.locator('#label-preview svg rect').count()>0
        page.locator('#label-type').select_option('qr'); assert page.locator('#label-preview canvas').count()==1
        page.locator('#nav-more').click(); page.locator('[data-go=reports]').click(); page.get_by_role('heading',name='Reportes y costos').wait_for()
        for width,height in [(375,812),(768,1024),(1024,768),(1440,900),(812,375)]:
            page.set_viewport_size({'width':width,'height':height})
            for screen in ['home','inventory','labels','moves','orders','locations','suppliers','reports','settings']:
                page.evaluate(f'go({screen!r})')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (width,screen,page.evaluate('document.documentElement.scrollWidth'))
            page.evaluate("go('home')");page.locator('[data-action=toggle-stock-view]').click();assert page.locator('.stock-column').count()==3;assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (width,'cards');page.locator('[data-action=toggle-stock-view]').click()
            if width==375:
                page.evaluate("go('inventory')")
                page.screenshot(path='/tmp/tintastock-workbench-mobile.png')
                page.locator('#menu').click(); assert page.locator('#menu').get_attribute('aria-expanded')=='true'; page.locator('[data-go=home]').last.click(); assert page.locator('#menu').get_attribute('aria-expanded')=='false'
        assert not errors, errors
        print('OK: light/dark persistence, comfortable/classic, create, accent-insensitive search, scanner manual, movement, barcode/QR, navigation, 50 responsive page checks and no JS errors')
        browser.close()
finally:
    server.terminate(); server.wait(timeout=5)
