# almacen — TintaStock · Gráfica Ali

Sistema de almacén para imprentas gráficas con interfaz CMYK, escáner y etiquetas. **Versión 0.4: backend Python con FastAPI, SQLAlchemy y SQLite, inicio de sesión y roles**; frontend HTML, CSS, JavaScript y GSAP. La base de datos ahora se comparte entre todos los equipos conectados al mismo servidor. El proyecto del taller `grafica_2` permanece independiente y no se modifica.

## Ejecutar el sistema real (Python)

Requisitos: Python 3.10 o superior, Git. No se necesita Node.js para arrancar el servidor Python: los recursos de interfaz vienen preparados en `dist/`.

```bash
git clone https://github.com/JhefersonJk/almacen.git
cd almacen
```

Si ya lo tienes, ejecuta `git pull` en la carpeta del proyecto.

**Windows:** doble clic en `iniciar_almacen.bat` (crea `.venv`, instala dependencias, solicita crear la primera cuenta de administración si aún no existe y arranca el servidor). Alternativamente:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m sistema_almacen.users --ensure
.venv\Scripts\python.exe -m uvicorn sistema_almacen.main:app --host 127.0.0.1 --port 8001
```

**Linux/macOS:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m sistema_almacen.users --ensure
.venv/bin/python -m uvicorn sistema_almacen.main:app --host 127.0.0.1 --port 8001
```

Abre **http://127.0.0.1:8001**. La documentación interactiva de la API REST está en **http://127.0.0.1:8001/docs**. El puerto 8001 permite usar al mismo tiempo el taller Gráfica Ali en 8000.

En el primer arranque se crea automáticamente `data/almacen.db`, inicialmente vacía. Inicia sesión con la cuenta administrativa creada en el servidor. En el menú **Más → Usuarios**, crea las cuentas del equipo. No hay cuentas ni contraseñas predeterminadas. Para practicar, ve a **Configuración → Restablecer demo**; para usar tus datos, importa una copia JSON exportada en la versión anterior. No se importan automáticamente datos del navegador ni la base del taller. Antes de restaurar, exporta un respaldo del inventario compartido. La base y los archivos de entorno están excluidos de Git.

### Conectar otra computadora o celular

Los equipos de la misma red de confianza pueden compartir datos iniciando Uvicorn con `--host 0.0.0.0 --port 8001`, y abriendo `http://IP_DEL_SERVIDOR:8001` desde cada dispositivo. El equipo servidor debe permanecer encendido; la interfaz consulta cambios cada 10 segundos cuando está visible y no hay un formulario abierto. Una versión obsoleta de los datos no puede sobrescribir nuevas existencias; se pide reabrir el formulario y confirmar de nuevo.

La cámara requiere HTTPS (excepto `localhost` en el propio equipo). Para usar la cámara desde el celular, configura el servidor detrás de un proxy HTTPS con un certificado confiable para el teléfono. En HTTP se puede usar búsqueda manual o un lector de códigos USB/Bluetooth que escriba el texto. Esta versión exige iniciar sesión. Usa HTTPS con un certificado confiable para proteger credenciales y datos cuando se conecten otros dispositivos. Para acceso desde Internet todavía se necesita una instalación HTTPS segura y gestión de infraestructura; no publiques directamente el puerto de desarrollo.

## Funcionalidades

- Dashboard, catálogo, alertas, búsqueda sin tildes y ubicación por estantes.
- Entradas, salidas, devoluciones, ajustes y traslados: el servidor valida y actualiza inventario e historial en una misma transacción.
- Sobrantes, órdenes de trabajo, proveedores y reportes de consumo; costos en centavos y cantidades hasta tres decimales.
- Lectura de códigos con cámara y búsqueda manual; etiquetas imprimibles Code 128 y QR en tamaños configurables.
- Modos claro y nocturno neón, vista cómoda y clásica, tarjetas móviles y animaciones GSAP que respetan movimiento reducido.
- Exportación CSV y respaldo/restauración JSON.

## Perfiles y permisos

| Rol | Acceso principal |
|---|---|
| **Almacén** | Alta y edición de materiales, entradas, salidas, devoluciones, traslados y ajustes, etiquetas y proveedores. |
| **Producción** | Consultar material y órdenes, escanear, retirar o devolver material. |
| **Gerencia** | Consultar inventario, movimientos, órdenes, costos y reportes, exportar CSV. Sin cambios de stock. |
| **Administración** | Acceso completo: usuarios, roles, contraseñas, costos, órdenes, inventario y respaldos. |

La identidad del responsable de los movimientos se toma de la sesión, no de un campo editable. Los costos se ocultan a almacén y producción; almacén puede editar existencias y descripción sin sustituir los costos asignados por Administración. Se puede registrar una diferencia como **Ajuste** con nota opcional; el desperdicio no es un paso obligatorio. Los registros históricos de mermas se conservan.

El gestor permite crear/editar/desactivar cuentas; cambiar rol, contraseña o estado revoca las sesiones asociadas. Cada usuario puede cambiar su propia contraseña. Siempre se conserva al menos una cuenta de administración activa. El respaldo JSON de inventario no contiene cuentas, contraseñas ni sesiones.

## Arquitectura

| Archivo | Propósito |
|---|---|
| `sistema_almacen/main.py` | FastAPI, rutas REST y entrega de interfaz |
| `sistema_almacen/database.py` | Motor SQLAlchemy, SQLite independiente |
| `sistema_almacen/models.py` | Tablas de materiales, movimientos, órdenes y proveedores |
| `sistema_almacen/schemas.py` | Validación de contratos de entrada |
| `sistema_almacen/operations.py` | Reglas de negocio y escrituras transaccionales |
| `sistema_almacen/auth.py`, `users.py` | Permisos, cuentas, sesiones y configuración inicial |
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

`npm start` conserva la demostración estática sin inicio de sesión real en `http://localhost:8080` con datos locales y sin sincronización, útil para maquetas. El servidor Python de puerto 8001 es el sistema centralizado. La vista web estática publicada en Sites no ejecuta Python ni se conecta a la base local del taller. Para reconstruir las librerías JS: `npm ci && npm run build && npm run check`.

Las librerías JsBarcode, html5-qrcode, qrcode y GSAP se distribuyen según sus licencias en `licenses/`.
