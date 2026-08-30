"""Рендеринг текста для печати."""

from PIL import Image, ImageDraw, ImageFont


class TextRenderer:
    """Рендеринг текста."""

    def __init__(self, width: int = 384):
        """Инициализация."""
        self.width = width
        self._init_fonts()

    def _init_fonts(self) -> None:
        """Инициализация шрифтов."""
        self.font_regular = ImageFont.load_default()
        self.font_bold = ImageFont.load_default()

    def render_text(self, text: str, font_size: int = 20, align: str = "left") -> Image.Image:
        """Рендеринг текста в изображение."""
        lines = text.split("\n")
        line_height = font_size + 4
        height = max(50, len(lines) * line_height + 40)
        
        img = Image.new("1", (self.width, height), 1)
        draw = ImageDraw.Draw(img)
        
        y = 10
        for line in lines:
            if not line.strip():
                y += line_height
                continue
            
            # Разбивка длинных строк
            words = line.split()
            current_line = ""
            x = 10
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=self.font_regular)
                text_width = bbox[2] - bbox[0]
                
                if text_width > self.width - 20 and current_line:
                    # Рисуем текущую строку
                    self._draw_line(draw, current_line, x, y, font_size, align)
                    y += line_height
                    current_line = word
                else:
                    current_line = test_line
            
            if current_line:
                self._draw_line(draw, current_line, x, y, font_size, align)
                y += line_height
        
        # Обрезка
        img = img.crop((0, 0, self.width, y + 10))
        return img

    def _draw_line(
        self,
        draw: ImageDraw.Draw,
        text: str,
        x: int,
        y: int,
        font_size: int,
        align: str
    ) -> None:
        """Рисование строки."""
        bbox = draw.textbbox((0, 0), text, font=self.font_regular)
        text_width = bbox[2] - bbox[0]
        
        if align == "center":
            x = (self.width - text_width) // 2
        elif align == "right":
            x = self.width - text_width - 10
        
        draw.text((x, y), text, fill=0, font=self.font_regular)