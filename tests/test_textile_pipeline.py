#!/usr/bin/env python3
"""
Comprehensive test suite for textile pipeline
Target: 90% coverage of all pipeline components
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "erp1"))

# Import modules to test
from erp_yarn_fabric_processor import YarnFabricProcessor
from yarn_fabric_mapper import YarnFabricMapper
from yarn_consumption_analyzer import YarnConsumptionAnalyzer
from yarn_interchangeability_analyzer import YarnInterchangeabilityAnalyzer
from beverly_knits_data_loader import BeverlyKnitsDataLoader
from beverly_knits_data_config import load_data, BUSINESS_RULES


class TestYarnFabricProcessor:
    """Test suite for YarnFabricProcessor"""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance"""
        return YarnFabricProcessor()
    
    def test_initialization(self, processor):
        """Test processor initialization"""
        assert processor is not None
        assert hasattr(processor, 'conversion_rates')
        assert 'DEFAULT' in processor.conversion_rates
        assert processor.conversion_rates['DEFAULT'] == 0.64
    
    def test_pounds_to_yards_conversion(self, processor):
        """Test weight to length conversion"""
        # Test with default fabric
        result = processor.pounds_to_yards(100, 'DEFAULT')
        assert result == pytest.approx(156.25, rel=1e-2)
        
        # Test with cotton
        result = processor.pounds_to_yards(100, 'COTTON')
        assert result == pytest.approx(178.57, rel=1e-2)
        
        # Test with polyester
        result = processor.pounds_to_yards(100, 'POLYESTER')
        assert result == pytest.approx(142.86, rel=1e-2)
    
    def test_yards_to_pounds_conversion(self, processor):
        """Test length to weight conversion"""
        # Test inverse conversion
        yards = processor.pounds_to_yards(100, 'DEFAULT')
        pounds = processor.yards_to_pounds(yards, 'DEFAULT')
        assert pounds == pytest.approx(100, rel=1e-2)
    
    def test_invalid_fabric_type(self, processor):
        """Test handling of invalid fabric types"""
        # Should use default for unknown types
        result = processor.pounds_to_yards(100, 'UNKNOWN_FABRIC')
        assert result == processor.pounds_to_yards(100, 'DEFAULT')
    
    def test_negative_values(self, processor):
        """Test handling of negative values"""
        with pytest.raises(ValueError):
            processor.pounds_to_yards(-100, 'DEFAULT')
        
        with pytest.raises(ValueError):
            processor.yards_to_pounds(-100, 'DEFAULT')
    
    def test_zero_values(self, processor):
        """Test handling of zero values"""
        result = processor.pounds_to_yards(0, 'DEFAULT')
        assert result == 0
        
        result = processor.yards_to_pounds(0, 'DEFAULT')
        assert result == 0
    
    def test_process_inventory_data(self, processor):
        """Test inventory data processing"""
        # Create sample inventory data
        inventory_df = pd.DataFrame({
            'Style': ['S001', 'S002', 'S003'],
            'Qty (lbs)': [100, 200, 150],
            'Fabric Type': ['COTTON', 'POLYESTER', 'DEFAULT']
        })
        
        # Process inventory
        result = processor.process_inventory(inventory_df)
        
        assert 'Qty (yards)' in result.columns
        assert len(result) == 3
        assert result['Qty (yards)'].sum() > 0
    
    def test_calculate_consumption_metrics(self, processor):
        """Test consumption metrics calculation"""
        # Create sample sales data
        sales_df = pd.DataFrame({
            'Invoice Date': pd.date_range('2025-01-01', periods=30),
            'Qty Shipped': np.random.randint(10, 100, 30),
            'UOM': ['lbs'] * 15 + ['yds'] * 15,
            'Style': ['S001'] * 30
        })
        
        metrics = processor.calculate_consumption_metrics(sales_df)
        
        assert 'total_consumed_lbs' in metrics
        assert 'total_consumed_yards' in metrics
        assert 'daily_average_lbs' in metrics
        assert metrics['total_consumed_lbs'] > 0


