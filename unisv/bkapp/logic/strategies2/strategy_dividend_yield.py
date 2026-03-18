from .base import StockSelectionStrategyBase


class DividendYieldStrategy(StockSelectionStrategyBase):
    """Dividend yield based stock selection strategy.
    
    Selects stocks with dividend yield above a specified threshold.
    """
    value = '203'
    name = 'Dividend_Yield'
    params = ['min_dividend_yield']
    level = 'normal'
    category = 'Fundamental'
    description = 'Select stocks with high dividend yield'

    def __init__(self, min_dividend_yield=0.03, **kwargs):
        """Initialize strategy.
        
        Args:
            min_dividend_yield: Minimum dividend yield (e.g., 0.03 for 3%)
        """
        super().__init__(min_dividend_yield=min_dividend_yield, **kwargs)
        self.min_dividend_yield = float(min_dividend_yield)

    def filter_stocks(self, stocks_data):
        """Filter stocks with sufficient dividend yield."""
        import pandas as pd
        
        selected = []
        
        if isinstance(stocks_data, pd.DataFrame):
            for idx, stock in stocks_data.iterrows():
                yield_val = stock.get('dividend_yield', 0)
                if yield_val >= self.min_dividend_yield:
                    selected.append(stock)
        else:
            for stock in stocks_data:
                yield_val = stock.get('dividend_yield', 0)
                if yield_val >= self.min_dividend_yield:
                    selected.append(stock)
        
        return selected

    def score_stocks(self, stocks_data):
        """Score stocks by their dividend yield."""
        import pandas as pd
        
        scores = {}
        
        if isinstance(stocks_data, pd.DataFrame):
            for idx, stock in stocks_data.iterrows():
                symbol = stock.get('symbol', stock.get('code', str(idx)))
                yield_val = stock.get('dividend_yield', 0)
                scores[symbol] = yield_val
        else:
            for stock in stocks_data:
                symbol = stock.get('symbol', stock.get('code', ''))
                yield_val = stock.get('dividend_yield', 0)
                scores[symbol] = yield_val
        
        return scores
