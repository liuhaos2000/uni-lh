# Stock selection strategy base class

class StockSelectionStrategyBase:
    """Base class for stock selection strategies.
    
    Stock selection strategies are used to filter and identify stocks that meet
    certain criteria for investment.
    """
    value = '00'
    name = 'base'
    params = []
    level = 'normal'  # 'normal' or 'vip'
    category = 'General'  # Category of the strategy
    description = ''  # Description of the strategy

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def filter_stocks(self, stocks_data):
        """Filter stocks based on strategy criteria.
        
        Args:
            stocks_data: List of stock data dictionaries or DataFrame with stock info
            
        Returns:
            List of selected stocks meeting the strategy criteria
        """
        raise NotImplementedError

    def score_stocks(self, stocks_data):
        """Score stocks for ranking purposes.
        
        Args:
            stocks_data: List of stock data dictionaries or DataFrame with stock info
            
        Returns:
            Dictionary with stock symbols as keys and scores as values
        """
        raise NotImplementedError