class TestYarnFabricMapper:
    """Test suite for YarnFabricMapper"""
    
    @pytest.fixture
    def mapper(self):
        """Create mapper instance"""
        return YarnFabricMapper()
    
    def test_initialization(self, mapper):
        """Test mapper initialization"""
        assert mapper is not None
        assert hasattr(mapper, 'yarn_to_fabric_map')
        assert isinstance(mapper.yarn_to_fabric_map, dict)
    
    def test_map_yarn_to_fabric(self, mapper):
        """Test yarn to fabric mapping"""
        # Add test mapping
        mapper.yarn_to_fabric_map = {
            'Y001': ['F001', 'F002'],
            'Y002': ['F003']
        }
        
        fabrics = mapper.get_fabrics_for_yarn('Y001')
        assert len(fabrics) == 2
        assert 'F001' in fabrics
        
        fabrics = mapper.get_fabrics_for_yarn('Y003')
        assert len(fabrics) == 0
    
    def test_reverse_mapping(self, mapper):
        """Test fabric to yarn mapping"""
        mapper.yarn_to_fabric_map = {
            'Y001': ['F001', 'F002'],
            'Y002': ['F001', 'F003']
        }
        
        yarns = mapper.get_yarns_for_fabric('F001')
        assert len(yarns) == 2
        assert 'Y001' in yarns
        assert 'Y002' in yarns
    
    def test_load_mappings_from_file(self, mapper, tmp_path):
        """Test loading mappings from CSV file"""
        # Create temporary CSV file
        csv_file = tmp_path / "yarn_fabric_map.csv"
        df = pd.DataFrame({
            'Yarn Code': ['Y001', 'Y001', 'Y002'],
            'Fabric Code': ['F001', 'F002', 'F003']
        })
        df.to_csv(csv_file, index=False)
        
        # Load mappings
        mapper.load_mappings(csv_file)
        
        assert 'Y001' in mapper.yarn_to_fabric_map
        assert len(mapper.yarn_to_fabric_map['Y001']) == 2


class TestYarnConsumptionAnalyzer:
    """Test suite for YarnConsumptionAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return YarnConsumptionAnalyzer()
    
    def test_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer is not None
        assert hasattr(analyzer, 'consumption_history')
    
    def test_analyze_consumption_patterns(self, analyzer):
        """Test consumption pattern analysis"""
        # Create sample consumption data
        consumption_df = pd.DataFrame({
            'Date': pd.date_range('2025-01-01', periods=90),
            'Yarn Code': ['Y001'] * 30 + ['Y002'] * 30 + ['Y003'] * 30,
            'Consumed (lbs)': np.random.randint(50, 200, 90)
        })
        
        patterns = analyzer.analyze_patterns(consumption_df)
        
        assert 'Y001' in patterns
        assert 'average_daily' in patterns['Y001']
        assert 'trend' in patterns['Y001']
        assert patterns['Y001']['average_daily'] > 0
    
    def test_forecast_consumption(self, analyzer):
        """Test consumption forecasting"""
        # Create historical data
        historical_df = pd.DataFrame({
            'Date': pd.date_range('2025-01-01', periods=30),
            'Yarn Code': ['Y001'] * 30,
            'Consumed (lbs)': [100 + i * 2 + np.random.randint(-10, 10) for i in range(30)]
        })
        
        forecast = analyzer.forecast_consumption(historical_df, 'Y001', days=7)
        
        assert len(forecast) == 7
        assert all(f > 0 for f in forecast)
    
    def test_identify_high_consumption_yarns(self, analyzer):
        """Test identification of high consumption yarns"""
        consumption_df = pd.DataFrame({
            'Yarn Code': ['Y001', 'Y002', 'Y003', 'Y004'],
            'Total Consumed': [1000, 500, 2000, 100]
        })
        
        high_consumption = analyzer.identify_high_consumption(consumption_df, threshold=0.75)
        
        assert 'Y003' in high_consumption
        assert 'Y001' in high_consumption
        assert 'Y004' not in high_consumption


class TestYarnInterchangeabilityAnalyzer:
    """Test suite for YarnInterchangeabilityAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return YarnInterchangeabilityAnalyzer()
    
    def test_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer is not None
        assert hasattr(analyzer, 'similarity_threshold')
        assert analyzer.similarity_threshold == 0.85
    
    def test_calculate_yarn_similarity(self, analyzer):
        """Test yarn similarity calculation"""
        yarn1 = {
            'composition': 'Cotton 100%',
            'weight': 100,
            'color': 'White',
            'twist': 'S'
        }
        yarn2 = {
            'composition': 'Cotton 100%',
            'weight': 102,
            'color': 'White',
            'twist': 'S'
        }
        yarn3 = {
            'composition': 'Polyester 100%',
            'weight': 100,
            'color': 'White',
            'twist': 'S'
        }
        
        similarity1_2 = analyzer.calculate_similarity(yarn1, yarn2)
        similarity1_3 = analyzer.calculate_similarity(yarn1, yarn3)
        
        assert similarity1_2 > similarity1_3
        assert similarity1_2 > 0.9
        assert similarity1_3 < 0.7
    
    def test_find_interchangeable_yarns(self, analyzer):
        """Test finding interchangeable yarns"""
        yarn_inventory = pd.DataFrame({
            'Yarn Code': ['Y001', 'Y002', 'Y003'],
            'Composition': ['Cotton 100%', 'Cotton 100%', 'Polyester 100%'],
            'Weight': [100, 102, 100],
            'Color': ['White', 'White', 'White']
        })
        
        interchangeable = analyzer.find_interchangeable(yarn_inventory, 'Y001')
        
        assert 'Y002' in interchangeable
        assert 'Y003' not in interchangeable
    
    def test_generate_substitution_matrix(self, analyzer):
        """Test substitution matrix generation"""
        yarn_inventory = pd.DataFrame({
            'Yarn Code': ['Y001', 'Y002', 'Y003'],
            'Composition': ['Cotton 100%', 'Cotton 95% Spandex 5%', 'Polyester 100%'],
            'Weight': [100, 100, 100]
        })
        
        matrix = analyzer.generate_substitution_matrix(yarn_inventory)
        
        assert matrix.shape == (3, 3)
        assert matrix.loc['Y001', 'Y001'] == 1.0
        assert matrix.loc['Y001', 'Y003'] < 0.5


