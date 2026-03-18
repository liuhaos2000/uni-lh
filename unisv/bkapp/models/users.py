from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from .base import BaseModel


class User(BaseModel):
    class Meta:
        db_table = 'users'

    username = models.CharField(max_length=80, unique=True)
    email = models.EmailField(max_length=120, unique=True)
    password_hash = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, null=True, blank=True)
    is_vip = models.BooleanField(default=False)
    
    def set_password(self, password):
        """设置密码哈希（使用 Django 的哈希器）"""
        self.password_hash = make_password(password)

    def check_password(self, password):
        """验证密码"""
        return check_password(password, self.password_hash)

    def to_dict(self):
        """转换为字典，排除敏感信息"""
        data = super().to_dict()
        data.update({
            'phone': self.phone,
            'username': self.username,
            'email': self.email,
            'is_vip': self.is_vip,
        })
        return data

    def __str__(self):
        return f'<User {self.username}>'