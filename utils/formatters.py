"""
Formatting Utilities
Number, currency, and text formatting
"""


def format_currency(value, symbol="Rs."):
    """
    Format number as currency
    
    Args:
        value: Numeric value
        symbol: Currency symbol
        
    Returns:
        Formatted string
    """
    try:
        if value >= 0:
            return "%s %.2f" % (symbol, value)
        else:
            return "-%s %.2f" % (symbol, abs(value))
    except:
        return "%s 0.00" % symbol


def format_pnl(value):
    """
    Format P&L with sign
    
    Args:
        value: P&L value
        
    Returns:
        Formatted string with + or - sign
    """
    try:
        if value > 0:
            return "+%.2f" % value
        elif value < 0:
            return "%.2f" % value
        else:
            return "0.00"
    except:
        return "0.00"


def format_quantity(value):
    """
    Format quantity with sign
    
    Args:
        value: Quantity value
        
    Returns:
        Formatted string
    """
    try:
        if value > 0:
            return "+%d" % value
        else:
            return "%d" % value
    except:
        return "0"


def format_percentage(value):
    """
    Format as percentage
    
    Args:
        value: Decimal value (e.g., 0.05 for 5%)
        
    Returns:
        Formatted string with % sign
    """
    try:
        return "%.2f%%" % (value * 100)
    except:
        return "0.00%"


def get_pnl_color(value):
    """
    Get color for P&L value
    
    Args:
        value: P&L value
        
    Returns:
        Color hex code
    """
    if value > 0:
        return "#48bb78"  # Green
    elif value < 0:
        return "#f56565"  # Red
    else:
        return "#a0aec0"  # Gray


def get_quantity_color(value):
    """
    Get color for quantity value
    
    Args:
        value: Quantity value
        
    Returns:
        Color hex code
    """
    if value > 0:
        return "#48bb78"  # Green (buy)
    elif value < 0:
        return "#f56565"  # Red (sell)
    else:
        return "#a0aec0"  # Gray (neutral)


def truncate_text(text, max_length=20):
    """
    Truncate text to max length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ... if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


if __name__ == "__main__":
    # Test formatters
    print("Testing Formatters")
    print("=" * 50)
    
    print("\nCurrency:")
    print(format_currency(1234.56))
    print(format_currency(-1234.56))
    
    print("\nP&L:")
    print(format_pnl(123.45))
    print(format_pnl(-123.45))
    print(format_pnl(0))
    
    print("\nQuantity:")
    print(format_quantity(50))
    print(format_quantity(-50))
    print(format_quantity(0))
    
    print("\nPercentage:")
    print(format_percentage(0.0523))
    print(format_percentage(-0.0234))
    
    print("\nColors:")
    print("Profit: %s" % get_pnl_color(100))
    print("Loss: %s" % get_pnl_color(-100))
    print("Neutral: %s" % get_pnl_color(0))