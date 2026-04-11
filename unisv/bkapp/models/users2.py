from django.contrib.auth.models import AbstractUser
from django.db import models

class User2(AbstractUser):
    # 邮箱：唯一且必填，作为登录主键使用
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    is_vip = models.BooleanField(default=False)
    nickname = models.CharField(max_length=100, null=True, blank=True)
    openid = models.CharField(max_length=255, null=True, blank=True, unique=True)
    headimg = models.URLField(null=True, blank=True)

    # 非 VIP 回测/优化配额
    backtest_count = models.IntegerField(default=0)   # 累计已使用次数
    backtest_quota = models.IntegerField(default=20)  # 总配额（管理员可在后台调整）

    def to_dict(self):
        """返回字典，不包含密碼"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'is_vip': self.is_vip,
            'nickname': self.nickname,
            'openid': self.openid,
            'headimg': self.headimg,
            'backtest_count': self.backtest_count,
            'backtest_quota': self.backtest_quota,
        }
        return data

    def __str__(self):
        return f'<User {self.username}>'
