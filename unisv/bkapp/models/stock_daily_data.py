from django.db import models
from .base import BaseModel


class StockDailyData(BaseModel):
    class Meta:
        db_table = 'stock_daily_data'

    stock_code = models.CharField(max_length=20)
    trade_date = models.DateField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    high_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    low_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    close_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    volume = models.IntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    change_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def to_dict(self):
        """转换为字典"""
        data = super().to_dict()
        data.update({
            'stock_code': self.stock_code,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'open_price': float(self.open_price) if self.open_price is not None else 0.0,
            'high_price': float(self.high_price) if self.high_price is not None else 0.0,
            'low_price': float(self.low_price) if self.low_price is not None else 0.0,
            'close_price': float(self.close_price) if self.close_price is not None else 0.0,
            'volume': self.volume if self.volume is not None else 0,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'change_percent': float(self.change_percent) if self.change_percent is not None else 0.0
        })
        return data

    def __str__(self):
        return f'<StockDailyData {self.stock_code}:{self.trade_date}>'