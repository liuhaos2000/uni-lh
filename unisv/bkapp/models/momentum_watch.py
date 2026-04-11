from django.db import models
from django.conf import settings


class MomentumWatch(models.Model):
    """动量轮动策略订阅。

    每个用户最多一条订阅记录（user OneToOne）。
    模拟交易状态不在此存储——任务每天重跑回测取最后一天结果。
    """
    class Meta:
        db_table = 'momentum_watch'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='momentum_watch',
    )
    etf_codes = models.JSONField(default=list)  # ["518880", "513100", ...]
    lookback_n = models.IntegerField(default=25)
    rebalance_days = models.IntegerField(default=5)
    initial_capital = models.FloatField(default=1000000)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'etf_codes': self.etf_codes,
            'lookback_n': self.lookback_n,
            'rebalance_days': self.rebalance_days,
            'initial_capital': self.initial_capital,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f'<MomentumWatch user={self.user_id} codes={self.etf_codes}>'
