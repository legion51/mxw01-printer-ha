"""Render the supported MXW01 markup to a 384-pixel monochrome bitmap."""
from io import BytesIO
import re
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode

WIDTH = 384
FONT_PATH = "/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf"


def _image_from_url(url: str) -> Image.Image:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http(s) image URLs are accepted")
    request = Request(url, headers={"User-Agent": "Home-Assistant-MXW01/0.1"})
    with urlopen(request, timeout=15) as response:
        data = response.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("Image exceeds 10 MB")
    return Image.open(BytesIO(data))


def _bitmap_bytes(image: Image.Image) -> bytes:
    pixels = image.load()
    result = bytearray()
    for y in range(image.height):
        row = bytearray(WIDTH // 8)
        for x in range(WIDTH):
            if pixels[x, y] == 0:
                row[x // 8] |= 1 << (x % 8)
        result.extend(row)
    return bytes(result)


def render(markdown: str, font_size: int = 20, qr_size: int = 3, image_scale: int = 100) -> Image.Image:
    if not markdown.strip():
        raise ValueError("Nothing to print")
    if not 10 <= font_size <= 40 or not 1 <= qr_size <= 10 or not 20 <= image_scale <= 200:
        raise ValueError("Rendering options are outside allowed limits")
    normal = ImageFont.truetype(FONT_PATH, font_size)
    bold = ImageFont.truetype(FONT_PATH, round(font_size * 1.25))
    rows: list[tuple[str, object]] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        tag = re.fullmatch(r"\[(IMG|QR):(.+?)\]", line)
        if tag:
            kind, content = tag.groups()
            value, _, size = content.rpartition("|")
            value = value if size else content
            scale = int(size) if size else (qr_size if kind == "QR" else image_scale)
            rows.append((kind, (value.strip(), scale)))
        elif line in ("---", "==="):
            rows.append(("line", line))
        elif line:
            centered = line.startswith("[C]")
            line = line.removeprefix("[C]").strip()
            heading = line.startswith("# ")
            rows.append(("text", (line[2:] if heading else line, centered, bold if heading else normal)))
        else:
            rows.append(("space", font_size))

    prepared: list[tuple[str, object, int]] = []
    total = 20
    for kind, payload in rows:
        if kind == "QR":
            value, size = payload
            code = qrcode.QRCode(version=1, box_size=max(1, min(10, size)), border=2)
            code.add_data(value); code.make(fit=True)
            image = code.make_image(fill_color="black", back_color="white").convert("1")
            height = image.height + 10
        elif kind == "IMG":
            value, size = payload
            image = ImageOps.grayscale(_image_from_url(value))
            ratio = min(WIDTH / image.width, 1) * max(20, min(200, size)) / 100
            image = image.resize((max(1, round(image.width * ratio)), max(1, round(image.height * ratio))), Image.Resampling.LANCZOS)
            image = image.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
            height = image.height + 10
        elif kind == "text":
            text, _, font = payload
            box = ImageDraw.Draw(Image.new("1", (1, 1))).textbbox((0, 0), text, font=font)
            height = (box[3] - box[1]) + round(font_size * 0.6)
            image = None
        elif kind == "space":
            image, height = None, payload
        else:
            image, height = None, 12
        prepared.append((kind, (payload, image), height)); total += height
    if total > 65535:
        raise ValueError("Rendered page is too tall")
    canvas = Image.new("1", (WIDTH, total + 20), 1)
    draw, y = ImageDraw.Draw(canvas), 20
    for kind, pair, height in prepared:
        payload, image = pair
        if kind in ("QR", "IMG"):
            canvas.paste(image, ((WIDTH - image.width) // 2, y)); y += height
        elif kind == "text":
            text, centered, font = payload
            x = (WIDTH - draw.textlength(text, font=font)) // 2 if centered else 10
            draw.text((x, y), text, font=font, fill=0); y += height
        elif kind == "line":
            draw.line((5, y + 5, WIDTH - 5, y + 5), fill=0, width=2 if payload == "===" else 1); y += height
        else:
            y += height
    return canvas


def to_printer_bytes(image: Image.Image) -> bytes:
    return _bitmap_bytes(image)
