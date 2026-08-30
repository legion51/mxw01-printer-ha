"""HTTP bridge used by the Home Assistant custom integration."""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from bleak import BleakScanner
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from .driver import MXW01Driver
from .render import render, to_printer_bytes

SETTINGS_FILE = Path("/data/mxw01_settings.json")
settings = {
    "device_address": os.getenv("MXW01_DEVICE_ADDRESS", "").strip(),
    "device_name": os.getenv("MXW01_DEVICE_NAME", "MXW01").strip(),
}
AUTO_CONNECT = os.getenv("MXW01_AUTO_CONNECT", "true").lower() == "true"
driver = MXW01Driver()
print_lock = asyncio.Lock()


class PrintRequest(BaseModel):
    markdown: str = Field(min_length=1, max_length=12000)
    font_size: int = Field(default=20, ge=10, le=40)
    qr_size: int = Field(default=3, ge=1, le=10)
    image_scale: int = Field(default=100, ge=20, le=200)
    device_address: str | None = None


class SettingsRequest(BaseModel):
    device_address: str = Field(default="", max_length=64)
    device_name: str = Field(default="MXW01", min_length=1, max_length=64)


def _load_settings() -> None:
    if SETTINGS_FILE.is_file():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            settings.update({key: str(saved[key]).strip() for key in settings if key in saved})
        except (OSError, ValueError, TypeError) as error:
            print(f"Unable to load saved printer settings: {error}")


def _save_settings() -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False), encoding="utf-8")


async def _resolve_address(request_address: str | None) -> str:
    if request_address:
        return request_address
    if settings["device_address"]:
        return settings["device_address"]
    devices = await BleakScanner.discover(timeout=8)
    matched = [item for item in devices if item.name and settings["device_name"].lower() in item.name.lower()]
    if not matched:
        raise RuntimeError(f"No Bluetooth device matching '{settings['device_name']}' was found")
    return matched[0].address


@asynccontextmanager
async def lifespan(_: FastAPI):
    _load_settings()
    if AUTO_CONNECT and settings["device_address"]:
        try:
            await driver.connect(settings["device_address"])
        except Exception as error:  # Printer may be switched off at add-on boot.
            print(f"Initial MXW01 connection failed: {error}")
    yield
    await driver.disconnect()


