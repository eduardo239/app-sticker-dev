"""
Converte uma imagem para o formato de sticker do WhatsApp:
- WebP com transparência
- 512x512 pixels
- Máximo 100 KB (estático)
"""
import io
from pathlib import Path

from PIL import Image

# Limite de pixels para evitar decompression bomb (imagens maliciosas que explodem em memória)
Image.MAX_IMAGE_PIXELS = 50_000_000  # 50 megapixels

# Requisitos WhatsApp: https://faq.whatsapp.com/4148445205479237
STICKER_SIZE = (512, 512)
MAX_BYTES = 100 * 1024  # 100 KB
WEBP_QUALITY_MIN = 1
WEBP_QUALITY_MAX = 95

# Magic bytes de formatos permitidos (evita processar arquivos que não são imagem)
ALLOWED_IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
    (b"RIFF", "WEBP"),  # WEBP: RIFF....WEBP
)


def image_to_sticker(
    image_source: str | Path | bytes | io.BytesIO,
    *,
    add_transparent_bg: bool = True,
    crop_mode: str = "contain",
) -> bytes:
    """
    Converte uma imagem para bytes de um sticker WebP (512x512, &lt;100KB).

    Args:
        image_source: Caminho do arquivo, bytes ou BytesIO da imagem.
        add_transparent_bg: Se True, trata fundo branco como transparente (útil para logos).
        crop_mode: "contain" (cabe no quadrado, com margem) ou "cover" (preenche, pode cortar).

    Returns:
        Bytes do arquivo WebP.

    Raises:
        ValueError: Se o arquivo não for uma imagem suportada (JPEG, PNG, GIF, WebP).
        PIL.Image.DecompressionBombError: Se a imagem exceder MAX_IMAGE_PIXELS.
    """
    if isinstance(image_source, bytes):
        raw = image_source[:32]
    elif isinstance(image_source, (str, Path)):
        with open(image_source, "rb") as f:
            raw = f.read(32)
    else:
        raw = image_source.read(32) if hasattr(image_source, "read") else b""
        if hasattr(image_source, "seek"):
            image_source.seek(0)

    if raw:
        ok = any(raw.startswith(sig) for sig, _ in ALLOWED_IMAGE_SIGNATURES)
        if not ok and len(raw) >= 12 and raw[:4] == b"RIFF":
            ok = raw[8:12] == b"WEBP"
        if not ok:
            raise ValueError("Formato de imagem não suportado. Use JPEG, PNG, GIF ou WebP.")

    if isinstance(image_source, (str, Path)):
        img = Image.open(image_source).convert("RGBA")
    elif isinstance(image_source, bytes):
        img = Image.open(io.BytesIO(image_source)).convert("RGBA")
    else:
        img = Image.open(image_source).convert("RGBA")

    if add_transparent_bg:
        # Opcional: tornar pixels muito claros transparentes (útil para fundo branco)
        data = img.getdata()
        new_data = []
        for item in data:
            r, g, b, a = item
            if r > 250 and g > 250 and b > 250:
                new_data.append((r, g, b, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)

    # Redimensionar para caber em 512x512
    img.thumbnail(STICKER_SIZE, Image.Resampling.LANCZOS)
    w, h = img.size

    canvas = Image.new("RGBA", STICKER_SIZE, (0, 0, 0, 0))
    if crop_mode == "contain":
        x = (STICKER_SIZE[0] - w) // 2
        y = (STICKER_SIZE[1] - h) // 2
        canvas.paste(img, (x, y))
    else:
        # cover: centralizar e colar (thumbnail já limitou; sobra margem)
        x = (STICKER_SIZE[0] - w) // 2
        y = (STICKER_SIZE[1] - h) // 2
        canvas.paste(img, (x, y))

    out = io.BytesIO()
    quality = WEBP_QUALITY_MAX
    canvas.save(out, format="WEBP", quality=quality, method=6)
    data = out.getvalue()

    # Reduzir qualidade até ficar <= 100 KB
    while len(data) > MAX_BYTES and quality >= WEBP_QUALITY_MIN:
        quality -= 5
        out = io.BytesIO()
        canvas.save(out, format="WEBP", quality=max(1, quality), method=6)
        data = out.getvalue()

    if len(data) > MAX_BYTES:
        # Última tentativa com qualidade mínima
        out = io.BytesIO()
        canvas.save(out, format="WEBP", quality=1, method=4)
        data = out.getvalue()

    return data