class TestBeverlyKnitsDataLoader:
    """Test suite for BeverlyKnitsDataLoader"""
    
    @pytest.fixture
    def loader(self):
        """Create loader instance"""
        return BeverlyKnitsDataLoader()
    
    def test_initialization(self, loader):
        """Test loader initialization"""
        assert loader is not None
        assert hasattr(loader, 'data_cache')
        assert isinstance(loader.data_cache, dict)
    
    @patch('pandas.read_excel')
    def test_load_excel_data(self, mock_read_excel, loader):
        """Test loading Excel data"""
        # Mock Excel data
        mock_df = pd.DataFrame({'col1': [1, 2, 3]})
        mock_read_excel.return_value = mock_df
        
        result = loader.load_excel('test.xlsx')
        
        assert result is not None
        assert len(result) == 3
        mock_read_excel.assert_called_once()
    
    @patch('pandas.read_csv')
    def test_load_csv_data(self, mock_read_csv, loader):
        """Test loading CSV data"""
        # Mock CSV data
        mock_df = pd.DataFrame({'col1': [1, 2, 3]})
        mock_read_csv.return_value = mock_df
        
        result = loader.load_csv('test.csv')
        
        assert result is not None
        assert len(result) == 3
        mock_read_csv.assert_called_once()
    
    def test_cache_functionality(self, loader):
        """Test data caching"""
        # Add data to cache
        test_df = pd.DataFrame({'col1': [1, 2, 3]})
        loader.data_cache['test_key'] = test_df
        
        # Retrieve from cache
        cached = loader.get_from_cache('test_key')
        assert cached is not None
        assert len(cached) == 3
        
        # Test missing key
        missing = loader.get_from_cache('missing_key')
        assert missing is None
    
    def test_validate_required_columns(self, loader):
        """Test column validation"""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [4, 5, 6]
        })
        
        # Should pass
        assert loader.validate_columns(df, ['col1', 'col2'])
        
        # Should fail
        assert not loader.validate_columns(df, ['col1', 'col3'])


class TestBusinessRules:
    """Test suite for business rules validation"""
    
    def test_minimum_order_quantities(self):
        """Test minimum order quantity rules"""
        assert BUSINESS_RULES['minimum_order_quantities']['yarn'] == 100
        assert BUSINESS_RULES['minimum_order_quantities']['fabric'] == 500
    
    def test_lead_time_rules(self):
        """Test lead time rules"""
        assert BUSINESS_RULES['lead_times']['domestic'] == 14
        assert BUSINESS_RULES['lead_times']['international'] == 45
    
    def test_safety_stock_rules(self):
        """Test safety stock rules"""
        assert BUSINESS_RULES['safety_stock']['weeks_of_supply'] == 4
        assert BUSINESS_RULES['safety_stock']['critical_items_weeks'] == 8
    
    def test_quality_thresholds(self):
        """Test quality threshold rules"""
        assert BUSINESS_RULES['quality_thresholds']['defect_rate'] == 0.02
        assert BUSINESS_RULES['quality_thresholds']['first_pass_yield'] == 0.95


