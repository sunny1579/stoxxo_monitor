
"""
Comprehensive Stoxxo API Library
================================

A complete Python library for interacting with Stoxxo Intelligent Trading Bridge.
Provides all functionality from the Stoxxo documentation in an organized, easy-to-use format.

Author: AI Assistant
Version: 1.1.0
License: MIT

Installation:
    pip install requests

Basic Usage:
    from stoxxo_complete import StoxxoClient
    
    client = StoxxoClient()
    if client.status.ping():
        print("Connected to Stoxxo Bridge")
"""

import json
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import requests


# =============================================================================
# CONFIGURATION AND DATA MODELS
# =============================================================================

@dataclass
class StoxxoConfig:
    """Configuration settings for Stoxxo client"""
    bridge_ports: List[int] = None
    request_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.bridge_ports is None:
            self.bridge_ports = [21000, 80]


class TransactionType(Enum):
    """Transaction types for orders"""
    LONG_ENTRY = "LE"
    LONG_EXIT = "LX" 
    SHORT_ENTRY = "SE"
    SHORT_EXIT = "SX"
    LONG_MODIFY = "LM"
    SHORT_MODIFY = "SM"


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"


class ProductType(Enum):
    """Product types"""
    MIS = "MIS"
    CNC = "CNC"
    NRML = "NRML"
    BRACKET_ORDER = "BO"
    COVER_ORDER = "CO"


class Exchange(Enum):
    """Supported exchanges"""
    NSE = "NSE"
    NFO = "NFO"
    BSE = "BSE"
    CDS = "CDS"
    MCX = "MCX"


@dataclass
class OrderData:
    """Order information structure"""
    request_id: Optional[int] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    transaction_type: Optional[str] = None
    order_type: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: Optional[str] = None
    filled_quantity: Optional[int] = None
    average_price: Optional[float] = None
    error: Optional[str] = None


@dataclass
class PortfolioData:
    """Multi-leg portfolio information"""
    name: str
    mtm: Optional[float] = None
    status: Optional[str] = None
    premium: Optional[float] = None
    legs: Optional[str] = None
    delta: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    error: Optional[str] = None


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    ltp: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: Optional[datetime] = None


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class StoxxoException(Exception):
    """Base exception for Stoxxo operations"""
    pass


class StoxxoConnectionError(StoxxoException):
    """Bridge connection error"""
    pass


class StoxxoAPIError(StoxxoException):
    """API call error"""
    pass


class StoxxoOrderError(StoxxoException):
    """Order-specific error"""
    pass


class StoxxoParsingError(StoxxoException):
    """Response parsing error"""
    pass


# =============================================================================
# RESPONSE PROCESSOR
# =============================================================================

class StoxxoResponseProcessor:
    """Handles Stoxxo API response processing and parsing"""
    
    @staticmethod
    def parse_response(response_text: str) -> Any:
        """
        Parse Stoxxo API response (JSON or plain text)
        
        Args:
            response_text: Raw response from Stoxxo API
            
        Returns:
            Parsed response data
        """
        if not response_text:
            return None
        
        try:
            # Try JSON parsing first
            response_json = json.loads(response_text)
            
            if isinstance(response_json, dict):
                # Standard Stoxxo response format
                if 'response' in response_json:
                    return response_json['response']
                elif response_json.get('status') == 'success':
                    # Alternative response formats
                    for key in ['data', 'value', 'result']:
                        if key in response_json:
                            return response_json[key]
                    return response_json.get('response', '')
                else:
                    # Error response
                    if 'error' in response_json:
                        raise StoxxoAPIError(f"API Error: {response_json['error']}")
                    return response_text
            else:
                return response_json
                
        except json.JSONDecodeError:
            # Plain text response
            return response_text
    
    @staticmethod
    def parse_numeric(value: Any) -> Optional[float]:
        """
        Parse numeric values from API responses
        
        Args:
            value: Raw value to parse
            
        Returns:
            Parsed float value or None
        """
        if value is None:
            return None
        
        try:
            # Clean string values
            cleaned = str(value).replace(',', '').strip()
            if cleaned.replace('-', '').replace('.', '').isdigit():
                return float(cleaned)
            
            # Extract numbers using regex
            numbers = re.findall(r'-?\d+\.?\d*', cleaned)
            if numbers:
                return float(numbers[0])
        except (ValueError, TypeError):
            pass
        
        return None
    
    @staticmethod
    def validate_request_id(request_id: Any) -> bool:
        """
        Validate if request ID indicates success
        
        Args:
            request_id: Request ID to validate
            
        Returns:
            True if valid success ID, False otherwise
        """
        try:
            return int(request_id) >= 90000
        except (ValueError, TypeError):
            return False


# =============================================================================
# CORE CLIENT
# =============================================================================

