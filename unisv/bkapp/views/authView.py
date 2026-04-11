"""用户注册 / 登录 / 邮箱验证码 / 找回密码。

新方案：
- 注册：邮箱 + 用户名 + 密码 + 邮箱验证码 + 图形验证码
- 登录：邮箱 + 密码 + 图形验证码（5 次失败锁 10 分钟）
- 找回密码：邮箱 + 邮箱验证码 + 新密码
"""
import re
import logging

from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..models.users2 import User2
from ..utils.captcha import generate_captcha, verify_captcha
from ..utils.email_code import (
    issue_code,
    verify_code,
    can_send,
    is_login_locked,
    login_fail_record,
    login_fail_reset,
    LOGIN_FAIL_LIMIT,
)

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')
USERNAME_RE = re.compile(r'^[A-Za-z0-9_\-\u4e00-\u9fa5]{2,30}$')


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _user_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'nickname': getattr(user, 'nickname', '') or '',
        'is_vip': getattr(user, 'is_vip', False),
        'backtest_count': getattr(user, 'backtest_count', 0),
        'backtest_quota': getattr(user, 'backtest_quota', 20),
    }


def _err(msg, code=400, http=status.HTTP_400_BAD_REQUEST):
    return Response({'code': code, 'message': msg}, status=http)


# ---------------------------------------------------------------------------
# 图形验证码
# ---------------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def captcha(request):
    """获取一张新的图形验证码。"""
    data = generate_captcha()
    return Response({'code': 0, 'data': data})


# ---------------------------------------------------------------------------
# 发送邮箱验证码
# ---------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def send_email_code(request):
    """发送邮箱验证码。

    body: {email, captcha_id, captcha_text, purpose?}
    purpose: register | reset
    """
    data = request.data or {}
    email = (data.get('email') or '').strip().lower()
    captcha_id = data.get('captcha_id') or ''
    captcha_text = data.get('captcha_text') or ''
    purpose = data.get('purpose') or 'register'

    if purpose not in ('register', 'reset'):
        return _err('purpose 非法')
    if not EMAIL_RE.match(email):
        return _err('邮箱格式不正确')
    if not verify_captcha(captcha_id, captcha_text):
        return _err('图形验证码错误或已过期', code=4101)

    # 注册场景：邮箱不能已存在；找回场景：必须存在
    exists = User2.objects.filter(email__iexact=email).exists()
    if purpose == 'register' and exists:
        return _err('该邮箱已被注册', code=409, http=status.HTTP_409_CONFLICT)
    if purpose == 'reset' and not exists:
        return _err('该邮箱尚未注册', code=404, http=status.HTTP_404_NOT_FOUND)

    wait = can_send(email)
    if wait:
        return _err(f'请 {wait} 秒后再试', code=4102, http=status.HTTP_429_TOO_MANY_REQUESTS)

    try:
        issue_code(email, purpose=purpose)
    except Exception as exc:
        logger.exception('发送验证码失败: %s', exc)
        return _err('邮件发送失败，请稍后再试', code=500, http=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'code': 0, 'message': '验证码已发送'})


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """注册新账号。

    body: {email, username, password, email_code, captcha_id, captcha_text, nickname?}
    """
    data = request.data or {}
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    email_code = (data.get('email_code') or '').strip()
    captcha_id = data.get('captcha_id') or ''
    captcha_text = data.get('captcha_text') or ''
    nickname = (data.get('nickname') or '').strip()

    if not EMAIL_RE.match(email):
        return _err('邮箱格式不正确')
    if not USERNAME_RE.match(username):
        return _err('用户名 2-30 位（字母/数字/下划线/中文）')
    if len(password) < 6 or len(password) > 60:
        return _err('密码长度需在 6-60 之间')
    if not verify_captcha(captcha_id, captcha_text):
        return _err('图形验证码错误或已过期', code=4101)
    if not verify_code(email, email_code, purpose='register'):
        return _err('邮箱验证码错误或已过期', code=4103)

    if User2.objects.filter(email__iexact=email).exists():
        return _err('该邮箱已被注册', code=409, http=status.HTTP_409_CONFLICT)
    if User2.objects.filter(username=username).exists():
        return _err('用户名已被占用', code=409, http=status.HTTP_409_CONFLICT)

    user = User2.objects.create_user(username=username, email=email, password=password)
    if nickname:
        user.nickname = nickname
    user.save()

    tokens = _tokens_for_user(user)
    return Response({
        'code': 0,
        'message': '注册成功',
        'data': {**tokens, 'user': _user_payload(user)},
    })


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """用户登录。

    body: {email, password, captcha_id, captcha_text}
    """
    data = request.data or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    captcha_id = data.get('captcha_id') or ''
    captcha_text = data.get('captcha_text') or ''

    if not email or not password:
        return _err('邮箱和密码不能为空')
    if not verify_captcha(captcha_id, captcha_text):
        return _err('图形验证码错误或已过期', code=4101)

    if is_login_locked(email):
        return _err(
            f'登录失败次数过多，请 10 分钟后再试',
            code=4104,
            http=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        user_obj = User2.objects.get(email__iexact=email)
    except User2.DoesNotExist:
        login_fail_record(email)
        return _err('邮箱或密码错误', code=401, http=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(request, username=user_obj.username, password=password)
    if not user:
        n = login_fail_record(email)
        remain = max(0, LOGIN_FAIL_LIMIT - n)
        return _err(
            f'邮箱或密码错误，剩余尝试次数 {remain}',
            code=401,
            http=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return _err('账号已被禁用', code=403, http=status.HTTP_403_FORBIDDEN)

    login_fail_reset(email)
    tokens = _tokens_for_user(user)
    return Response({
        'code': 0,
        'message': '登录成功',
        'data': {**tokens, 'user': _user_payload(user)},
    })


# ---------------------------------------------------------------------------
# 找回密码
# ---------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """通过邮箱验证码重置密码。

    body: {email, email_code, new_password, captcha_id, captcha_text}
    """
    data = request.data or {}
    email = (data.get('email') or '').strip().lower()
    email_code = (data.get('email_code') or '').strip()
    new_password = data.get('new_password') or ''
    captcha_id = data.get('captcha_id') or ''
    captcha_text = data.get('captcha_text') or ''

    if not EMAIL_RE.match(email):
        return _err('邮箱格式不正确')
    if len(new_password) < 6 or len(new_password) > 60:
        return _err('密码长度需在 6-60 之间')
    if not verify_captcha(captcha_id, captcha_text):
        return _err('图形验证码错误或已过期', code=4101)
    if not verify_code(email, email_code, purpose='reset'):
        return _err('邮箱验证码错误或已过期', code=4103)

    try:
        user = User2.objects.get(email__iexact=email)
    except User2.DoesNotExist:
        return _err('该邮箱尚未注册', code=404, http=status.HTTP_404_NOT_FOUND)

    user.set_password(new_password)
    user.save(update_fields=['password'])
    login_fail_reset(email)

    return Response({'code': 0, 'message': '密码重置成功，请重新登录'})


# ---------------------------------------------------------------------------
# 当前用户信息
# ---------------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({'code': 0, 'data': _user_payload(request.user)})
