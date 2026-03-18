from django.db import models
from .base import BaseModel


class Stock(BaseModel):
    class Meta:
        db_table = 'stocks'

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    market = models.CharField(max_length=20, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    sector = models.CharField(max_length=100, null=True, blank=True)
    price = models.FloatField(null=True, blank=True)
    change_percent = models.FloatField(null=True, blank=True)
    price_change = models.FloatField(null=True, blank=True)
    volume = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    amplitude = models.FloatField(null=True, blank=True)
    high_price = models.FloatField(null=True, blank=True)
    low_price = models.FloatField(null=True, blank=True)
    open_price = models.FloatField(null=True, blank=True)
    prev_close = models.FloatField(null=True, blank=True)
    volume_ratio = models.FloatField(null=True, blank=True)
    turnover_rate = models.FloatField(null=True, blank=True)
    pe = models.FloatField(null=True, blank=True)
    pb = models.FloatField(null=True, blank=True)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    circulating_market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    price_speed = models.FloatField(null=True, blank=True)
    five_minute_change = models.FloatField(null=True, blank=True)
    sixty_day_change = models.FloatField(null=True, blank=True)
    year_to_date_change = models.FloatField(null=True, blank=True)

    def to_dict(self):
        """转换为字典，包含所有字段"""
        data = super().to_dict()
        data.update({
            'code': self.code,
            'name': self.name,
            'market': self.market,
            'industry': self.industry,
            'sector': self.sector,
            'price': float(self.price) if self.price is not None else None,
            'change_percent': float(self.change_percent) if self.change_percent is not None else None,
            'price_change': float(self.price_change) if self.price_change is not None else None,
            'volume': float(self.volume) if self.volume is not None else None,
            'amount': float(self.amount) if self.amount is not None else None,
            'amplitude': float(self.amplitude) if self.amplitude is not None else None,
            'high_price': float(self.high_price) if self.high_price is not None else None,
            'low_price': float(self.low_price) if self.low_price is not None else None,
            'open_price': float(self.open_price) if self.open_price is not None else None,
            'prev_close': float(self.prev_close) if self.prev_close is not None else None,
            'volume_ratio': float(self.volume_ratio) if self.volume_ratio is not None else None,
            'turnover_rate': float(self.turnover_rate) if self.turnover_rate is not None else None,
            'pe': float(self.pe) if self.pe is not None else None,
            'pb': float(self.pb) if self.pb is not None else None,
            'market_cap': float(self.market_cap) if self.market_cap is not None else None,
            'circulating_market_cap': float(self.circulating_market_cap) if self.circulating_market_cap is not None else None,
            'price_speed': float(self.price_speed) if self.price_speed is not None else None,
            'five_minute_change': float(self.five_minute_change) if self.five_minute_change is not None else None,
            'sixty_day_change': float(self.sixty_day_change) if self.sixty_day_change is not None else None,
            'year_to_date_change': float(self.year_to_date_change) if self.year_to_date_change is not None else None
        })
        return data

    def __str__(self):
        return f'<Stock {self.code}:{self.name}>'