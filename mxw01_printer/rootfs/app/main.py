"""HTTP bridge used by the Home Assistant custom integration."""
import asyncio
import os
from contextlib import asynccontextmanager

from bleak import BleakScanner
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .driver import MXW01Driver
from .render import render, to_printer_bytes

DEVICE_ADDRESS = os.getenv("MXW01_DEVICE_ADDRESS", "").strip()
DEVICE_NAME = os.getenv("MXW01_DEVICE_NAME", "MXW01").strip()
AUTO_CONNECT = os.getenv("MXW01_AUTO_CONNECT", "true").lower() == "true"
driver = MXW01Driver()
print_lock = asyncio.Lock()


class PrintRequest(BaseModel):
    markdown: str = Field(min_length=1, max_length=12000)
    font_size: int = Field(default=20, ge=10, le=40)
    qr_size: int = Field(default=3, ge=1, le=10)
    image_scale: int = Field(default=100, ge=20, le=200)
    device_address: str | None = None


async def _resolve_address(request_address: str | None) -> str:
    if request_address:
        return request_address
    if DEVICE_ADDRESS:
        return DEVICE_ADDRESS
    devices = await BleakScanner.discover(timeout=8)
    matched = [item for item in devices if item.name and DEVICE_NAME.lower() in item.name.lower()]
    if not matched:
        raise RuntimeError(f"No Bluetooth device matching '{DEVICE_NAME}' was found")
    return matched[0].address


@asynccontextmanager
async def lifespan(_: FastAPI):
    if AUTO_CONNECT and DEVICE_ADDRESS:
        try:
            await driver.connect(DEVICE_ADDRESS)
        except Exception as error:  # Printer may be switched off at add-on boot.
            print(f"Initial MXW01 connection failed: {error}")
    yield
    await driver.disconnect()


app = FastAPI(title="MXW01 Printer Bridge", lifespan=lifespan)


@app.get("/")
async def index() -> dict:
    return {"name": "MXW01 Printer Bridge", "connected": driver.connected}


@app.get("/status")
async def status() -> dict:
    return {"connected": driver.connected, "device_address": driver.address or DEVICE_ADDRESS or None, "device_name": DEVICE_NAME}


@app.get("/scan")
async def scan() -> list[dict]:
    devices = await BleakScanner.discover(timeout=8)
    return [{"name": item.name, "address": item.address} for item in devices if item.name and DEVICE_NAME.lower() in item.name.lower()]


@app.post("/print")
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