app = FastAPI(title="MXW01 Printer Bridge", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return UI


@app.get("/api/status")
async def status() -> dict:
    return {"connected": driver.connected, "device_address": driver.address or settings["device_address"] or None, "device_name": settings["device_name"]}


@app.get("/api/scan")
async def scan() -> list[dict]:
    devices = await BleakScanner.discover(timeout=8)
    return [{"name": item.name, "address": item.address} for item in devices if item.name and settings["device_name"].lower() in item.name.lower()]


@app.get("/api/settings")
async def get_settings() -> dict:
    return settings


@app.put("/api/settings")
async def put_settings(request: SettingsRequest) -> dict:
    settings.update(request.model_dump())
    _save_settings()
    await driver.disconnect()
    return settings


@app.post("/api/preview")
async def preview(request: PrintRequest) -> Response:
    try:
        image = render(request.markdown, request.font_size, request.qr_size, request.image_scale)
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return Response(buffer.getvalue(), media_type="image/png")
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/print")
async def print_document(request: PrintRequest) -> dict:
    async with print_lock:
        try:
            address = await _resolve_address(request.device_address)
            await driver.connect(address)
            image = render(request.markdown, request.font_size, request.qr_size, request.image_scale)
            await driver.print_image(to_printer_bytes(image), image.height)
            return {"ok": True, "height": image.height, "device_address": address}
        except Exception as error:
            raise HTTPException(status_code=502, detail=str(error)) from error


UI = r'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MXW01 Printer</title><style>
:root{color-scheme:dark;--bg:#101318;--panel:#1b212b;--line:#344155;--blue:#43a7ff;--text:#edf3ff;--muted:#aebbd0}*{box-sizing:border-box}body{margin:0;font:16px system-ui,sans-serif;background:var(--bg);color:var(--text)}main{max-width:1200px;margin:auto;padding:24px}h1{margin:0;font-size:26px}.sub{color:var(--muted);margin:6px 0 22px}.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}label{display:block;margin:12px 0 5px;color:var(--muted);font-size:14px}input,textarea,select,button{font:inherit;border-radius:8px;border:1px solid var(--line)}input,textarea,select{width:100%;padding:10px;background:#111722;color:var(--text)}textarea{min-height:300px;resize:vertical;line-height:1.45}button{padding:10px 14px;background:#27354a;color:var(--text);cursor:pointer}button.primary{background:var(--blue);color:#06101e;border:0;font-weight:700}.row{display:flex;gap:8px;align-items:end}.row>*{flex:1}.row button{flex:0 0 auto}.status{display:inline-block;padding:5px 9px;border-radius:999px;background:#4a2325;color:#ffc7c7;font-size:13px}.status.on{background:#1d4c3b;color:#baf5d3}.buttons{display:flex;gap:10px;margin-top:14px}.buttons button{flex:1}img{display:block;max-width:100%;margin:14px auto;background:#fff;image-rendering:pixelated}.hint{color:var(--muted);font-size:13px;line-height:1.45}@media(max-width:800px){main{padding:14px}.grid{grid-template-columns:1fr}.row{flex-wrap:wrap}}
</style></head><body><main><h1>MXW01 Printer</h1><div class="sub">Печать чеков, QR-кодов и изображений по Bluetooth <span id="state" class="status">проверка…</span></div>
<div class="grid"><section class="card"><h2>Макет печати</h2><textarea id="markdown" placeholder="# Заголовок\n[C]Центрированный текст\n---\n[QR:https://example.org|4]"></textarea><p class="hint">Поддерживается: <code># заголовок</code>, <code>[C] текст</code>, <code>[QR:данные|4]</code>, <code>[IMG:https://…|80]</code>, <code>---</code>.</p><div class="row"><label>Шрифт<input id="font" type="number" min="10" max="40" value="20"></label><label>QR<input id="qr" type="number" min="1" max="10" value="3"></label><label>Масштаб картинки<input id="scale" type="number" min="20" max="200" value="100"></label></div><div class="buttons"><button onclick="preview()">Предпросмотр</button><button class="primary" onclick="printDoc()">Напечатать</button></div><p id="message" class="hint"></p></section>
<section class="card"><h2>Принтер</h2><label>Имя при поиске<input id="name" value="MXW01"></label><div class="row"><label>Bluetooth-адрес<select id="address"><option value="">Выберите через поиск</option></select></label><button onclick="scan()">Найти</button></div><div class="buttons"><button onclick="save()">Сохранить принтер</button></div><p class="hint">Адрес сохраняется в данных add-on и восстанавливается после перезапуска.</p><h2>Предпросмотр</h2><img id="preview" alt="Здесь появится макет печати"><p class="hint">Всё готово к печати после появления статуса «подключён».</p></section></div></main>
<script>
const $=id=>document.getElementById(id);let settings={};
function payload(){return{markdown:$('markdown').value,font_size:+$('font').value,qr_size:+$('qr').value,image_scale:+$('scale').value}}
async function api(path,opt={}){let r=await fetch('/api/'+path,opt);if(!r.ok){let x=await r.json().catch(()=>({}));throw Error(x.detail||'Ошибка '+r.status)}return r}
async function refresh(){try{let s=await (await api('status')).json();$('state').textContent=s.connected?'подключён':'не подключён';$('state').className='status '+(s.connected?'on':'')}catch(e){$('state').textContent='нет связи'}}
async function load(){settings=await (await api('settings')).json();$('name').value=settings.device_name;let a=$('address');if(settings.device_address)a.add(new Option(settings.device_address,settings.device_address,true,true));refresh()}
async function scan(){try{$('message').textContent='Ищу принтеры…';let d=await (await api('scan')).json(),a=$('address');a.innerHTML='<option value="">Выберите через поиск</option>';d.forEach(x=>a.add(new Option(x.name+' — '+x.address,x.address)));$('message').textContent=d.length?'Выберите найденный принтер.':'MXW01 не найден. Проверьте питание и Bluetooth.'}catch(e){$('message').textContent=e.message}}
async function save(){try{await api('settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_address:$('address').value,device_name:$('name').value})});$('message').textContent='Настройки сохранены.';refresh()}catch(e){$('message').textContent=e.message}}
async function preview(){try{$('message').textContent='Создаю предпросмотр…';let r=await api('preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});$('preview').src=URL.createObjectURL(await r.blob());$('message').textContent='Готово.'}catch(e){$('message').textContent=e.message}}
async function printDoc(){try{$('message').textContent='Отправляю на принтер…';let r=await api('print',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});let x=await r.json();$('message').textContent='Напечатано: '+x.height+' строк растра.';refresh()}catch(e){$('message').textContent='Печать не выполнена: '+e.message;refresh()}}
load();setInterval(refresh,5000);
</script></body></html>'''
