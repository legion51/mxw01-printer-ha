"""Драйвер принтера MXW01 для Home Assistant."""

import asyncio
import logging
from io import BytesIO
from typing import Optional

from bleak import BleakClient
from PIL import Image, ImageDraw, ImageFont

from .image_manager import ImageManager
from .renderer import TextRenderer

_LOGGER = logging.getLogger(__name__)


class MXW01Printer:
    """Драйвер принтера MXW01."""

    SERVICE_UUIDS = [
        "0000ae30-0000-1000-8000-00805f9b34fb",
        "0000ae00-0000-1000-8000-00805f9b34fb",
        "0000ff00-0000-1000-8000-00805f9b34fb",
    ]
    CTRL_CHAR_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
    DATA_CHAR_UUID = "0000ae03-0000-1000-8000-00805f9b34fb"

    def __init__(self, hass, address: str, name: str = "MXW01 Printer"):
        """Инициализация."""
        self.hass = hass
        self.address = address
        self.name = name
        self.client: Optional[BleakClient] = None
        self.ctrl_char = None
        self.data_char = None
        self.is_connected = False
        self._connect_lock = asyncio.Lock()
        self._renderer = TextRenderer()

    async def async_connect(self) -> bool:
        """Подключение к принтеру."""
        async with self._connect_lock:
            if self.is_connected:
                return True

            try:
                self.client = BleakClient(self.address)
                await self.client.connect()
                await asyncio.sleep(0.6)

                # Поиск сервисов
                for svc_uuid in self.SERVICE_UUIDS:
                    try:
                        service = self.client.services.get_service(svc_uuid)
                        if not service:
                            continue
                        
                        ctrl = service.get_characteristic(self.CTRL_CHAR_UUID)
                        data = service.get_characteristic(self.DATA_CHAR_UUID)
                        
                        if ctrl and data:
                            self.ctrl_char = ctrl
                            self.data_char = data
                            self.is_connected = True
                            _LOGGER.info("Подключен к %s", self.address)
                            return True
                    except Exception as e:
                        _LOGGER.debug("Сервис %s не найден: %s", svc_uuid, e)

                raise Exception("Каналы управления не найдены")

            except Exception as e:
                _LOGGER.error("Ошибка подключения: %s", e)
                self.is_connected = False
                raise

    async def async_disconnect(self) -> None:
        """Отключение от принтера."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        self.is_connected = False
        self.client = None

    @staticmethod
    def _crc(data: bytes) -> int:
        """Вычисление CRC."""
        c = 0
        for b in data:
            c ^= b
            for _ in range(8):
                if c & 0x80:
                    c = ((c << 1) ^ 0x07) & 0xFF
                else:
                    c = (c << 1) & 0xFF
        return c

    async def _send_command(self, cmd_id: int, payload: bytes) -> None:
        """Отправка команды."""
        if not self.is_connected or not self.client:
            raise Exception("Принтер не подключен")

        pkt = bytes([
            0x22, 0x21, cmd_id, 0x00,
            len(payload) & 0xFF, (len(payload) >> 8) & 0xFF,
            *payload,
            self._crc(payload),
            0xFF
        ])
        
        await self.client.write_gatt_char(self.ctrl_char, pkt, response=False)
        await asyncio.sleep(0.05)

    async def async_print_image_data(self, image_data: bytes, height: int) -> None:
        """Печать изображения."""
        if not self.is_connected:
            raise Exception("Принтер не подключен")

        # Инициализация
        await self._send_command(0xB1, b"\x00")
        await self._send_command(
            0xA9,
            bytes([height & 0xFF, (height >> 8) & 0xFF, 48, 0])
        )

        # Отправка данных
        for i in range(0, len(image_data), 20):
            chunk = image_data[i:i+20]
            await self.client.write_gatt_char(self.data_char, chunk, response=False)
            if i % 400 == 0:
                await asyncio.sleep(0.02)

        # Завершение
        await self._send_command(0xAD, b"\x00")

    async def async_print_text(self, text: str, font_size: int = 20, align: str = "left") -> None:
        """Печать текста."""
        # Генерация изображения
        img = self._renderer.render_text(text, font_size, align)
        
        # Конвертация в байты
        printer_bytes = ImageManager.to_printer_bytes(img)
        
        await self.async_print_image_data(printer_bytes, img.height)

    async def async_print_image(
        self,
        image_url: str,
        width: int = 384,
        brightness: int = 0,
        contrast: float = 1.0,
        dither: str = "floyd",
        invert: bool = False,
    ) -> None:
        """Печать изображения по URL."""
        # Загрузка и обработка
        img = ImageManager.process_image(
            image_url,
            width=width,
            brightness=brightness,
            contrast=contrast,
            dither=dither,
            invert=invert,
        )
        
        printer_bytes = ImageManager.to_printer_bytes(img)
        await self.async_print_image_data(printer_bytes, img.height)

    async def async_print_qr(self, data: str, box_size: int = 3, border: int = 2) -> None:
        """Печать QR-кода."""
        import qrcode
        
        qr = qrcode.QRCode(version=1, box_size=box_size, border=border)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white").convert("1")
        img = img.point(lambda x: 1 - x)  # Инверсия
        
        # Масштабирование до 384 пикселей
        if img.width < 384:
            scale = 384 / img.width
            new_w = 384
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.Resampling.NEAREST)
        
        printer_bytes = ImageManager.to_printer_bytes(img)
        await self.async_print_image_data(printer_bytes, img.height)