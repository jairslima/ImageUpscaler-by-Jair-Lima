"""Gera icon.ico para o Image Upscaler by Jair Lima."""
from PIL import Image, ImageDraw


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    r = max(2, size // 7)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                            fill=(30, 30, 46, 255))

    cx = size / 2
    aw = size * 0.30   # meia-largura da cabeça da seta
    sw = size * 0.13   # meia-largura do corpo
    top    = size * 0.13
    neck   = size * 0.50
    bottom = size * 0.83
    accent = (137, 180, 250, 255)

    draw.polygon([
        (cx,        top),
        (cx - aw,   neck),
        (cx - sw,   neck),
        (cx - sw,   bottom),
        (cx + sw,   bottom),
        (cx + sw,   neck),
        (cx + aw,   neck),
    ], fill=accent)

    # Pequena estrela de brilho (canto sup. direito)
    if size >= 32:
        sx, sy, sr = size * 0.78, size * 0.22, size * 0.07
        for angle in (0, 90, 45, 135):
            import math
            a = math.radians(angle)
            draw.line([
                (sx - math.cos(a) * sr, sy - math.sin(a) * sr),
                (sx + math.cos(a) * sr, sy + math.sin(a) * sr),
            ], fill=accent, width=max(1, int(size * 0.025)))

    return img


def create_icon(path="icon.ico"):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [make_frame(s) for s in sizes]
    frames[0].save(
        path, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Ícone gerado: {path}")


if __name__ == "__main__":
    create_icon()
