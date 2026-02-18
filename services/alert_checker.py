"""
Alert Checker
Checks user position data against configured thresholds
Implements 5-minute cooldown per user per alert type
"""
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from models.position_summary import OptionsPositionSummary


@dataclass
class AlertEvent:
    """Represents a triggered alert"""
    user_alias: str
    alert_type: str  # 'mtm_above', 'mtm_below', 'roi_above', etc.
    metric_name: str  # Human-readable name
    threshold: float
    actual_value: float
    timestamp: float
    
    def format_message(self) -> str:
        """Format alert as Telegram message"""
        # Category emojis and labels
        if 'mtm' in self.alert_type or 'roi' in self.alert_type:
            category_emoji = '📈'
            category = 'MTM ALERT' if 'mtm' in self.alert_type else 'ROI ALERT'
        elif 'margin' in self.alert_type:
            category_emoji = '⚠️'
            category = 'MARGIN ALERT'
        else:
            category_emoji = '📊'
            category = 'QUANTITY ALERT'

        # Format values based on type
        if 'margin' in self.alert_type:
            threshold_str = f"{self.threshold:.1f}%"
            actual_str    = f"{self.actual_value:.1f}%"
        elif 'roi' in self.alert_type:
            threshold_str = f"{self.threshold:.2f}%"
            actual_str    = f"{self.actual_value:.2f}%"
        elif any(x in self.alert_type for x in ['calls', 'puts']):
            threshold_str = f"{int(self.threshold)}"
            actual_str    = f"{int(self.actual_value)}"
        else:
            # MTM — Indian Rupee, comma-formatted
            threshold_str = f"₹{self.threshold:,.2f}"
            actual_str    = f"₹{self.actual_value:,.2f}"

        lines = [
            f"{category_emoji} {category}",
            f"User Alias: {self.user_alias}",
            f"Metric: {self.metric_name}",
            f"Threshold: {threshold_str}",
            f"Actual: {actual_str}",
        ]

        return "\n".join(lines)


