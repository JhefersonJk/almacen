# Dirección visual de TintaStock · Gráfica Ali

La versión 0.2 adapta el lenguaje visual del proyecto del taller, sin importar su base de datos ni alterar los registros locales del almacén. Referencia: [Gráfica Ali](https://github.com/JhefersonJk/grafica_2/tree/main/sistema_grafica_neon/repo), documento `docs/design.md` y estilos `style.css`, `theme.css`, `comfort.css`.

## Sistema visual

- **Claro, predeterminado:** cian `#00b9d6`, magenta `#dc2378`, amarillo `#f7d633`, negro `#18191b`, papel `#f7f7f3`.
- **Nocturno neón:** cian `#00e5ff`, magenta `#ff2e97`, amarillo `#ffe14d`, fondo `#07070f`, superficie `#10111d`. Los textos semánticos tienen variantes de contraste.
- Las cuatro tintas identifican la marca y estructuran los indicadores. Los estados siempre incluyen texto, no dependen solo del color. Las etiquetas impresas conservan tinta negra sobre blanco en ambos temas.
- Tipografía de sistema, iconos SVG de trazo y cifras tabulares. La vista cómoda utiliza navegación superior y un menú para módulos menos frecuentes; la clásica recupera la barra lateral. En celular el menú lateral y las tarjetas de inventario conservan los controles, sin exigir desplazamiento horizontal para consultar material.
- Los ajustes de tema y vista se guardan en `tintastock-theme` y `tintastock-layout`, separados del almacenamiento de inventario `tintastock-v1`.

## Skills consultadas

- [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): SKILL.md, búsqueda de sistema visual `inventory warehouse data dashboard`, búsqueda dirigida `data dense dashboard` (confirmó dashboard de datos), y búsqueda de foco y espaciado táctil. Se adoptaron la retícula de indicadores, densidad legible, estados, filtros, botones táctiles y foco visible. Se conservó la paleta CMYK del taller en lugar de la paleta industrial genérica sugerida.
- [GSAP Skills](https://github.com/greensock/gsap-skills): gsap-core, gsap-timeline y gsap-performance. GSAP local, entradas y gráficos con `transform` y `opacity`, lotes de hasta 12 elementos, sin animaciones infinitas, limpieza al cambiar de pantalla y respeto a movimiento reducido. La interfaz no depende de las animaciones para funcionar.

## Validación

`tests/browser-smoke.py` realiza pruebas de tema y distribución persistentes, búsqueda sin tildes, alta, escaneo manual, salida, generación de Code 128 y QR, navegación y ausencia de desbordamiento horizontal a 375, 768, 1024, 1440 y 812×375 px. Los datos son de prueba aislados. El permiso y lectura con cámara física se comprueban por separado en un teléfono con HTTPS.


## Versión 0.5: mesa de trabajo realmente alineada con Gráfica Ali

Se inició una copia local del proyecto `grafica_2` con SQLite temporal para comparar capturas reales en claro y oscuro. La referencia original muestra una navegación superior con marca de cuatro círculos a la izquierda, indicador activo subrayado, selector de densidad en píldora, aurora CMYK, tarjetas con borde de etapa y mesa directamente debajo de los filtros. El nuevo `workbench.css` aplica estos rasgos al almacén y conserva los tokens y los estilos previos como base. No se modificó el repositorio de origen ni se usaron sus datos.

- La pantalla inicial ahora es **Mesa de almacén** (o Mesa de producción · Materiales). El inventario, búsqueda y operaciones directas están en la primera pantalla. Se eliminó el banner de escaneo y las tarjetas redundantes que separaban la tarea diaria de los indicadores; las alertas y actividad reciente están en paneles laterales de altura natural en escritorio.
- Densidad compacta por defecto, con cómoda y detallada persistentes. El listado combina nombre y SKU, muestra existencias, ubicación y estado, y permite Entrada/Salida o Retirar/Devolver según el rol. Detallada añade mínimo y descripción. La vista Tarjetas agrupa por estados con columnas de estilo del taller; en móvil se apila.
- Filtros progresivos, chips de estado, búsqueda inmediata sin tildes, Ctrl+K, código + Enter. Al escoger una operación de un material se preselecciona el material y tipo, con foco en cantidad. No se pide volver a seleccionarlos.
- Se conservaron API, autenticación, permisos e inventario. Se comprobaron ambos temas mediante capturas, 50 comprobaciones de distribución de lista, pantallas y tarjetas en cinco tamaños de pantalla, y el recorrido con dos usuarios del backend Python.
