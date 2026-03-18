from django.db import models
from .base import BaseModel


class StockFinancialReport(BaseModel):
    class Meta:
        db_table = 'stock_financial_reports'
        indexes = [
            models.Index(fields=['stock_code', 'report_date'], name='idx_stock_code_date'),
            models.Index(fields=['report_date'], name='idx_report_date'),
            models.Index(fields=['quarter'], name='idx_quarter'),
            models.Index(fields=['stock_code'], name='idx_stock_code'),
            models.Index(fields=['industry'], name='idx_industry'),
        ]

    stock_code = models.CharField(max_length=20)
    stock_name = models.CharField(max_length=100)
    report_date = models.DateField()
    quarter = models.CharField(max_length=10)

    # 每股指标
    eps = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    bps = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    ocfps = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # 收入指标
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    revenue_yoy = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    revenue_qoq = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # 利润指标
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    profit_yoy = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    profit_qoq = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # 其他指标
    roe = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    gross_margin = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    announcement_date = models.DateField(null=True, blank=True)

    def to_dict(self):
        """转换为字典"""
        data = super().to_dict()
        data.update({
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'quarter': self.quarter,
            'eps': float(self.eps) if self.eps is not None else None,
            'bps': float(self.bps) if self.bps is not None else None,
            'ocfps': float(self.ocfps) if self.ocfps is not None else None,
            'total_revenue': float(self.total_revenue) if self.total_revenue is not None else None,
            'revenue_yoy': float(self.revenue_yoy) if self.revenue_yoy is not None else None,
            'revenue_qoq': float(self.revenue_qoq) if self.revenue_qoq is not None else None,
            'net_profit': float(self.net_profit) if self.net_profit is not None else None,
            'profit_yoy': float(self.profit_yoy) if self.profit_yoy is not None else None,
            'profit_qoq': float(self.profit_qoq) if self.profit_qoq is not None else None,
            'roe': float(self.roe) if self.roe is not None else None,
            'gross_margin': float(self.gross_margin) if self.gross_margin is not None else None,
            'industry': self.industry,
            'announcement_date': self.announcement_date.isoformat() if self.announcement_date else None
        })
        return data

    def __str__(self):
        return f'<StockFinancialReport {self.stock_code}:{self.report_date}:{self.quarter}>'
