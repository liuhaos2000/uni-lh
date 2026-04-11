"""邮箱验证码 + 登录失败计数（基于 Django cache / Redis）。"""
import logging
import random
import time
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

CODE_TTL = 5 * 60         # 验证码有效期：5 分钟
SEND_THROTTLE = 60        # 同邮箱发送间隔：60 秒
LOGIN_FAIL_TTL = 10 * 60  # 登录失败计数窗口：10 分钟
LOGIN_FAIL_LIMIT = 5      # 失败上限

CODE_PREFIX = 'email_code:'
THROTTLE_PREFIX = 'email_code_throttle:'
LOGIN_FAIL_PREFIX = 'login_fail:'


# ---------- 邮箱验证码 ----------

def _gen_code() -> str:
    return ''.join(random.choice('0123456789') for _ in range(6))


def can_send(email: str) -> int:
    """返回距离下次可发送还剩多少秒；0 表示可发送。"""
    key = THROTTLE_PREFIX + email.lower()
    saved = cache.get(key)
    if not saved:
        return 0
    try:
        remain = int(SEND_THROTTLE - (time.time() - float(saved)))
    except (TypeError, ValueError):
        return SEND_THROTTLE
    return max(0, remain)


def issue_code(email: str, purpose: str = 'register') -> str:
    """生成 6 位验证码并发送到邮箱。返回验证码（用于日志/调试）。"""
    email = email.strip().lower()
    code = _gen_code()
    cache.set(CODE_PREFIX + f'{purpose}:' + email, code, CODE_TTL)
    # 节流：存入发送时间戳
    cache.set(THROTTLE_PREFIX + email, str(time.time()), SEND_THROTTLE)

    brand = getattr(settings, 'BRAND_NAME', '金点策略')
    subject_map = {
        'register': f'【{brand}】注册验证码',
        'reset': f'【{brand}】找回密码验证码',
    }
    subject = subject_map.get(purpose, f'【{brand}】验证码')
    body = (
        f'您本次的验证码是：{code}\n\n'
        f'有效期 5 分钟，请勿泄露给他人。\n'
        f'如非本人操作请忽略此邮件。'
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception('发送验证码失败 %s: %s', email, exc)
        raise
    return code


def verify_code(email: str, code: str, purpose: str = 'register', *, consume: bool = True) -> bool:
    if not email or not code:
        return False
    key = CODE_PREFIX + f'{purpose}:' + email.strip().lower()
    saved = cache.get(key)
    if not saved:
        return False
    ok = str(saved) == str(code).strip()
    if ok and consume:
        cache.delete(key)
    return ok


# ---------- 登录失败计数 ----------

def login_fail_record(identifier: str) -> int:
    """登录失败 +1，返回当前失败次数。"""
    key = LOGIN_FAIL_PREFIX + identifier.lower()
    current = cache.get(key) or 0
    try:
        current = int(current)
    except (TypeError, ValueError):
        current = 0
    n = current + 1
    cache.set(key, n, LOGIN_FAIL_TTL)
    return n


def login_fail_count(identifier: str) -> int:
    val = cache.get(LOGIN_FAIL_PREFIX + identifier.lower()) or 0
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def login_fail_reset(identifier: str):
    cache.delete(LOGIN_FAIL_PREFIX + identifier.lower())


def is_login_locked(identifier: str) -> bool:
    return login_fail_count(identifier) >= LOGIN_FAIL_LIMIT