class TestIntegrationPipeline:
    """Integration tests for complete pipeline"""
    
    @pytest.fixture
    def pipeline_components(self):
        """Create all pipeline components"""
        return {
            'processor': YarnFabricProcessor(),
            'mapper': YarnFabricMapper(),
            'consumption_analyzer': YarnConsumptionAnalyzer(),
            'interchangeability_analyzer': YarnInterchangeabilityAnalyzer(),
            'loader': BeverlyKnitsDataLoader()
        }
    
    def test_end_to_end_yarn_analysis(self, pipeline_components):
        """Test complete yarn analysis pipeline"""
        # Create sample data
        yarn_inventory = pd.DataFrame({
            'Yarn Code': ['Y001', 'Y002', 'Y003'],
            'Description': ['Cotton White', 'Cotton Blue', 'Polyester Red'],
            'Qty (lbs)': [1000, 500, 750],
            'Cost/Pound': [5.50, 6.00, 4.50]
        })
        
        sales_data = pd.DataFrame({
            'Invoice Date': pd.date_range('2025-01-01', periods=30),
            'Qty Shipped': np.random.randint(10, 50, 30),
            'UOM': ['lbs'] * 30,
            'Style': ['S001'] * 30
        })
        
        # Process through pipeline
        processor = pipeline_components['processor']
        
        # Convert weights to yards
        yarn_inventory['Qty (yards)'] = yarn_inventory['Qty (lbs)'].apply(
            lambda x: processor.pounds_to_yards(x, 'DEFAULT')
        )
        
        # Calculate consumption metrics
        consumption_metrics = processor.calculate_consumption_metrics(sales_data)
        
        # Analyze interchangeability
        analyzer = pipeline_components['interchangeability_analyzer']
        interchangeable_yarns = analyzer.find_interchangeable(yarn_inventory, 'Y001')
        
        # Validate results
        assert 'Qty (yards)' in yarn_inventory.columns
        assert yarn_inventory['Qty (yards)'].sum() > 0
        assert consumption_metrics['total_consumed_lbs'] > 0
        assert isinstance(interchangeable_yarns, list)
    
    def test_pipeline_error_handling(self, pipeline_components):
        """Test pipeline error handling"""
        processor = pipeline_components['processor']
        
        # Test with invalid data
        invalid_df = pd.DataFrame({'invalid': [1, 2, 3]})
        
        with pytest.raises(KeyError):
            processor.process_inventory(invalid_df)
        
        # Test with empty data
        empty_df = pd.DataFrame()
        result = processor.process_inventory(empty_df)
        assert len(result) == 0
    
    def test_pipeline_performance(self, pipeline_components):
        """Test pipeline performance with large dataset"""
        import time
        
        # Create large dataset
        large_df = pd.DataFrame({
            'Yarn Code': [f'Y{i:04d}' for i in range(10000)],
            'Qty (lbs)': np.random.randint(100, 1000, 10000),
            'Fabric Type': np.random.choice(['COTTON', 'POLYESTER', 'DEFAULT'], 10000)
        })
        
        processor = pipeline_components['processor']
        
        # Measure processing time
        start_time = time.time()
        result = processor.process_inventory(large_df)
        processing_time = time.time() - start_time
        
        # Should process 10,000 records in under 1 second
        assert processing_time < 1.0
        assert len(result) == 10000


# Test configuration and fixtures
@pytest.fixture(scope='session')
def test_data_dir(tmp_path_factory):
    """Create temporary test data directory"""
    return tmp_path_factory.mktemp('test_data')


@pytest.fixture(scope='session')
def sample_yarn_data():
    """Generate sample yarn data for testing"""
    return pd.DataFrame({
        'Yarn Code': [f'Y{i:03d}' for i in range(1, 21)],
        'Description': [f'Yarn Type {i}' for i in range(1, 21)],
        'Composition': ['Cotton 100%'] * 10 + ['Polyester 100%'] * 10,
        'Weight': np.random.randint(80, 120, 20),
        'Color': ['White'] * 5 + ['Blue'] * 5 + ['Red'] * 5 + ['Green'] * 5,
        'On Hand': np.random.randint(100, 1000, 20),
        'On Order': np.random.randint(0, 500, 20),
        'Cost/Pound': np.random.uniform(4.0, 8.0, 20)
    })


@pytest.fixture(scope='session')
def sample_sales_data():
    """Generate sample sales data for testing"""
    dates = pd.date_range('2025-01-01', periods=90)
    return pd.DataFrame({
        'Invoice Date': dates,
        'Invoice Number': [f'INV{i:05d}' for i in range(1, 91)],
        'Style': np.random.choice(['S001', 'S002', 'S003'], 90),
        'Qty Shipped': np.random.randint(10, 100, 90),
        'UOM': np.random.choice(['lbs', 'yds'], 90),
        'Unit Price': np.random.uniform(10, 50, 90)
    })


if __name__ == '__main__':
    # Run tests with coverage
    pytest.main([__file__, '-v', '--cov=.', '--cov-report=html', '--cov-report=term'])