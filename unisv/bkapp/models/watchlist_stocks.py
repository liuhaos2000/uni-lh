from django.db import models
from .base import BaseModel


class WatchlistStock(BaseModel):
    class Meta:
        db_table = 'watchlist_stocks'

    watchlist = models.ForeignKey('Watchlist', related_name='stocks', on_delete=models.CASCADE)
    stock_code = models.CharField(max_length=20)
    added_at = models.DateTimeField(auto_now_add=True)

    # 注意：SQLAlchemy 中的 exclude_properties 没有直接对应的 Django 选项。
    # 如果需要去掉 BaseModel 的某个字段，请在设计时调整 BaseModel 或在迁移层面处理。

    def to_dict(self):
        """转换为字典"""
        data = super().to_dict()
        data.update({
            'watchlist_id': self.watchlist_id,
            'stock_code': self.stock_code,
            'added_at': self.added_at.isoformat() if self.added_at else None
        })
        return data

    def __str__(self):
        return f'<WatchlistStock {self.watchlist_id}:{self.stock_code}>'