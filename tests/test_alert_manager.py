"""
Unit tests for AlertManager class
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alert_manager import (
    AlertManager, Alert, AlertRule, AlertType, 
    AlertPriority, AlertChannel, EmailChannel, SMSChannel, DashboardChannel
)


class TestAlert:
    """Test Alert data class"""
    
    def test_alert_creation(self):
        """Test basic alert creation"""
        alert = Alert(
            alert_id="TEST-001",
            alert_type=AlertType.STOCKOUT,
            priority=AlertPriority.HIGH,
            title="Test Alert",
            message="This is a test",
            data={"test": "data"},
            channels=[AlertChannel.EMAIL]
        )
        
        assert alert.alert_id == "TEST-001"
        assert alert.alert_type == AlertType.STOCKOUT
        assert alert.priority == AlertPriority.HIGH
        assert alert.created_at is not None
        assert alert.expires_at is not None
    
    def test_alert_to_dict(self):
        """Test alert dictionary conversion"""
        alert = Alert(
            alert_id="TEST-002",
            alert_type=AlertType.LOW_INVENTORY,
            priority=AlertPriority.MEDIUM,
            title="Test",
            message="Message",
            data={},
            channels=[AlertChannel.DASHBOARD]
        )
        
        alert_dict = alert.to_dict()
        assert alert_dict['alert_id'] == "TEST-002"
        assert alert_dict['alert_type'] == "low_inventory"
        assert alert_dict['priority'] == 2
        assert alert_dict['channels'] == ["dashboard"]


class TestAlertRule:
    """Test AlertRule functionality"""
    
    def test_rule_creation(self):
        """Test rule creation"""
        rule = AlertRule(
            rule_id="RULE-001",
            name="Test Rule",
            condition=lambda data: data.get('value', 0) > 100,
            alert_type=AlertType.STOCKOUT,
            priority=AlertPriority.HIGH,
            channels=[AlertChannel.EMAIL],
            cooldown_minutes=60
        )
        
        assert rule.rule_id == "RULE-001"
        assert rule.enabled is True
        assert rule.cooldown_minutes == 60
    
    def test_rule_condition(self):
        """Test rule condition evaluation"""
        rule = AlertRule(
            rule_id="RULE-002",
            name="Value Check",
            condition=lambda data: data.get('value', 0) > 50,
            alert_type=AlertType.FORECAST_ANOMALY,
            priority=AlertPriority.LOW,
            channels=[AlertChannel.DASHBOARD]
        )
        
        assert rule.condition({'value': 100}) is True
        assert rule.condition({'value': 25}) is False
        assert rule.condition({}) is False


class TestEmailChannel:
    """Test EmailChannel"""
    
    def test_email_channel_validation(self):
        """Test email channel configuration validation"""
        channel = EmailChannel(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="test@test.com"
        )
        
        assert channel.validate_config() is True
        
        # Test invalid config
        invalid_channel = EmailChannel(
            smtp_host="",
            smtp_port=587,
            username="",
            password="",
            from_email=""
        )
        
        assert invalid_channel.validate_config() is False
    
    @pytest.mark.asyncio
    async def test_email_send(self):
        """Test email sending (mocked)"""
        channel = EmailChannel(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="test@test.com"
        )
        
        alert = Alert(
            alert_id="TEST-003",
            alert_type=AlertType.STOCKOUT,
            priority=AlertPriority.HIGH,
            title="Test Alert",
            message="Test message",
            data={'email_recipients': ['recipient@test.com']},
            channels=[AlertChannel.EMAIL]
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await channel.send(alert)
            assert result is True
            mock_server.send_message.assert_called_once()


class TestAlertManager:
    """Test AlertManager main functionality"""
    
    @pytest.fixture
    def alert_manager(self):
        """Create AlertManager instance for testing"""
        config = {
            'email': {
                'smtp_host': 'smtp.test.com',
                'smtp_port': 587,
                'username': 'test',
                'password': 'test',
                'from_email': 'test@test.com'
            },
            'dashboard': {
                'db_path': ':memory:'
            }
        }
        return AlertManager(config)
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test AlertManager initialization"""
        assert len(alert_manager.channels) > 0
        assert len(alert_manager.rules) > 0
        assert alert_manager.max_history == 1000
    
    @pytest.mark.asyncio
    async def test_create_alert(self, alert_manager):
        """Test alert creation"""
        with patch.object(alert_manager, '_send_alert') as mock_send:
            alert = await alert_manager.create_alert(
                alert_type=AlertType.STOCKOUT,
                priority=AlertPriority.HIGH,
                title="Test",
                message="Test message",
                data={'test': 'data'},
                channels=[AlertChannel.DASHBOARD]
            )
            
            assert alert.alert_id.startswith("ALERT-")
            assert alert.title == "Test"
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_rules(self, alert_manager):
        """Test rule checking"""
        # Add a test rule
        test_rule = AlertRule(
            rule_id="TEST-RULE",
            name="Test Rule",
            condition=lambda data: data.get('trigger', False),
            alert_type=AlertType.STOCKOUT,
            priority=AlertPriority.HIGH,
            channels=[AlertChannel.DASHBOARD],
            cooldown_minutes=0
        )
        alert_manager.add_rule(test_rule)
        
        # Test with triggering data
        with patch.object(alert_manager, 'create_alert') as mock_create:
            mock_create.return_value = Mock(alert_id="TEST-ALERT")
            
            alerts = await alert_manager.check_rules({'trigger': True})
            assert len(alerts) > 0
            mock_create.assert_called()
        
        # Test with non-triggering data
        alerts = await alert_manager.check_rules({'trigger': False})
        # Only default rules might trigger
        assert isinstance(alerts, list)
    
    def test_add_remove_rule(self, alert_manager):
        """Test adding and removing rules"""
        initial_count = len(alert_manager.rules)
        
        # Add rule
        new_rule = AlertRule(
            rule_id="NEW-RULE",
            name="New Rule",
            condition=lambda x: True,
            alert_type=AlertType.SYSTEM_ERROR,
            priority=AlertPriority.LOW,
            channels=[AlertChannel.DASHBOARD]
        )
        alert_manager.add_rule(new_rule)
        assert len(alert_manager.rules) == initial_count + 1
        
        # Remove rule
        alert_manager.remove_rule("NEW-RULE")
        assert len(alert_manager.rules) == initial_count
    
    def test_get_alert_statistics(self, alert_manager):
        """Test alert statistics generation"""
        # Add some alerts to history
        for i in range(5):
            alert = Alert(
                alert_id=f"STAT-{i}",
                alert_type=AlertType.STOCKOUT,
                priority=AlertPriority.HIGH if i < 2 else AlertPriority.LOW,
                title="Test",
                message="Test",
                data={},
                channels=[AlertChannel.DASHBOARD]
            )
            alert_manager._add_to_history(alert)
        
        stats = alert_manager.get_alert_statistics()
        
        assert stats['total_alerts'] == 5
        assert stats['by_priority']['high'] == 2
        assert stats['by_priority']['low'] == 3
        assert 'by_type' in stats
        assert 'active_rules' in stats
    
    def test_get_default_channels(self, alert_manager):
        """Test default channel selection based on priority"""
        critical_channels = alert_manager._get_default_channels(AlertPriority.CRITICAL)
        assert AlertChannel.EMAIL in critical_channels
        assert AlertChannel.SMS in critical_channels
        assert AlertChannel.DASHBOARD in critical_channels
        
        high_channels = alert_manager._get_default_channels(AlertPriority.HIGH)
        assert AlertChannel.EMAIL in high_channels
        assert AlertChannel.DASHBOARD in high_channels
        
        low_channels = alert_manager._get_default_channels(AlertPriority.LOW)
        assert AlertChannel.DASHBOARD in low_channels
    
    def test_history_limit(self, alert_manager):
        """Test alert history size limit"""
        alert_manager.max_history = 10
        
        # Add more alerts than the limit
        for i in range(15):
            alert = Alert(
                alert_id=f"HIST-{i}",
                alert_type=AlertType.STOCKOUT,
                priority=AlertPriority.LOW,
                title="Test",
                message="Test",
                data={},
                channels=[]
            )
            alert_manager._add_to_history(alert)
        
        assert len(alert_manager.alert_history) == 10
        assert alert_manager.alert_history[0].alert_id == "HIST-5"
        assert alert_manager.alert_history[-1].alert_id == "HIST-14"


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_alert_flow(self):
        """Test complete alert flow from rule to notification"""
        config = {
            'dashboard': {
                'db_path': ':memory:'
            }
        }
        
        manager = AlertManager(config)
        
        # Create a custom rule
        rule = AlertRule(
            rule_id="E2E-RULE",
            name="End-to-End Test",
            condition=lambda data: data.get('stock_level', 100) < 20,
            alert_type=AlertType.LOW_INVENTORY,
            priority=AlertPriority.HIGH,
            channels=[AlertChannel.DASHBOARD],
            cooldown_minutes=0
        )
        manager.add_rule(rule)
        
        # Trigger the rule
        test_data = {
            'product_id': 'PROD-123',
            'stock_level': 10,
            'reorder_point': 50
        }
        
        alerts = await manager.check_rules(test_data)
        
        assert len(alerts) > 0
        assert alerts[0].alert_type == AlertType.LOW_INVENTORY
        assert alerts[0].priority == AlertPriority.HIGH
        
        # Check statistics
        stats = manager.get_alert_statistics()
        assert stats['total_alerts'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])