class AlertChecker:
    """
    Checks position data against user-configured thresholds
    Implements 5-minute cooldown to prevent spam
    """
    
    def __init__(self):
        """Initialize alert checker"""
        self.logger = logging.getLogger(__name__)
        
        # Cooldown tracking: {user_alias: {alert_type: last_trigger_time}}
        self._cooldowns = {}
        self.cooldown_seconds = 300  # 5 minutes
    
    def check_all_alerts(self, 
                        summaries: List[OptionsPositionSummary],
                        mtm_roi_thresholds: Dict,
                        margin_thresholds: Dict,
                        quantity_thresholds: Dict) -> List[AlertEvent]:
        """
        Check all position summaries against all thresholds
        
        Args:
            summaries: List of OptionsPositionSummary objects
            mtm_roi_thresholds: Dict {user_alias: {mtm_above, mtm_below, roi_above, roi_below}}
            margin_thresholds: Dict {user_alias: margin_percent}
            quantity_thresholds: Dict {user_alias: {calls_sell, puts_sell, ...}}
            
        Returns:
            List[AlertEvent]: Triggered alerts (after cooldown filtering)
        """
        alerts = []
        
        for summary in summaries:
            user_alias = summary.user_alias
            
            # Check MTM/ROI thresholds
            if user_alias in mtm_roi_thresholds:
                thresholds = mtm_roi_thresholds[user_alias]
                alerts.extend(self._check_mtm_roi(summary, thresholds))
            
            # Check margin thresholds
            if user_alias in margin_thresholds:
                threshold = margin_thresholds[user_alias]
                if threshold:  # Not empty
                    alert = self._check_margin(summary, threshold)
                    if alert:
                        alerts.append(alert)
            
            # Check quantity thresholds
            if user_alias in quantity_thresholds:
                thresholds = quantity_thresholds[user_alias]
                alerts.extend(self._check_quantities(summary, thresholds))
        
        # Filter by cooldown
        filtered_alerts = self._apply_cooldown(alerts)
        
        return filtered_alerts
    
    def _check_mtm_roi(self, summary: OptionsPositionSummary, 
                       thresholds: Dict) -> List[AlertEvent]:
        """
        Check MTM and ROI% thresholds
        
        Args:
            summary: Position summary
            thresholds: {mtm_above, mtm_below, roi_above, roi_below}
            
        Returns:
            List[AlertEvent]: Triggered alerts
        """
        alerts = []
        current_time = time.time()
        
        mtm = summary.live_pnl
        
        # Calculate ROI%
        # ROI% = (live_pnl / utilized_margin) * 100
        if summary.utilized_margin > 0:
            roi_percent = (mtm / summary.utilized_margin) * 100
        else:
            roi_percent = 0
        
        # Check MTM above
        mtm_above = thresholds.get('mtm_above', '')
        if mtm_above and mtm_above.strip():
            try:
                threshold = float(mtm_above)
                if mtm > threshold:
                    alerts.append(AlertEvent(
                        user_alias=summary.user_alias,
                        alert_type='mtm_above',
                        metric_name='MTM Above Threshold',
                        threshold=threshold,
                        actual_value=mtm,
                        timestamp=current_time
                    ))
            except (ValueError, TypeError):
                pass
        
        # Check MTM below
        mtm_below = thresholds.get('mtm_below', '')
        if mtm_below and mtm_below.strip():
            try:
                threshold = float(mtm_below)
                # Below means negative, so check if mtm < threshold
                if mtm < threshold:
                    alerts.append(AlertEvent(
                        user_alias=summary.user_alias,
                        alert_type='mtm_below',
                        metric_name='MTM Below Threshold',
                        threshold=threshold,
                        actual_value=mtm,
                        timestamp=current_time
                    ))
            except (ValueError, TypeError):
                pass
        
        # Check ROI% above (positive threshold)
        roi_above = thresholds.get('roi_above', '')
        if roi_above and roi_above.strip():
            try:
                threshold = float(roi_above)
                # User enters 5, we check if ROI% > +5%
                if roi_percent > threshold:
                    alerts.append(AlertEvent(
                        user_alias=summary.user_alias,
                        alert_type='roi_above',
                        metric_name='ROI% Above Threshold',
                        threshold=threshold,
                        actual_value=roi_percent,
                        timestamp=current_time
                    ))
            except (ValueError, TypeError):
                pass
        
        # Check ROI% below (negative threshold)
        roi_below = thresholds.get('roi_below', '')
        if roi_below and roi_below.strip():
            try:
                threshold = float(roi_below)
                # User enters 5, we check if ROI% < -5%
                if roi_percent < -threshold:
                    alerts.append(AlertEvent(
                        user_alias=summary.user_alias,
                        alert_type='roi_below',
                        metric_name='ROI% Below Threshold',
                        threshold=-threshold,
                        actual_value=roi_percent,
                        timestamp=current_time
                    ))
            except (ValueError, TypeError):
                pass
        
        return alerts
    
    def _check_margin(self, summary: OptionsPositionSummary, 
                     threshold: str) -> Optional[AlertEvent]:
        """
        Check margin utilization percentage
        
        Args:
            summary: Position summary
            threshold: Margin % threshold (e.g., "85")
            
        Returns:
            AlertEvent or None
        """
        if not threshold or not threshold.strip():
            return None
        
        try:
            threshold_value = float(threshold)
            
            # Calculate utilised margin %
            total_margin = summary.available_margin + summary.utilized_margin
            if total_margin > 0:
                margin_percent = (summary.utilized_margin / total_margin) * 100
            else:
                margin_percent = 0
            
            # Check if above threshold
            if margin_percent > threshold_value:
                return AlertEvent(
                    user_alias=summary.user_alias,
                    alert_type='margin_above',
                    metric_name='Margin Utilization',
                    threshold=threshold_value,
                    actual_value=margin_percent,
                    timestamp=time.time()
                )
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _check_quantities(self, summary: OptionsPositionSummary, 
                         thresholds: Dict) -> List[AlertEvent]:
        """
        Check position quantity thresholds
        
        Args:
            summary: Position summary
            thresholds: {calls_sell, puts_sell, calls_buy, puts_buy, calls_net, puts_net}
            
        Returns:
            List[AlertEvent]: Triggered alerts
        """
        alerts = []
        current_time = time.time()
        
        # Define checks (threshold_key, actual_value, metric_name, use_absolute)
        checks = [
            ('calls_sell', summary.call_sell_qty, 'Calls Sell Quantity', True),
            ('puts_sell', summary.put_sell_qty, 'Puts Sell Quantity', True),
            ('calls_buy', summary.call_buy_qty, 'Calls Buy Quantity', False),
            ('puts_buy', summary.put_buy_qty, 'Puts Buy Quantity', False),
            ('calls_net', summary.calls_net, 'Calls Net Quantity', True),
            ('puts_net', summary.puts_net, 'Puts Net Quantity', True)
        ]
        
        for threshold_key, actual_value, metric_name, use_absolute in checks:
            threshold_str = thresholds.get(threshold_key, '')
            if not threshold_str or not threshold_str.strip():
                continue
            
            try:
                threshold_value = float(threshold_str)
                
                # For sell quantities: use absolute value (user enters positive, we check abs)
                # For net quantities: use absolute value (check both +/- net)
                # For buy quantities: use actual value (already positive)
                
                compare_value = abs(actual_value) if use_absolute else actual_value
                
                if compare_value > threshold_value:
                    alerts.append(AlertEvent(
                        user_alias=summary.user_alias,
                        alert_type=threshold_key,
                        metric_name=metric_name,
                        threshold=threshold_value,
                        actual_value=actual_value,
                        timestamp=current_time
                    ))
            except (ValueError, TypeError):
                pass
        
        return alerts
    
    def _apply_cooldown(self, alerts: List[AlertEvent]) -> List[AlertEvent]:
        """
        Apply 5-minute cooldown filter
        
        Args:
            alerts: List of triggered alerts
            
        Returns:
            List[AlertEvent]: Alerts after cooldown filtering
        """
        filtered = []
        current_time = time.time()
        
        for alert in alerts:
            user_alias = alert.user_alias
            alert_type = alert.alert_type
            
            # Initialize user cooldowns if needed
            if user_alias not in self._cooldowns:
                self._cooldowns[user_alias] = {}
            
            # Check cooldown
            last_trigger = self._cooldowns[user_alias].get(alert_type, 0)
            time_since_last = current_time - last_trigger
            
            if time_since_last >= self.cooldown_seconds:
                # Cooldown expired, allow alert
                filtered.append(alert)
                # Update cooldown
                self._cooldowns[user_alias][alert_type] = current_time
                self.logger.debug(f"Alert triggered: {user_alias} - {alert_type}")
            else:
                # Still in cooldown
                remaining = self.cooldown_seconds - time_since_last
                self.logger.debug(f"Alert suppressed (cooldown): {user_alias} - {alert_type} "
                                f"({remaining:.0f}s remaining)")
        
        return filtered
    
    def clear_cooldowns(self, user_alias: Optional[str] = None):
        """
        Clear cooldown tracking
        
        Args:
            user_alias: Specific user to clear, or None for all users
        """
        if user_alias:
            if user_alias in self._cooldowns:
                del self._cooldowns[user_alias]
                self.logger.info(f"Cleared cooldowns for {user_alias}")
        else:
            self._cooldowns.clear()
            self.logger.info("Cleared all cooldowns")
    
    def get_cooldown_status(self, user_alias: str) -> Dict[str, float]:
        """
        Get remaining cooldown times for a user
        
        Args:
            user_alias: User to check
            
        Returns:
            Dict {alert_type: seconds_remaining}
        """
        if user_alias not in self._cooldowns:
            return {}
        
        current_time = time.time()
        status = {}
        
        for alert_type, last_trigger in self._cooldowns[user_alias].items():
            elapsed = current_time - last_trigger
            remaining = max(0, self.cooldown_seconds - elapsed)
            status[alert_type] = remaining
        
        return status