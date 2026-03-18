from .base import StockSelectionStrategyBase


class PriceMomentumStrategy(StockSelectionStrategyBase):
    """Price momentum strategy for stock selection.
    
    Selects stocks with strong upward price momentum based on recent price changes.
    """
    value = '201'
    name = 'Price_Momentum'
    params = ['days', 'min_change_rate']
    level = 'vip'
    category = 'Technical'
    description = 'Select stocks with strong upward price momentum'

    def __init__(self, days=20, min_change_rate=0.05, **kwargs):
        """Initialize strategy.
        
        Args:
            days: Number of days to look back for momentum calculation
            min_change_rate: Minimum price change rate (e.g., 0.05 for 5%)
        """
        super().__init__(days=days, min_change_rate=min_change_rate, **kwargs)
        self.days = int(days)
        self.min_change_rate = float(min_change_rate)

    def filter_stocks(self, stocks_data):
        """Filter stocks with positive momentum."""
        import pandas as pd
        
        selected = []
        
        if isinstance(stocks_data, pd.DataFrame):
            for idx, stock in stocks_data.iterrows():
                if self._calculate_momentum(stock) >= self.min_change_rate:
                    selected.append(stock)
        else:
            for stock in stocks_data:
                if self._calculate_momentum(stock) >= self.min_change_rate:
                    selected.append(stock)
        
        return selected

    def score_stocks(self, stocks_data):
        """Score stocks by their momentum."""
        import pandas as pd
        
        scores = {}
        
        if isinstance(stocks_data, pd.DataFrame):
            for idx, stock in stocks_data.iterrows():
                symbol = stock.get('symbol', stock.get('code', str(idx)))
                scores[symbol] = self._calculate_momentum(stock)
        else:
            for stock in stocks_data:
                symbol = stock.get('symbol', stock.get('code', ''))
                scores[symbol] = self._calculate_momentum(stock)
        
        return scores

    def _calculate_momentum(self, stock):
        """Calculate momentum for a single stock."""
        # This is a simplified version - in real usage, you'd have historical price data
        current_price = stock.get('close', stock.get('current_price', 0))
        previous_price = stock.get('open', stock.get('previous_close', current_price))
        
        if previous_price == 0:
            return 0
        
        return (current_price - previous_price) / previous_price
