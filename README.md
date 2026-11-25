# almacen — TintaStock · Gráfica Ali

Sistema de almacén para imprentas gráficas con interfaz CMYK, escáner y etiquetas. **Versión 0.3: backend Python con FastAPI, SQLAlchemy y SQLite**; frontend HTML, CSS, JavaScript y GSAP. La base de datos ahora se comparte entre todos los equipos conectados al mismo servidor. El proyecto del taller `grafica_2` permanece independiente y no se modifica.

## Ejecutar el sistema real (Python)

Requisitos: Python 3.10 o superior, Git. No se necesita Node.js para arrancar el servidor Python: los recursos de interfaz vienen preparados en `dist/`.

```bash
git clone https://github.com/JhefersonJk/almacen.git
cd almacen
```

Si ya lo tienes, ejecuta `git pull` en la carpeta del proyecto.

**Windows:** doble clic en `iniciar_almacen.bat` (crea `.venv`, instala dependencias y arranca el servidor). Alternativamente:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn sistema_almacen.main:app --host 127.0.0.1 --port 8001
```

**Linux/macOS:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn sistema_almacen.main:app --host 127.0.0.1 --port 8001
```

Abre **http://127.0.0.1:8001**. La documentación interactiva de la API REST está en **http://127.0.0.1:8001/docs**. El puerto 8001 permite usar al mismo tiempo el taller Gráfica Ali en 8000.

En el primer arranque se crea automáticamente `data/almacen.db`, inicialmente vacía. Para practicar, ve a **Configuración → Restablecer demo**; para usar tus datos, importa una copia JSON exportada en la versión anterior. No se importan automáticamente datos del navegador ni la base del taller. Antes de restaurar, exporta un respaldo del inventario compartido. La base y los archivos de entorno están excluidos de Git.

### Conectar otra computadora o celular

Los equipos de la misma red de confianza pueden compartir datos iniciando Uvicorn con `--host 0.0.0.0 --port 8001`, y abriendo `http://IP_DEL_SERVIDOR:8001` desde cada dispositivo. El equipo servidor debe permanecer encendido; la interfaz consulta cambios cada 10 segundos cuando está visible y no hay un formulario abierto. Una versión obsoleta de los datos no puede sobrescribir nuevas existencias; se pide reabrir el formulario y confirmar de nuevo.

La cámara requiere HTTPS (excepto `localhost` en el propio equipo). Para usar la cámara desde el celular, configura el servidor detrás de un proxy HTTPS con un certificado confiable para el teléfono. En HTTP se puede usar búsqueda manual o un lector de códigos USB/Bluetooth que escriba el texto. Esta versión todavía no tiene autenticación: no expongas el servidor directamente a Internet; habrá que añadir cuentas y roles antes de desplegarlo públicamente con inventario real.

## Funcionalidades

- Dashboard, catálogo, alertas, búsqueda sin tildes y ubicación por estantes.
- Entradas, salidas, devoluciones, ajustes, traslados y mermas: el servidor valida y actualiza inventario e historial en una misma transacción.
- Sobrantes, órdenes de trabajo, proveedores y reportes de consumo; costos en centavos y cantidades hasta tres decimales.
- Lectura de códigos con cámara y búsqueda manual; etiquetas imprimibles Code 128 y QR en tamaños configurables.
- Modos claro y nocturno neón, vista cómoda y clásica, tarjetas móviles y animaciones GSAP que respetan movimiento reducido.
- Exportación CSV y respaldo/restauración JSON.

## Arquitectura

| Archivo | Propósito |
|---|---|
| `sistema_almacen/main.py` | FastAPI, rutas REST y entrega de interfaz |
| `sistema_almacen/database.py` | Motor SQLAlchemy, SQLite independiente |
| `sistema_almacen/models.py` | Tablas de materiales, movimientos, órdenes y proveedores |
| `sistema_almacen/schemas.py` | Validación de contratos de entrada |
| `sistema_almacen/operations.py` | Reglas de negocio y escrituras transaccionales |
| `dist/` | Interfaz, estilos, escáner, etiquetas, GSAP y otros recursos locales |
| `tests/` | Pruebas API y navegador con bases temporales |

`ALMACEN_DATABASE_URL` permite elegir una base SQLite independiente, por ejemplo `sqlite:///./data/almacen-pruebas.db`. No apuntar a la base de Gráfica Ali. Las tablas se crean sin eliminar las existentes. Los cambios de esquema futuros necesitarán migraciones versionadas.

Consulta [la arquitectura y estrategia de integración](docs/arquitectura.md) y [la dirección visual](docs/design.md).

## Pruebas

Con el entorno virtual activo:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_api.py
python -m playwright install chromium
python tests/browser_server.py
```

Para los scripts de navegador, se puede configurar `CHROMIUM_PATH` si se usa Chromium del sistema. Las pruebas usan una base temporal, nunca la real del taller.

## Demostración estática (opcional)

`npm start` conserva el piloto anterior en `http://localhost:8080` con datos locales y sin sincronización, útil para maquetas. El servidor Python de puerto 8001 es el sistema centralizado. La vista web estática publicada en Sites no ejecuta Python ni se conecta a la base local del taller. Para reconstruir las librerías JS: `npm ci && npm run build && npm run check`.

Las librerías JsBarcode, html5-qrcode, qrcode y GSAP se distribuyen según sus licencias en `licenses/`.
