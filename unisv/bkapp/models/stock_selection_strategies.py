from django.db import models
from .base import BaseModel


class StockSelectionStrategy(BaseModel):
    class Meta:
        db_table = 'stock_strategies'

    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    class_name = models.CharField(max_length=100)
    params = models.JSONField(null=True, blank=True)

    def to_dict(self):
        """转换为字典"""
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description,
            'class_name': self.class_name,
            'params': self.params
        })
        return data

    def __str__(self):
        return f'<StockSelectionStrategy {self.name}>'