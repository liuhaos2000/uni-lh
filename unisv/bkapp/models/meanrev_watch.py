from django.db import models
from django.conf import settings


class MeanrevWatch(models.Model):
    """均值回归策略订阅。

    每个用户最多 5 条订阅。enabled 字段同时作为"通知"开关。
    """
    class Meta:
        db_table = 'meanrev_watch'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meanrev_watches',
    )
    name = models.CharField(max_length=50, default='')
    etf_codes = models.JSONField(default=list)  # ["518880", "513100", ...]
    signal_type = models.CharField(max_length=20, default='bollinger')  # bollinger / rsi
    period = models.IntegerField(default=20)
    num_std = models.FloatField(default=2.0)
    oversold = models.IntegerField(default=30)
    overbought = models.IntegerField(default=70)
    stop_loss = models.FloatField(default=0.05)
    rebalance_days = models.IntegerField(default=1)
    initial_capital = models.FloatField(default=1000000)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'etf_codes': self.etf_codes,
            'signal_type': self.signal_type,
            'period': self.period,
            'num_std': self.num_std,
            'oversold': self.oversold,
            'overbought': self.overbought,
            'stop_loss': self.stop_loss,
            'rebalance_days': self.rebalance_days,
            'initial_capital': self.initial_capital,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f'<MeanrevWatch user={self.user_id} type={self.signal_type} codes={self.etf_codes}>'
