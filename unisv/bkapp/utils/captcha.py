"""图形验证码工具：基于 Pillow 生成 4 位字符干扰图片，结果存入 cache。

使用流程：
1. 前端 GET /api/auth/captcha/ → 返回 {captcha_id, image_base64}
2. 用户填写后随表单提交 captcha_id + captcha_text
3. 后端 verify_captcha(captcha_id, text) → True/False，验证一次即失效
"""
import base64
import io
import random
import string
import uuid

from django.core.cache import cache

CAPTCHA_TTL = 5 * 60          # 验证码 5 分钟有效
CAPTCHA_LEN = 4               # 字符长度
CAPTCHA_CACHE_PREFIX = 'captcha:'

# 排除容易混淆的字符
_CHARS = ''.join(c for c in (string.ascii_uppercase + string.digits) if c not in 'O0I1L')


def _gen_text(n: int = CAPTCHA_LEN) -> str:
    return ''.join(random.choice(_CHARS) for _ in range(n))


def _gen_image(text: str) -> bytes:
    """生成带干扰的 PNG 图片字节，如果 Pillow 不可用则返回空字节。"""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        return b''

    width, height = 130, 44
    bg_color = (random.randint(220, 255),) * 3
    image = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # 字体：系统默认即可
    font_size = 36
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype('Arial.ttf', font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()
            

    # 干扰点
    for _ in range(120):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(random.randint(0, 200),) * 3,
        )
    # 干扰线
    for _ in range(4):
        draw.line(
            [
                (random.randint(0, width), random.randint(0, height)),
                (random.randint(0, width), random.randint(0, height)),
            ],
            fill=(random.randint(80, 180),) * 3,
            width=1,
        )

    # 文字
    char_w = width // (len(text) + 1)
    for idx, ch in enumerate(text):
        color = (
            random.randint(0, 120),
            random.randint(0, 120),
            random.randint(0, 120),
        )
        x = char_w * (idx + 0.5) + random.randint(-3, 3)
        y = random.randint(-2, 4)
        draw.text((x, y), ch, font=font, fill=color)

    image = image.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    return buf.getvalue()


def generate_captcha() -> dict:
    """生成新的验证码，返回 {captcha_id, image_base64}。"""
    text = _gen_text()
    captcha_id = uuid.uuid4().hex
    cache.set(CAPTCHA_CACHE_PREFIX + captcha_id, text.upper(), CAPTCHA_TTL)

    img_bytes = _gen_image(text)
    if img_bytes:
        b64 = 'data:image/png;base64,' + base64.b64encode(img_bytes).decode('ascii')
    else:
        # Pillow 缺失时降级：直接把验证码写在 data URI 里供调试
        b64 = ''
    return {
        'captcha_id': captcha_id,
        'image_base64': b64,
        # 如果图像生成失败（缺 Pillow），把明文回传方便联调；线上请确保 Pillow 已安装
        'fallback_text': text if not img_bytes else None,
    }


def verify_captcha(captcha_id: str, text: str, *, consume: bool = True) -> bool:
    """校验图形验证码。consume=True 时校验成功后立刻删除避免复用。"""
    if not captcha_id or not text:
        return False
    key = CAPTCHA_CACHE_PREFIX + captcha_id
    saved = cache.get(key)
    if not saved:
        return False
    ok = saved.upper() == text.strip().upper()
    if ok and consume:
        cache.delete(key)
    return ok