class StoxxoClient:
    """
    Core Stoxxo client for HTTP communication
    
    Handles connection management, request routing, and response processing
    """
    
    def __init__(self, config: Optional[StoxxoConfig] = None):
        """
        Initialize Stoxxo client
        
        Args:
            config: Configuration object (optional)
        """
        self.config = config or StoxxoConfig()
        self.base_url = None
        self.working_port = None
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, self.config.log_level))
        self.logger = logging.getLogger(__name__)
        
        # Initialize response processor
        self.processor = StoxxoResponseProcessor()
        
        # Initialize functional modules
        self.status = StoxxoStatus(self)
        self.active_trading = StoxxoActiveTrading(self)
        self.passive_trading = StoxxoPassiveTrading(self)
        self.order_management = StoxxoOrderManagement(self)
        self.position_management = StoxxoPositionManagement(self)
        self.market_data = StoxxoMarketData(self)
        self.order_info = StoxxoOrderInfo(self)
        self.multi_leg = StoxxoMultiLeg(self)
        self.system_info = StoxxoSystemInfo(self)
    
    def _find_working_port(self) -> Optional[int]:
        """Find working Stoxxo bridge port"""
        for port in self.config.bridge_ports:
            try:
                url = f"http://localhost:{port}/Ping"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.working_port = port
                    self.base_url = f"http://localhost:{port}"
                    self.logger.info(f"Connected to Stoxxo bridge on port {port}")
                    return port
            except requests.exceptions.ConnectionError:
                continue
            except Exception as e:
                self.logger.warning(f"Error testing port {port}: {e}")
                continue
        
        return None
    
    def request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """
        Make HTTP request to Stoxxo bridge
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Parsed response data
            
        Raises:
            StoxxoConnectionError: If cannot connect to bridge
            StoxxoAPIError: If API returns error
        """
        if not self.base_url:
            if not self._find_working_port():
                raise StoxxoConnectionError("Cannot connect to Stoxxo bridge on any configured port")
        
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = requests.get(
                    url, 
                    params=params or {}, 
                    timeout=self.config.request_timeout
                )
                
                if response.status_code == 200:
                    return self.processor.parse_response(response.text.strip())
                else:
                    self.logger.warning(f"Request failed with status {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error on attempt {attempt + 1}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
                    # Try to find working port again
                    self._find_working_port()
                continue
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                break
        
        raise StoxxoConnectionError(f"Failed to complete request to {endpoint} after {self.config.retry_attempts} attempts")


# =============================================================================
# CONNECTION & STATUS MODULE
# =============================================================================

class StoxxoStatus:
    """Handles connection and status operations"""
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def ping(self) -> bool:
        """
        Check bridge connectivity and trading status
        
        Returns:
            True if bridge is running and trading is active
        """
        try:
            result = self.client.request("Ping")
            return bool(result)
        except Exception:
            return False
    
    def get_error(self, request_id: int) -> Optional[str]:
        """
        Get error details for a request ID
        
        Args:
            request_id: Request ID to check
            
        Returns:
            Error message or None
        """
        try:
            return self.client.request("GetError", {"RequestID": request_id})
        except Exception as e:
            return str(e)


# =============================================================================
# ACTIVE TRADING MODULE
# =============================================================================

class StoxxoActiveTrading:
    """
    Handles active bridge trading operations
    Uses symbol mapping and strategy settings
    """
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def mapped_order_simple(self, 
                          source_symbol: str, 
                          transaction_type: Union[str, TransactionType], 
                          signal_ltp: float, 
                          strategy_tag: str) -> int:
        """
        Place simple mapped order
        
        Args:
            source_symbol: Symbol from charting platform
            transaction_type: LE, LX, SE, SX
            signal_ltp: Last traded price from signal
            strategy_tag: Strategy identifier
            
        Returns:
            Request ID (>= 90000 for success)
        """
        if isinstance(transaction_type, TransactionType):
            transaction_type = transaction_type.value
        
        params = {
            "SourceSymbol": source_symbol,
            "TransactionType": transaction_type,
            "SignalLTP": signal_ltp,
            "StrategyTag": strategy_tag
        }
        
        result = self.client.request("MappedOrderSimple", params)
        request_id = int(result) if result else 0
        
        if not self.client.processor.validate_request_id(request_id):
            error = self.client.status.get_error(request_id)
            raise StoxxoOrderError(f"Order failed: {error}")
        
        return request_id
    
    def mapped_order_mod(self,
                        signal_id: int,
                        transaction_type: Union[str, TransactionType],
                        source_symbol: str,
                        order_type: Union[str, OrderType] = "",
                        trigger_price: float = 0,
                        price: float = 0,
                        quantity: int = 0,
                        signal_ltp: float = 0,
                        strategy_tag: str = "DEFAULT") -> int:
        """
        Place modified mapped order with additional parameters
        
        Args:
            signal_id: Unique signal identifier
            transaction_type: LE, LX, SE, SX
            source_symbol: Symbol from charting platform
            order_type: MARKET, LIMIT, SL, SL-M
            trigger_price: Trigger price for SL orders
            price: Limit price
            quantity: Order quantity (in lots for F&O)
            signal_ltp: Signal LTP
            strategy_tag: Strategy identifier
            
        Returns:
            Request ID
        """
        if isinstance(transaction_type, TransactionType):
            transaction_type = transaction_type.value
        if isinstance(order_type, OrderType):
            order_type = order_type.value
        
        params = {
            "SignalID": signal_id,
            "TransactionType": transaction_type,
            "SourceSymbol": source_symbol,
            "OrderType": order_type,
            "TriggerPrice": trigger_price,
            "Price": price,
            "Quantity": quantity,
            "SignalLTP": signal_ltp,
            "StrategyTag": strategy_tag
        }
        
        result = self.client.request("MappedOrderMod", params)
        return int(result) if result else 0
    
    def mapped_order_advanced(self,
                            signal_id: int,
                            transaction_type: Union[str, TransactionType],
                            source_symbol: str,
                            order_type: Union[str, OrderType] = "",
                            trigger_price: float = 0,
                            price: float = 0,
                            quantity: int = 0,
                            target: str = "0",
                            stop_loss: str = "0",
                            trailing_stop_loss: str = "0",
                            signal_ltp: float = 0,
                            strategy_tag: str = "DEFAULT",
                            product_type: Union[str, ProductType] = "",
                            options_type: str = "") -> int:
        """
        Place advanced mapped order with all parameters
        
        Args:
            signal_id: Unique signal identifier
            transaction_type: LE, LX, SE, SX
            source_symbol: Symbol from charting platform
            order_type: MARKET, LIMIT, SL, SL-M
            trigger_price: Trigger price
            price: Limit price
            quantity: Order quantity
            target: Target as points or percentage (e.g., "10" or "1.5%")
            stop_loss: Stop loss as points or percentage
            trailing_stop_loss: Trailing SL as points or percentage
            signal_ltp: Signal LTP
            strategy_tag: Strategy identifier
            product_type: MIS, CNC, NRML, BO, CO
            options_type: CE, PE
            
        Returns:
            Request ID
        """
        if isinstance(transaction_type, TransactionType):
            transaction_type = transaction_type.value
        if isinstance(order_type, OrderType):
            order_type = order_type.value
        if isinstance(product_type, ProductType):
            product_type = product_type.value
        
        params = {
            "SignalID": signal_id,
            "TransactionType": transaction_type,
            "SourceSymbol": source_symbol,
            "OrderType": order_type,
            "TriggerPrice": trigger_price,
            "Price": price,
            "Quantity": quantity,
            "Target": target,
            "StopLoss": stop_loss,
            "TrailingStoploss": trailing_stop_loss,
            "SignalLTP": signal_ltp,
            "StrategyTag": strategy_tag,
            "ProductType": product_type,
            "OptionsType": options_type
        }
        
        result = self.client.request("MappedOrderAdv", params)
        return int(result) if result else 0
    
    def mapped_order_scheduled(self,
                             signal_id: int,
                             transaction_type: Union[str, TransactionType],
                             source_symbol: str,
                             schedule_time: str,
                             order_type: Union[str, OrderType] = "",
                             trigger_price: float = 0,
                             price: float = 0,
                             quantity: int = 0,
                             target: str = "0",
                             stop_loss: str = "0",
                             trailing_stop_loss: str = "0",
                             signal_ltp: float = 0,
                             strategy_tag: str = "DEFAULT",
                             product_type: Union[str, ProductType] = "",
                             options_type: str = "") -> int:
        """
        Place scheduled mapped order
        
        Args:
            signal_id: Unique signal identifier
            transaction_type: LE, LX, SE, SX
            source_symbol: Symbol from charting platform
            schedule_time: Execution time (DD-MON-YYYY HH:MM:SS)
            order_type: MARKET, LIMIT, SL, SL-M
            trigger_price: Trigger price
            price: Limit price
            quantity: Order quantity
            target: Target as points or percentage
            stop_loss: Stop loss as points or percentage
            trailing_stop_loss: Trailing SL as points or percentage
            signal_ltp: Signal LTP
            strategy_tag: Strategy identifier
            product_type: MIS, CNC, NRML, BO, CO
            options_type: CE, PE
            
        Returns:
            Request ID
        """
        if isinstance(transaction_type, TransactionType):
            transaction_type = transaction_type.value
        if isinstance(order_type, OrderType):
            order_type = order_type.value
        if isinstance(product_type, ProductType):
            product_type = product_type.value
        
        params = {
            "SignalID": signal_id,
            "TransactionType": transaction_type,
            "SourceSymbol": source_symbol,
            "OrderType": order_type,
            "TriggerPrice": trigger_price,
            "Price": price,
            "Quantity": quantity,
            "Target": target,
            "StopLoss": stop_loss,
            "TrailingStoploss": trailing_stop_loss,
            "SignalLTP": signal_ltp,
            "StrategyTag": strategy_tag,
            "ProductType": product_type,
            "OptionsType": options_type,
            "ScheduleTime": schedule_time
        }
        
        result = self.client.request("MappedOrderSch", params)
        return int(result) if result else 0


# =============================================================================
# PASSIVE TRADING MODULE
# =============================================================================

class StoxxoPassiveTrading:
    """
    Handles passive bridge trading operations
    Direct order placement without symbol mapping
    """
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def place_order(self,
                   unique_id: int,
                   strategy_tag: str,
                   user_id: str,
                   exchange: Union[str, Exchange],
                   symbol: str,
                   transaction_type: Union[str, TransactionType],
                   order_type: Union[str, OrderType],
                   validity: str = "DAY",
                   product_type: Union[str, ProductType] = "MIS",
                   qty: int = 1,
                   price: float = 0,
                   trigger_price: float = 0,
                   profit_value: str = "0",
                   stoploss_value: str = "0",
                   sl_trailing_value: str = "0",
                   disclosed_quantity: int = 0,
                   signal_ltp: float = 0,
                   data_provider: str = "") -> int:
        """
        Place order directly without symbol mapping
        
        Args:
            unique_id: Unique order identifier
            strategy_tag: Strategy identifier
            user_id: User ID (empty for first user)
            exchange: NSE, NFO, BSE, CDS, MCX
            symbol: Trading symbol
            transaction_type: BUY, SELL
            order_type: MARKET, LIMIT, SL, SL-M
            validity: DAY, IOC
            product_type: MIS, CNC, NRML, BO, CO
            qty: Order quantity
            price: Limit price
            trigger_price: SL trigger price
            profit_value: Target as points or percentage
            stoploss_value: SL as points or percentage
            sl_trailing_value: Trailing SL as points or percentage
            disclosed_quantity: Disclosed quantity
            signal_ltp: Signal LTP
            data_provider: Data provider identifier
            
        Returns:
            Request ID
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        if isinstance(transaction_type, TransactionType):
            # Convert LE/SE to BUY/SELL for passive trading
            transaction_type = "BUY" if transaction_type.value in ["LE"] else "SELL"
        if isinstance(order_type, OrderType):
            order_type = order_type.value
        if isinstance(product_type, ProductType):
            product_type = product_type.value
        
        params = {
            "UniqueID": unique_id,
            "StrategyTag": strategy_tag,
            "UserID": user_id,
            "Exchange": exchange,
            "Symbol": symbol,
            "TransactionType": transaction_type,
            "OrderType": order_type,
            "Validity": validity,
            "ProductType": product_type,
            "Qty": qty,
            "Price": price,
            "TriggerPrice": trigger_price,
            "ProfitValue": profit_value,
            "StoplossValue": stoploss_value,
            "SLTrailingValue": sl_trailing_value,
            "DisclosedQuantity": disclosed_quantity,
            "SignalLTP": signal_ltp,
            "DataProvider": data_provider
        }
        
        result = self.client.request("PlaceOrder", params)
        return int(result) if result else 0
    
    def place_order_advanced(self,
                           unique_id: int,
                           strategy_tag: str,
                           user_id: str,
                           exchange: Union[str, Exchange],
                           symbol: str,
                           transaction_type: Union[str, TransactionType],
                           order_type: Union[str, OrderType],
                           validity: str = "DAY",
                           product_type: Union[str, ProductType] = "MIS",
                           qty: int = 1,
                           price: float = 0,
                           trigger_price: float = 0,
                           profit_value: str = "0",
                           stoploss_value: str = "0",
                           sl_trailing_value: str = "0",
                           disclosed_quantity: int = 0,
                           data_provider: str = "",
                           tgt_trailing_value: str = "0",
                           break_even_point: str = "0",
                           signal_ltp: float = 0,
                           max_ltp_difference: str = "0",
                           price_spread: str = "0",
                           trigger_spread: str = "0",
                           cancel_if_not_complete_seconds: int = 0) -> int:
        """
        Place advanced order with all parameters
        
        Args:
            unique_id: Unique order identifier
            strategy_tag: Strategy identifier
            user_id: User ID
            exchange: Exchange
            symbol: Trading symbol
            transaction_type: BUY, SELL
            order_type: Order type
            validity: Order validity
            product_type: Product type
            qty: Quantity
            price: Limit price
            trigger_price: SL trigger
            profit_value: Target
            stoploss_value: Stop loss
            sl_trailing_value: Trailing SL
            disclosed_quantity: Disclosed qty
            data_provider: Data provider
            tgt_trailing_value: Target trailing
            break_even_point: Break even point
            signal_ltp: Signal LTP
            max_ltp_difference: Max LTP difference
            price_spread: Price spread
            trigger_spread: Trigger spread
            cancel_if_not_complete_seconds: Auto cancel time
            
        Returns:
            Request ID
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        if isinstance(transaction_type, TransactionType):
            transaction_type = "BUY" if transaction_type.value in ["LE"] else "SELL"
        if isinstance(order_type, OrderType):
            order_type = order_type.value
        if isinstance(product_type, ProductType):
            product_type = product_type.value
        
        params = {
            "UniqueID": unique_id,
            "StrategyTag": strategy_tag,
            "UserID": user_id,
            "Exchange": exchange,
            "Symbol": symbol,
            "TransactionType": transaction_type,
            "OrderType": order_type,
            "Validity": validity,
            "ProductType": product_type,
            "Qty": qty,
            "Price": price,
            "TriggerPrice": trigger_price,
            "ProfitValue": profit_value,
            "StoplossValue": stoploss_value,
            "SLTrailingValue": sl_trailing_value,
            "DisclosedQuantity": disclosed_quantity,
            "DataProvider": data_provider,
            "TgtTrailingValue": tgt_trailing_value,
            "BreakEvenPoint": break_even_point,
            "SignalLTP": signal_ltp,
            "MaxLTPDifference": max_ltp_difference,
            "PriceSpread": price_spread,
            "TriggerSpread": trigger_spread,
            "CancelIfNotCompleteInSeconds": cancel_if_not_complete_seconds
        }
        
        result = self.client.request("PlaceOrderAdv", params)
        return int(result) if result else 0


# =============================================================================
# ORDER MANAGEMENT MODULE
# =============================================================================

class StoxxoOrderManagement:
    """Handles order modification and cancellation operations"""
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def modify_order(self,
                    request_id: int,
                    qty: int = 0,
                    price: float = 0,
                    trigger_price: float = 0,
                    profit_value: str = "0",
                    stoploss_value: str = "0",
                    sl_trailing_value: str = "0",
                    tgt_trailing_value: str = "0",
                    break_even_point: str = "0") -> bool:
        """
        Modify existing order parameters
        
        Args:
            request_id: Request ID or unique ID
            qty: New quantity
            price: New price
            trigger_price: New trigger price
            profit_value: New target
            stoploss_value: New stop loss
            sl_trailing_value: New trailing SL
            tgt_trailing_value: New target trailing
            break_even_point: New break even point
            
        Returns:
            True if successful
        """
        params = {
            "RequestID": request_id,
            "Qty": qty,
            "Price": price,
            "TriggerPrice": trigger_price,
            "ProfitValue": profit_value,
            "StoplossValue": stoploss_value,
            "SLTrailingValue": sl_trailing_value,
            "TgtTrailingValue": tgt_trailing_value,
            "BreakEvenPoint": break_even_point
        }
        
        result = self.client.request("ModifyOrder", params)
        return bool(result)
    
    def cancel_or_exit_order(self, request_id: int) -> bool:
        """
        Cancel open order or exit executed order
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            True if successful
        """
        params = {"RequestID": request_id}
        result = self.client.request("CancelOrExitOrder", params)
        return bool(result)
    
    def convert_to_market(self, request_id: int, retry: int = 0) -> bool:
        """
        Convert order to market order
        
        Args:
            request_id: Request ID or unique ID
            retry: Number of retries (0 for single attempt)
            
        Returns:
            True if successful
        """
        params = {
            "RequestID": request_id,
            "Retry": retry
        }
        result = self.client.request("ConvertToMarket", params)
        return bool(result)


# =============================================================================
# POSITION MANAGEMENT MODULE
# =============================================================================

class StoxxoPositionManagement:
    """Handles position and margin operations"""
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def square_off(self, user_id: str = "") -> bool:
        """
        Square off all positions for a user
        
        Args:
            user_id: User ID (empty for first user, "ALL" for all users)
            
        Returns:
            True if successful
        """
        params = {"UserID": user_id} if user_id else {}
        result = self.client.request("SquareOff", params)
        return bool(result)
    
    def square_off_all(self) -> bool:
        """
        Square off all positions for all users
        
        Returns:
            True if successful
        """
        result = self.client.request("SquareOffAll")
        return bool(result)
    
    def square_off_strategy(self, strategy_tag: str) -> bool:
        """
        Square off all positions for a strategy
        
        Args:
            strategy_tag: Strategy identifier
            
        Returns:
            True if successful
        """
        params = {"StrategyTag": strategy_tag}
        result = self.client.request("SquareOffStrategy", params)
        return bool(result)
    
    def get_mtm(self, user_id: str = "") -> Optional[float]:
        """
        Get Mark-to-Market for user
        
        Args:
            user_id: User ID (empty for first user)
            
        Returns:
            MTM value or None
        """
        params = {"UserID": user_id} if user_id else {}
        result = self.client.request("MTM", params)
        return self.client.processor.parse_numeric(result)
    
    def get_available_margin(self, user_id: str = "") -> Optional[float]:
        """
        Get available margin for user
        
        Args:
            user_id: User ID (empty for first user)
            
        Returns:
            Available margin or None
        """
        params = {"UserID": user_id} if user_id else {}
        result = self.client.request("AvailableMargin", params)
        return self.client.processor.parse_numeric(result)
    
    def get_available_margin_commodity(self, user_id: str = "") -> Optional[float]:
        """
        Get available commodity margin for user
        
        Args:
            user_id: User ID (empty for first user)
            
        Returns:
            Available commodity margin or None
        """
        params = {"UserID": user_id} if user_id else {}
        result = self.client.request("AvailableMarginCommodity", params)
        return self.client.processor.parse_numeric(result)


# =============================================================================
# MARKET DATA MODULE
# =============================================================================

class StoxxoMarketData:
    """Handles market data operations"""
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def subscribe(self, 
                 exchange: Union[str, Exchange], 
                 symbol: str, 
                 data_provider: str = "") -> None:
        """
        Subscribe to market data for symbol
        
        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            data_provider: Data provider
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        
        params = {
            "Exchange": exchange,
            "Symbol": symbol,
            "DataProvider": data_provider
        }
        self.client.request("Subscribe", params)
    
    def get_ltp(self, 
               exchange: Union[str, Exchange], 
               symbol: str, 
               data_provider: str = "") -> Optional[float]:
        """
        Get Last Traded Price
        
        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            data_provider: Data provider
            
        Returns:
            LTP or None
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        
        params = {
            "Exchange": exchange,
            "Symbol": symbol,
            "DataProvider": data_provider
        }
        result = self.client.request("LTP", params)
        return self.client.processor.parse_numeric(result)
    
    def get_bid(self, 
               exchange: Union[str, Exchange], 
               symbol: str, 
               data_provider: str = "") -> Optional[float]:
        """
        Get Best Bid Price
        
        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            data_provider: Data provider
            
        Returns:
            Bid price or None
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        
        params = {
            "Exchange": exchange,
            "Symbol": symbol,
            "DataProvider": data_provider
        }
        result = self.client.request("BID", params)
        return self.client.processor.parse_numeric(result)
    
    def get_ask(self, 
               exchange: Union[str, Exchange], 
               symbol: str, 
               data_provider: str = "") -> Optional[float]:
        """
        Get Best Ask Price
        
        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            data_provider: Data provider
            
        Returns:
            Ask price or None
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        
        params = {
            "Exchange": exchange,
            "Symbol": symbol,
            "DataProvider": data_provider
        }
        result = self.client.request("ASK", params)
        return self.client.processor.parse_numeric(result)
    
    def feed_ltp(self, 
                exchange: Union[str, Exchange], 
                symbol: str, 
                data_provider: str, 
                ltp: float, 
                bid: float, 
                ask: float) -> None:
        """
        Feed custom LTP data to bridge
        
        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            data_provider: Data provider
            ltp: Last traded price
            bid: Bid price
            ask: Ask price
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        
        params = {
            "Exchange": exchange,
            "Symbol": symbol,
            "DataProvider": data_provider,
            "LTP": ltp,
            "BID": bid,
            "ASK": ask
        }
        self.client.request("FeedLTP", params)
    
    def get_market_data(self, 
                       exchange: Union[str, Exchange], 
                       symbol: str, 
                       data_provider: str = "") -> MarketData:
        """
        Get complete market data for symbol
        
        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            data_provider: Data provider
            
        Returns:
            MarketData object
        """
        if isinstance(exchange, Exchange):
            exchange = exchange.value
        
        data = MarketData(symbol=symbol)
        data.ltp = self.get_ltp(exchange, symbol, data_provider)
        data.bid = self.get_bid(exchange, symbol, data_provider)
        data.ask = self.get_ask(exchange, symbol, data_provider)
        data.timestamp = datetime.now()
        
        return data


# =============================================================================
# ORDER INFORMATION MODULE
# =============================================================================

class StoxxoOrderInfo:
    """Handles order information and status operations"""
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def get_order_id(self, request_id: int) -> Optional[str]:
        """
        Get broker order ID for request
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            Order ID or None
        """
        params = {"RequestID": request_id}
        result = self.client.request("OrderID", params)
        return result if result else None
    
    def get_last_order_id(self, user_id: str = "") -> Optional[str]:
        """
        Get last order ID for user
        
        Args:
            user_id: User ID (empty for first user)
            
        Returns:
            Order ID or None
        """
        params = {"UserID": user_id} if user_id else {}
        result = self.client.request("LastOrderID", params)
        return result if result else None
    
    def get_order_status(self, request_id: int) -> Optional[str]:
        """
        Get order status
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            Status: open, completed, rejected, cancelled
        """
        params = {"RequestID": request_id}
        result = self.client.request("OrderStatus", params)
        return result if result else None
    
    def get_order_quantity(self, request_id: int) -> Optional[int]:
        """
        Get order quantity
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            Order quantity or None
        """
        params = {"RequestID": request_id}
        result = self.client.request("OrderQty", params)
        return int(result) if result else None
    
    def get_filled_quantity(self, request_id: int) -> Optional[int]:
        """
        Get filled quantity
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            Filled quantity or None
        """
        params = {"RequestID": request_id}
        result = self.client.request("OrderFilledQty", params)
        return int(result) if result else None
    
    def get_average_price(self, request_id: int) -> Optional[float]:
        """
        Get average execution price
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            Average price or None
        """
        params = {"RequestID": request_id}
        result = self.client.request("OrderAvgPrice", params)
        return self.client.processor.parse_numeric(result)
    
    def is_order_open(self, request_id: int) -> bool:
        """
        Check if order is open
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            True if order is open
        """
        params = {"RequestID": request_id}
        result = self.client.request("IsOrderOpen", params)
        return bool(result)
    
    def is_order_completed(self, request_id: int) -> bool:
        """
        Check if order is completed
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            True if order is completed
        """
        params = {"RequestID": request_id}
        result = self.client.request("IsOrderCompleted", params)
        return bool(result)
    
    def is_order_rejected(self, request_id: int) -> bool:
        """
        Check if order is rejected
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            True if order is rejected
        """
        params = {"RequestID": request_id}
        result = self.client.request("IsOrderRejected", params)
        return bool(result)
    
    def is_order_cancelled(self, request_id: int) -> bool:
        """
        Check if order is cancelled
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            True if order is cancelled
        """
        params = {"RequestID": request_id}
        result = self.client.request("IsOrderCancelled", params)
        return bool(result)
    
    def get_order_details(self, request_id: int) -> OrderData:
        """
        Get complete order details
        
        Args:
            request_id: Request ID or unique ID
            
        Returns:
            OrderData object with all available information
        """
        data = OrderData(request_id=request_id)
        
        try:
            data.order_id = self.get_order_id(request_id)
            data.status = self.get_order_status(request_id)
            data.quantity = self.get_order_quantity(request_id)
            data.filled_quantity = self.get_filled_quantity(request_id)
            data.average_price = self.get_average_price(request_id)
        except Exception as e:
            data.error = str(e)
        
        return data


# =============================================================================
# MULTI-LEG OPTIONS MODULE
# =============================================================================

class StoxxoMultiLeg:
    """Handles multi-leg options portfolio operations"""
    
    def __init__(self, client: StoxxoClient):
        self.client = client
    
    def place_multi_leg_order(self,
                             portfolio_name: str,
                             strategy_tag: str,
                             symbol: str,
                             product: Union[str, ProductType],
                             lots: int,
                             no_duplicate_seconds: int = 0) -> str:
        """
        Place basic multi-leg order
        
        Args:
            portfolio_name: Name of options strategy
            strategy_tag: Strategy identifier
            symbol: Underlying symbol (NIFTY, BANKNIFTY, etc.)
            product: MIS, NRML
            lots: Number of lots
            no_duplicate_seconds: Duplicate prevention time
            
        Returns:
            Portfolio name for tracking
        """
        if isinstance(product, ProductType):
            product = product.value
        
        params = {
            "OptionPortfolioName": portfolio_name,
            "StrategyTag": strategy_tag,
            "Symbol": symbol,
            "Product": product,
            "Lots": lots,
            "NoDuplicateOrderForSeconds": no_duplicate_seconds
        }
        
        result = self.client.request("PlaceMultiLegOrder", params)
        return str(result) if result else ""
    
    def place_multi_leg_order_advanced(self,
                                      portfolio_name: str,
                                      strategy_tag: str,
                                      symbol: str,
                                      product: Union[str, ProductType],
                                      lots: int,
                                      combined_profit: str = "0",
                                      combined_loss: str = "0",
                                      leg_target: str = "0",
                                      leg_sl: str = "0",
                                      no_duplicate_seconds: int = 0,
                                      entry_price: float = 0,
                                      sl_to_cost: bool = False) -> str:
        """
        Place advanced multi-leg order with all parameters
        
        Args:
            portfolio_name: Name of options strategy
            strategy_tag: Strategy identifier
            symbol: Underlying symbol
            product: MIS, NRML
            lots: Number of lots
            combined_profit: Combined profit target (points or %)
            combined_loss: Combined loss limit (points or %)
            leg_target: Individual leg target (points or %)
            leg_sl: Individual leg stop loss (points or %)
            no_duplicate_seconds: Duplicate prevention time
            entry_price: Entry price based on combined premium
            sl_to_cost: Move SL to cost on target hit
            
        Returns:
            Portfolio name for tracking
        """
        if isinstance(product, ProductType):
            product = product.value
        
        params = {
            "OptionPortfolioName": portfolio_name,
            "StrategyTag": strategy_tag,
            "Symbol": symbol,
            "Product": product,
            "Lots": lots,
            "CombinedProfit": combined_profit,
            "CombinedLoss": combined_loss,
            "LegTarget": leg_target,
            "LegSL": leg_sl,
            "NoDuplicateOrderForSeconds": no_duplicate_seconds,
            "EntryPrice": entry_price,
            "SLtoCost": 1 if sl_to_cost else 0
        }
        
        result = self.client.request("PlaceMultiLegOrderAdv", params)
        return str(result) if result else ""
    
    def exit_multi_leg_order(self, portfolio_name: str) -> bool:
        """
        Exit multi-leg portfolio by name
        
        Args:
            portfolio_name: Portfolio name from place order
            
        Returns:
            True if successful
        """
        params = {"OptionPortfolioName": portfolio_name}
        result = self.client.request("ExitMultiLegOrder", params)
        return bool(result)
    
    def exit_multi_leg_by_details(self,
                                 portfolio_name: str,
                                 strategy_tag: str,
                                 symbol: str,
                                 product: Union[str, ProductType],
                                 lots: int) -> bool:
        """
        Exit multi-leg portfolio by details (FIFO)
        
        Args:
            portfolio_name: Options strategy name
            strategy_tag: Strategy identifier
            symbol: Underlying symbol
            product: MIS, NRML
            lots: Number of lots
            
        Returns:
            True if successful
        """
        if isinstance(product, ProductType):
            product = product.value
        
        params = {
            "OptionPortfolioName": portfolio_name,
            "StrategyTag": strategy_tag,
            "Symbol": symbol,
            "Product": product,
            "Lots": lots
        }
        
        result = self.client.request("ExitMultiLegOrderByDetails", params)
        return bool(result)
    
    def get_combined_premium(self, portfolio_name: str) -> Optional[float]:
        """
        Get combined premium of portfolio
        
        Args:
            portfolio_name: Portfolio name
            
        Returns:
            Combined premium or None
        """
        params = {"OptionPortfolioName": portfolio_name}
        result = self.client.request("CombinedPremium", params)
        return self.client.processor.parse_numeric(result)
    
    def get_portfolio_mtm(self, portfolio_name: str) -> Optional[float]:
        """
        Get portfolio MTM
        
        Args:
            portfolio_name: Portfolio name
            
        Returns:
            Portfolio MTM or None
        """
        params = {"OptionPortfolioName": portfolio_name}
        result = self.client.request("PortfolioMTM", params)
        return self.client.processor.parse_numeric(result)
    
    def get_portfolio_status(self, portfolio_name: str) -> Optional[str]:
        """
        Get portfolio status
        
        Args:
            portfolio_name: Portfolio name
            
        Returns:
            Status: Disabled, Stopped, Pending, Monitoring, Started, 
                   UnderExecution, Failed, Rejected, Completed, UnderExit
        """
        params = {"OptionPortfolioName": portfolio_name}
        result = self.client.request("PortfolioStatus", params)
        return result if result else None
    
    def get_portfolio_legs(self, portfolio_name: str, all_legs: bool = True) -> Optional[str]:
        """
        Get portfolio legs information
        
        Args:
            portfolio_name: Portfolio name
            all_legs: Include all legs (True) or only active legs (False)
            
        Returns:
            Legs information string or None
        """
        params = {
            "OptionPortfolioName": portfolio_name,
            "All": "Yes" if all_legs else "No"
        }
        result = self.client.request("PortfolioLegs", params)
        return result if result else None
    
    def get_portfolio_data(self, portfolio_name: str) -> PortfolioData:
        """
        Get complete portfolio data
        
        Args:
            portfolio_name: Portfolio name
            
        Returns:
            PortfolioData object with all available information
        """
        data = PortfolioData(name=portfolio_name)
        
        try:
            data.mtm = self.get_portfolio_mtm(portfolio_name)
            data.status = self.get_portfolio_status(portfolio_name)
            data.premium = self.get_combined_premium(portfolio_name)
            data.legs = self.get_portfolio_legs(portfolio_name)
        except Exception as e:
            data.error = str(e)
        
        return data
    
    # Advanced portfolio management methods
    def add_leg(self, portfolio_name: str, leg_details: str) -> bool:
        """
        Add leg to existing portfolio
        
        Args:
            portfolio_name: Portfolio name
            leg_details: Leg specification string
            
        Returns:
            True if successful
        """
        params = {
            "OptionPortfolioName": portfolio_name,
            "Leg": leg_details
        }
        result = self.client.request("AddLeg", params)
        return bool(result)
    
    def square_off_leg(self, portfolio_name: str, leg_identifier: str) -> bool:
        """
        Square off specific leg
        
        Args:
            portfolio_name: Portfolio name
            leg_identifier: Leg identification string
            
        Returns:
            True if successful
        """
        params = {
            "OptionPortfolioName": portfolio_name,
            "Leg": leg_identifier
        }
        result = self.client.request("SqOffLeg", params)
        return bool(result)
    
    def modify_portfolio(self, 
                        portfolio_name: str, 
                        field: str, 
                        value: str, 
                        leg_identifier: str = "") -> bool:
        """
        Modify portfolio parameters
        
        Args:
            portfolio_name: Portfolio name
            field: Field to modify (CombinedSL, CombinedTgt, LegSL, LegTgt)
            value: New value (points or percentage)
            leg_identifier: Specific leg (optional)
            
        Returns:
            True if successful
        """
        params = {
            "OptionPortfolioName": portfolio_name,
            "OptField": field,
            "Data": value,
            "Leg": leg_identifier
        }
        result = self.client.request("ModifyPortfolio", params)
        return bool(result)


# =============================================================================
# SYSTEM INFORMATION MODULE (INTEGRATED FROM CODE 2)
# =============================================================================

class StoxxoSystemInfo:
    """
    Handles system-level information endpoints:
    - /Users
    - /Positions  
    - /OrderBook
    """
    
    def __init__(self, client: StoxxoClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
    
    # =========================================================================
    # USERS ENDPOINT
    # =========================================================================
    
    def get_users(self, user_id: str = "") -> List[Dict[str, Any]]:
        """
        Get all users or specific user details from Stoxxo
        
        Args:
            user_id: Specific user ID (empty for all users)
            
        Returns:
            List of user dictionaries with parsed data
            
        Response Format (pipe-separated):
        Enabled | User ID | LoggedIn | MTM | MIS MTM | NRML MTM | Available Margin |
        Market Orders Allowed | User Alias | Broker | SqOff Time | Is Square Off Done |
        Max Profit | Max Loss | Qty Multiplier | Utilized Margin |
        Open Nifty Delta | Open BankNifty Delta | Open Sensex Delta
        """
        params = {"User": user_id} if user_id else {}
        
        try:
            result = self.client.request("Users", params)
            return self._parse_users_response(result)
        except Exception as e:
            self.logger.error("Error fetching users: %s", e)
            return []
    
    def _parse_users_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse pipe-separated user data"""
        if not response:
            return []
        
        users = []
        # Split by tilde for multiple users
        user_records = str(response).split('~')
        
        for record in user_records:
            record = record.strip()
            if not record:
                continue
            
            fields = record.split('|')
            if len(fields) < 19:
                self.logger.warning("Incomplete user record: %s", record)
                continue
            
            try:
                user_data = {
                    'enabled': fields[0].strip().lower() == 'true',
                    'user_id': fields[1].strip(),
                    'logged_in': fields[2].strip().lower() == 'true',
                    'mtm': self._safe_float(fields[3]),
                    'mis_mtm': self._safe_float(fields[4]),
                    'nrml_mtm': self._safe_float(fields[5]),
                    'available_margin': self._safe_float(fields[6]),
                    'market_orders_allowed': fields[7].strip().lower() == 'true',
                    'user_alias': fields[8].strip(),
                    'broker': fields[9].strip(),
                    'sqoff_time': fields[10].strip(),
                    'is_square_off_done': fields[11].strip().lower() == 'true',
                    'max_profit': self._safe_float(fields[12]),
                    'max_loss': self._safe_float(fields[13]),
                    'qty_multiplier': self._safe_float(fields[14]),
                    'utilized_margin': self._safe_float(fields[15]),
                    'open_nifty_delta': self._safe_float(fields[16]),
                    'open_banknifty_delta': self._safe_float(fields[17]),
                    'open_sensex_delta': self._safe_float(fields[18])
                }
                
                users.append(user_data)
            except Exception as e:
                self.logger.error("Error parsing user record: %s", e)
                continue
        
        return users
    
    # =========================================================================
    # POSITIONS ENDPOINT
    # =========================================================================
    
    def get_positions(self, user_id: str = "") -> List[Dict[str, Any]]:
        """
        Get all positions from Stoxxo
        
        Args:
            user_id: Specific user ID (empty for all users)
            
        Returns:
            List of position dictionaries
            
        Response Format (pipe-separated):
        Product | Exchange | Symbol | Net Qty | LTP | P&L | P&L % | Buy Qty |
        Buy Avg Price | Buy Value | Sell Qty | Sell Avg Price | Sell Value |
        Carry Fwd Qty | Realized Profit | Unrealized Profit | UserID | Delta
        """
        params = {"User": user_id} if user_id else {}
        
        try:
            result = self.client.request("Positions", params)
            return self._parse_positions_response(result)
        except Exception as e:
            self.logger.error("Error fetching positions: %s", e)
            return []
    
    def _parse_positions_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse pipe-separated positions data"""
        if not response:
            return []
        
        positions = []
        position_records = str(response).split('~')
        
        for record in position_records:
            record = record.strip()
            if not record:
                continue
            
            fields = record.split('|')
            if len(fields) < 18:
                self.logger.warning("Incomplete position record: %s", record)
                continue
            
            try:
                position = {
                    'product': fields[0].strip(),
                    'exchange': fields[1].strip(),
                    'symbol': fields[2].strip(),
                    'net_qty': self._safe_int(fields[3]),
                    'ltp': self._safe_float(fields[4]),
                    'pnl': self._safe_float(fields[5]),
                    'pnl_percent': self._safe_float(fields[6]),
                    'buy_qty': self._safe_int(fields[7]),
                    'buy_avg_price': self._safe_float(fields[8]),
                    'buy_value': self._safe_float(fields[9]),
                    'sell_qty': self._safe_int(fields[10]),
                    'sell_avg_price': self._safe_float(fields[11]),
                    'sell_value': self._safe_float(fields[12]),
                    'carry_fwd_qty': self._safe_int(fields[13]),
                    'realized_profit': self._safe_float(fields[14]),
                    'unrealized_profit': self._safe_float(fields[15]),
                    'user_id': fields[16].strip(),
                    'delta': self._safe_float(fields[17])
                }
                
                positions.append(position)
            except Exception as e:
                self.logger.error("Error parsing position record: %s", e)
                continue
        
        return positions
    
    # =========================================================================
    # ORDER BOOK ENDPOINT
    # =========================================================================
    
    def get_order_book(self, user_id: str = "", ignore_rejected: bool = True) -> List[Dict[str, Any]]:
        """
        Get complete order book from Stoxxo
        
        Args:
            user_id: Specific user ID (empty for all users)
            ignore_rejected: If True, exclude rejected/cancelled orders
            
        Returns:
            List of order dictionaries
            
        Response Format (pipe-separated):
        Symbol | Exchange | Order Time | Order ID | Txn | Avg Price | Quantity |
        Filled Quantity | Order Type | Limit Price | Trigger Price | Exchange Time |
        Exchg Order ID | Product | Validity | Status | User ID | Status Message | Tag
        """
        params = {}
        if user_id:
            params["User"] = user_id
        if ignore_rejected:
            params["IgnoreRejected"] = "True"
        
        try:
            result = self.client.request("OrderBook", params)
            return self._parse_order_book_response(result)
        except Exception as e:
            self.logger.error("Error fetching order book: %s", e)
            return []
    
    def _parse_order_book_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse pipe-separated order book data"""
        if not response:
            return []
        
        orders = []
        order_records = str(response).split('~')
        
        for record in order_records:
            record = record.strip()
            if not record:
                continue
            
            fields = record.split('|')
            if len(fields) < 19:
                self.logger.warning("Incomplete order record: %s", record)
                continue
            
            try:
                order = {
                    'symbol': fields[0].strip(),
                    'exchange': fields[1].strip(),
                    'order_time': fields[2].strip(),
                    'order_id': fields[3].strip(),
                    'transaction_type': fields[4].strip(),
                    'avg_price': self._safe_float(fields[5]),
                    'quantity': self._safe_int(fields[6]),
                    'filled_quantity': self._safe_int(fields[7]),
                    'order_type': fields[8].strip(),
                    'limit_price': self._safe_float(fields[9]),
                    'trigger_price': self._safe_float(fields[10]),
                    'exchange_time': fields[11].strip(),
                    'exchange_order_id': fields[12].strip(),
                    'product': fields[13].strip(),
                    'validity': fields[14].strip(),
                    'status': fields[15].strip(),
                    'user_id': fields[16].strip(),
                    'status_message': fields[17].strip(),
                    'tag': fields[18].strip()
                }
                
                orders.append(order)
            except Exception as e:
                self.logger.error("Error parsing order record: %s", e)
                continue
        
        return orders
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert string to float"""
        try:
            cleaned = str(value).strip()
            if not cleaned or cleaned == '-':
                return 0.0
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0
    
    def _safe_int(self, value: Any) -> int:
        """Safely convert string to int"""
        try:
            cleaned = str(value).strip()
            if not cleaned or cleaned == '-':
                return 0
            return int(float(cleaned))  # Handle "10.0" format
        except (ValueError, AttributeError):
            return 0


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_client(config: Optional[StoxxoConfig] = None) -> StoxxoClient:
    """
    Create and return configured Stoxxo client
    
    Args:
        config: Optional configuration
        
    Returns:
        Configured StoxxoClient instance
    """
    return StoxxoClient(config)


def quick_status_check(ports: List[int] = None) -> bool:
    """
    Quick connectivity check
    
    Args:
        ports: Ports to test (optional)
        
    Returns:
        True if any port is accessible
    """
    if ports is None:
        ports = [21000, 80]
    
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/Ping", timeout=5)
            if response.status_code == 200:
                return True
        except:
            continue
    
    return False


# =============================================================================
# EXPORT ALL PUBLIC CLASSES AND FUNCTIONS
# =============================================================================

__all__ = [
    # Main client
    'StoxxoClient',
    'create_client',
    
    # Configuration and data models
    'StoxxoConfig',
    'OrderData',
    'PortfolioData',
    'MarketData',
    
    # Enums
    'TransactionType',
    'OrderType',
    'ProductType',
    'Exchange',
    
    # Exceptions
    'StoxxoException',
    'StoxxoConnectionError',
    'StoxxoAPIError',
    'StoxxoOrderError',
    'StoxxoParsingError',
    
    # Functional modules
    'StoxxoStatus',
    'StoxxoActiveTrading',
    'StoxxoPassiveTrading',
    'StoxxoOrderManagement',
    'StoxxoPositionManagement',
    'StoxxoMarketData',
    'StoxxoOrderInfo',
    'StoxxoMultiLeg',
    'StoxxoSystemInfo',
    
    # Utilities
    'quick_status_check'
]


if __name__ == "__main__":
    # Example usage and testing
    print("Stoxxo Complete Library - Testing Basic Connectivity")
    print("=" * 60)
    
    if quick_status_check():
        print("[OK] Stoxxo bridge is accessible")
        
        # Create client and test basic functions
        client = create_client()
        
        if client.status.ping():
            print("[OK] Bridge is running and trading is active")
            
            # Test system info
            try:
                users = client.system_info.get_users()
                print(f"[OK] Found {len(users)} user(s)")
                
                positions = client.system_info.get_positions()
                print(f"[OK] Found {len(positions)} position(s)")
                
                orders = client.system_info.get_order_book()
                print(f"[OK] Found {len(orders)} order(s)")
            except Exception as e:
                print(f"[INFO] System info test: {e}")
            
            # Test market data (example)
            try:
                ltp = client.market_data.get_ltp("NSE", "SBIN")
                if ltp:
                    print(f"[OK] SBIN LTP: Rs.{ltp}")
                else:
                    print("[INFO] No market data available for SBIN")
            except Exception as e:
                print(f"[INFO] Market data test: {e}")
        else:
            print("[ERROR] Bridge ping failed - trading may be stopped")
    else:
        print("[ERROR] Cannot connect to Stoxxo bridge")
        print("        Make sure Stoxxo is running and accessible on ports 21000 or 80")