import { copyFile, mkdir } from 'node:fs/promises';
import { build } from 'esbuild';
await mkdir('dist/vendor',{recursive:true});
await copyFile('node_modules/jsbarcode/dist/JsBarcode.all.min.js','dist/vendor/barcode.js');
await copyFile('node_modules/html5-qrcode/html5-qrcode.min.js','dist/vendor/scanner.js');
await build({entryPoints:['node_modules/qrcode/lib/browser.js'],bundle:true,minify:true,globalName:'QR',outfile:'dist/vendor/qrcode.js'});
