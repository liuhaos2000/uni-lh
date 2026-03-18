from .base import StockSelectionStrategyBase


class PERatioStrategy(StockSelectionStrategyBase):
    """P/E Ratio based stock selection strategy.
    
    Selects stocks with P/E ratio within a specified range.
    """
    value = '202'
    name = 'PE_Ratio'
    params = ['min_pe', 'max_pe']
    level = 'normal'
    category = 'Fundamental'
    description = 'Select stocks with P/E ratio in specified range'

    def __init__(self, min_pe=10, max_pe=30, **kwargs):
        """Initialize strategy.
        
        Args:
            min_pe: Minimum P/E ratio threshold
            max_pe: Maximum P/E ratio threshold
        """
        super().__init__(min_pe=min_pe, max_pe=max_pe, **kwargs)
        self.min_pe = float(min_pe)
        self.max_pe = float(max_pe)

    def filter_stocks(self, stocks_data):
        """Filter stocks with P/E ratio in range."""
        import pandas as pd
        
        selected = []
        
        if isinstance(stocks_data, pd.DataFrame):
            for idx, stock in stocks_data.iterrows():
                pe = stock.get('pe_ratio', None)
                if pe is not None and self.min_pe <= pe <= self.max_pe:
                    selected.append(stock)
        else:
            for stock in stocks_data:
                pe = stock.get('pe_ratio', None)
                if pe is not None and self.min_pe <= pe <= self.max_pe:
                    selected.append(stock)
        
        return selected

    def score_stocks(self, stocks_data):
        """Score stocks - higher score for P/E closer to mid-point."""
        import pandas as pd
        
        scores = {}
        mid_pe = (self.min_pe + self.max_pe) / 2
        
        if isinstance(stocks_data, pd.DataFrame):
            for idx, stock in stocks_data.iterrows():
                symbol = stock.get('symbol', stock.get('code', str(idx)))
                pe = stock.get('pe_ratio', None)
                if pe is not None:
                    # Closer to mid-pe gets higher score
                    scores[symbol] = 1 - (abs(pe - mid_pe) / mid_pe)
                else:
                    scores[symbol] = 0
        else:
            for stock in stocks_data:
                symbol = stock.get('symbol', stock.get('code', ''))
                pe = stock.get('pe_ratio', None)
                if pe is not None:
                    scores[symbol] = 1 - (abs(pe - mid_pe) / mid_pe)
                else:
                    scores[symbol] = 0
        
        return scores
