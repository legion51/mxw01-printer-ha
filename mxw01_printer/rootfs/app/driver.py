"""BLE protocol implementation for Lefuxin/MXW01 printers."""
import asyncio

from bleak import BleakClient


class MXW01Driver:
    SERVICE_UUIDS = (
        "0000ae30-0000-1000-8000-00805f9b34fb",
        "0000ae00-0000-1000-8000-00805f9b34fb",
        "0000ff00-0000-1000-8000-00805f9b34fb",
    )
    CTRL_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
    DATA_UUID = "0000ae03-0000-1000-8000-00805f9b34fb"

    def __init__(self) -> None:
        self.client: BleakClient | None = None
        self.ctrl_char = None
        self.data_char = None
        self.address: str | None = None

    @property
    def connected(self) -> bool:
        return bool(self.client and self.client.is_connected and self.ctrl_char and self.data_char)

    async def connect(self, address: str) -> None:
        if self.connected and self.address == address:
            return
        await self.disconnect()
        self.client = BleakClient(address)
        await self.client.connect()
        self.address = address
        await asyncio.sleep(0.6)
        for service_uuid in self.SERVICE_UUIDS:
            service = self.client.services.get_service(service_uuid)
            if not service:
                continue
            ctrl = service.get_characteristic(self.CTRL_UUID)
            data = service.get_characteristic(self.DATA_UUID)
            if ctrl and data:
                self.ctrl_char, self.data_char = ctrl, data
                return
        await self.disconnect()
        raise RuntimeError("MXW01 control characteristics AE01/AE03 were not found")

    @staticmethod
    def _crc(payload: bytes) -> int:
        crc = 0
        for value in payload:
            crc ^= value
            for _ in range(8):
                crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
        return crc

    async def _command(self, command: int, payload: bytes) -> None:
        if not self.client or not self.ctrl_char:
            raise RuntimeError("Printer is not connected")
        packet = bytes((0x22, 0x21, command, 0, len(payload) & 0xFF, len(payload) >> 8, *payload, self._crc(payload), 0xFF))
        await self.client.write_gatt_char(self.ctrl_char, packet, response=False)
        await asyncio.sleep(0.05)

    async def print_image(self, bitmap: bytes, height: int) -> None:
        if not self.connected or not self.client or not self.data_char:
            raise RuntimeError("Printer is not connected")
        await self._command(0xB1, b"\x00")
        await self._command(0xA9, bytes((height & 0xFF, height >> 8, 48, 0)))
        for offset in range(0, len(bitmap), 20):
            await self.client.write_gatt_char(self.data_char, bitmap[offset : offset + 20], response=False)
            if offset % 400 == 0:
                await asyncio.sleep(0.02)
        await self._command(0xAD, b"\x00")
        
    async def get_status(self) -> None:
        """Send the documented A1 status request without printing or feeding paper."""
        if not self.connected:
            raise RuntimeError("Printer is not connected")
        await self._command(0xA1, b"\x00")

    async def disconnect(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        self.client = self.ctrl_char = self.data_char = None
        self.address = None
