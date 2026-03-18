from django.db import models
from .base import BaseModel


class BacktestRecord(BaseModel):
    class Meta:
        db_table = 'backtest_records'

    strategy = models.ForeignKey('StockSelectionStrategy', related_name='backtest_records', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=20, decimal_places=2)
    final_capital = models.DecimalField(max_digits=20, decimal_places=2)
    return_rate = models.DecimalField(max_digits=10, decimal_places=2)
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20)

    def to_dict(self):
        """转换为字典"""
        data = super().to_dict()
        data.update({
            'strategy_id': self.strategy_id if hasattr(self, 'strategy_id') else None,
            'strategy_name': self.strategy.name if self.strategy_id and self.strategy else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'initial_capital': float(self.initial_capital) if self.initial_capital is not None else 0.0,
            'final_capital': float(self.final_capital) if self.final_capital is not None else 0.0,
            'return_rate': float(self.return_rate) if self.return_rate is not None else 0.0,
            'max_drawdown': float(self.max_drawdown) if self.max_drawdown is not None else 0.0,
            'sharpe_ratio': float(self.sharpe_ratio) if self.sharpe_ratio is not None else 0.0,
            'status': self.status
        })
        return data

    def __str__(self):
        return f'<BacktestRecord {self.id}:{getattr(self, "strategy_id", None)}>'