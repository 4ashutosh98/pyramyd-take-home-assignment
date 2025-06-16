import pytest
import pandas as pd
import sys
import os

# Add parent directory to path to access src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_processing.data_loader import DataLoader

def test_data_loader_initialization():
    """Test DataLoader initialization."""
    loader = DataLoader("data/G2 software - CRM Category Product Overviews.csv")
    assert loader.file_path == "data/G2 software - CRM Category Product Overviews.csv"
    assert loader.data is None

def test_load_data():
    """Test data loading functionality."""
    loader = DataLoader("data/G2 software - CRM Category Product Overviews.csv")
    loader.load_data()
    
    # Check that data was loaded
    assert loader.data is not None
    assert isinstance(loader.data, pd.DataFrame)
    
    # Check expected columns exist
    required_columns = ['product_name', 'seller', 'category', 'rating']
    for col in required_columns:
        assert col in loader.data.columns
        
    # Check data is not empty
    assert len(loader.data) > 0

def test_get_vendors_by_category():
    """Test vendor filtering by category."""
    loader = DataLoader("data/G2 software - CRM Category Product Overviews.csv")
    loader.load_data()
    
    # Test filtering for CRM category
    crm_vendors = loader.get_vendors_by_category("CRM Software")
    assert len(crm_vendors) > 0
    for vendor in crm_vendors:
        assert vendor['category'] == "CRM Software"
    
    # Test filtering for non-existent category
    empty_vendors = loader.get_vendors_by_category("Invalid Category")
    assert len(empty_vendors) == 0

def test_get_vendor_features():
    """Test feature extraction for vendors."""
    loader = DataLoader("data/G2 software - CRM Category Product Overviews.csv")
    loader.load_data()
    
    # Get features for first vendor
    first_vendor = loader.data.iloc[0]
    vendor_name = first_vendor['product_name']
    features = loader.get_vendor_features(vendor_name)
    
    # Check feature structure
    assert isinstance(features, list)
    assert len(features) > 0
    for feature in features:
        assert isinstance(feature, dict)
        assert 'name' in feature
        assert 'score' in feature
        assert isinstance(feature['score'], float)
        assert 0 <= feature['score'] <= 1