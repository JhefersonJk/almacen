# almacen — TintaStock

Sistema piloto de gestión de almacén para imprentas gráficas, adaptable a computadora y celular. Interfaz en español y moneda de ejemplo en bolivianos (Bs).

## Funcionalidades

- Panel de indicadores, búsqueda y catálogo de materiales, alertas de existencias.
- Escáner de códigos de barras y QR mediante la cámara; búsqueda manual alternativa.
- Generación de etiquetas Code 128 y QR, selección múltiple, tamaños de impresión y PDF mediante el navegador.
- Entradas, salidas, devoluciones, ajustes, traslados, mermas y registro de sobrantes.
- Órdenes de trabajo, proveedores, ubicaciones, reportes y exportación CSV.
- Copias de seguridad JSON y aplicación web instalable (PWA, con caché local).

## Ejecutar en tu computadora

Necesitas Node.js 20 o superior y Git:

```bash
git clone https://github.com/JhefersonJk/almacen.git
cd almacen
npm start
```

Abre **http://localhost:8080**. No necesitas instalar dependencias para iniciar el piloto porque las librerías del navegador ya están incluidas en `dist/vendor/`.

Para actualizar o reconstruir las librerías de terceros:

```bash
npm ci
npm run build
npm run check
```

## Estructura

| Archivo | Propósito |
|---|---|
| `dist/index.html` | Estructura de la interfaz |
| `dist/style.css` | Diseño, adaptación móvil y estilos de impresión |
| `dist/app.js` | Lógica del inventario, escáner, etiquetas y movimientos |
| `dist/manifest.webmanifest`, `dist/sw.js` | Instalación y caché PWA |
| `dist/vendor/` | Librerías incluidas para escanear y generar códigos |
| `scripts/serve.mjs` | Servidor estático de desarrollo local |
| `scripts/build-vendor.mjs` | Reconstrucción de las librerías |
| `licenses/` | Avisos de licencia de librerías de terceros |

## Prueba de etiquetas y escáner

1. Entra en Inventario y crea un material, o usa el material ficticio `VIN-001`.
2. Ve a Etiquetas y selecciona el material. Elige Code 128 o QR e imprime a escala del 100%.
3. Abre Escáner móvil, activa la cámara y apunta al código. El navegador pedirá permiso.
4. Registra una salida y confirma que disminuyó el stock y se registró el movimiento.

La cámara necesita un contexto seguro: `localhost` en el propio equipo o un sitio alojado por HTTPS. Para probar desde un celular, publica el directorio `dist` en un servidor HTTPS. Una IP local entregada por HTTP normalmente no permite acceder a la cámara.

## Estado y próximos pasos

Esta es una versión de demostración. Los datos se guardan con `localStorage` en cada navegador; no se sincronizan entre dispositivos. Usa las opciones de exportación/importación JSON para trasladar una copia. No es todavía una base de datos multiusuario ni incluye autenticación de negocio.

Siguiente etapa: almacenamiento centralizado, autenticación y roles, trazabilidad por lotes y rollos, reservas, compras y pruebas con cámaras físicas y lectores de producción.

Las librerías JsBarcode, html5-qrcode y qrcode se distribuyen según sus licencias de terceros.
