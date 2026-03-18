from django.db import models
from .base import BaseModel


class BacktestStrategy(BaseModel):
    class Meta:
        db_table = 'backtest_strategies'

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    strategy_class = models.CharField(max_length=100)
    parameters = models.JSONField(null=True, blank=True)

    def to_dict(self):
        """转换为字典"""
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description,
            'strategy_class': self.strategy_class,
            'parameters': self.parameters
        })
        return data

    def __str__(self):
        return f'<BacktestStrategy {self.name}>'