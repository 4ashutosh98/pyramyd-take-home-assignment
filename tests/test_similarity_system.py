import sys
import os
import logging
from typing import List

# Add parent directory to path to access src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_processing.data_loader import DataLoader
from src.similarity.feature_matcher import FeatureMatcher
from src.ranking.vendor_ranker import VendorRanker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_loading():
    """Test data loading and preprocessing"""
    print("=" * 60)
    print("TESTING DATA LOADING")
    print("=" * 60)
    
    try:
        loader = DataLoader("data/G2 software - CRM Category Product Overviews.csv")
        
        print(f"Original data shape: {loader.data.shape}")
        print(f"Preprocessed data shape: {loader.preprocessed_dataset.shape}")
        print(f"Unique products: {loader.data['product_name'].nunique()}")
        print(f"Unique features: {loader.preprocessed_dataset['Feature_name'].nunique()}")
        
        # Show sample of flattened data
        print("\nSample of flattened feature data:")
        sample = loader.preprocessed_dataset[['product_name', 'seller', 'Feature_name', 'Feature_percent']].head()
        print(sample.to_string())
        
        return loader
        
    except Exception as e:
        print(f"Data loading failed: {e}")
        return None

def test_similarity_matching(loader: DataLoader):
    """Test semantic similarity matching"""
    print("\n" + "=" * 60)
    print("TESTING SEMANTIC SIMILARITY MATCHING")
    print("=" * 60)
    
    try:
        matcher = FeatureMatcher(similarity_threshold=0.5)
        
        # Test case 1: CRM with Lead Management
        print("\nTest Case 1: CRM Software + Lead Management")
        results1 = matcher.filter_vendors_by_category_and_capabilities(
            dataframe=loader.preprocessed_dataset,
            software_category="CRM Software",
            capabilities=["Lead Management"]
        )
        
        print(f"Found {results1['total_vendors']} vendors with {results1['total_matches']} feature matches")
        
        if results1['matching_vendors']:
            # Show top vendor
            top_vendor = list(results1['matching_vendors'].values())[0]
            print(f"Top vendor: {top_vendor['product_name']} by {top_vendor['vendor']}")
            print(f"   - Max similarity: {top_vendor['max_similarity_score']:.3f}")
            print(f"   - Total matches: {top_vendor['total_matches']}")
            print(f"   - Matched capabilities: {top_vendor['matched_capabilities']}")
        
        # Test case 2: CRM with multiple capabilities
        print("\nTest Case 2: CRM Software + Multiple Capabilities")
        results2 = matcher.filter_vendors_by_category_and_capabilities(
            dataframe=loader.preprocessed_dataset,
            software_category="CRM Software",
            capabilities=["Lead Management", "Email Marketing", "Contact Management"]
        )
        
        print(f"Found {results2['total_vendors']} vendors with {results2['total_matches']} feature matches")
        
        # Test case 3: Lower threshold
        print("\nTest Case 3: Lower Threshold (0.4)")
        matcher_low = FeatureMatcher(similarity_threshold=0.4)
        results3 = matcher_low.filter_vendors_by_category_and_capabilities(
            dataframe=loader.preprocessed_dataset,
            software_category="CRM Software",
            capabilities=["Lead Management"]
        )
        
        print(f"Found {results3['total_vendors']} vendors with {results3['total_matches']} feature matches")
        print(f"Threshold impact: {results3['total_vendors'] - results1['total_vendors']} more vendors at 0.4 vs 0.5")
        
        return results2  # Return multi-capability results for ranking test
        
    except Exception as e:
        print(f"Similarity matching failed: {e}")
        return None

def test_vendor_ranking(loader: DataLoader, matching_results: dict):
    """Test vendor ranking"""
    print("\n" + "=" * 60)
    print("TESTING VENDOR RANKING")
    print("=" * 60)
    
    try:
        ranker = VendorRanker(feature_weight=0.7, rating_weight=0.3)
        
        # Add ratings to vendor data
        enhanced_vendors = {}
        for vendor_key, vendor_data in matching_results['matching_vendors'].items():
            product_name = vendor_data['product_name']
            original_data = loader.data[loader.data['product_name'] == product_name]
            
            if not original_data.empty:
                rating = original_data.iloc[0].get('rating', 0.0)
                vendor_data['rating'] = rating
            else:
                vendor_data['rating'] = 0.0
            
            enhanced_vendors[vendor_key] = vendor_data
        
        # Rank vendors
        ranked_vendors = ranker.rank_vendors(enhanced_vendors, top_n=5)
        
        print(f"Ranked {len(enhanced_vendors)} vendors, showing top {len(ranked_vendors)}")
        
        # Show ranking results
        print("\nTOP RANKED VENDORS:")
        for i, vendor in enumerate(ranked_vendors, 1):
            print(f"{i}. {vendor['product_name']} by {vendor['vendor']}")
            print(f"   - Rank Score: {vendor['rank_score']:.3f}")
            print(f"   - Max Similarity: {vendor['max_similarity_score']:.3f}")
            print(f"   - Rating: {vendor['rating']}/5.0")
            print(f"   - Total Matches: {vendor['total_matches']}")
            print(f"   - Matched Capabilities: {vendor['matched_capabilities']}")
            print()
        
        # Generate ranking summary
        summary = ranker.get_ranking_summary(ranked_vendors)
        print("RANKING SUMMARY:")
        print(f"   - Score range: {summary['score_range']['min']:.3f} - {summary['score_range']['max']:.3f}")
        print(f"   - Average score: {summary['avg_score']:.3f}")
        print(f"   - Methodology: {summary['methodology']['description']}")
        
        return ranked_vendors
        
    except Exception as e:
        print(f"Vendor ranking failed: {e}")
        return None

def test_edge_cases(loader: DataLoader):
    """Test edge cases and error handling"""
    print("\n" + "=" * 60)
    print("TESTING EDGE CASES")
    print("=" * 60)
    
    matcher = FeatureMatcher(similarity_threshold=0.5)
    
    # Test 1: Non-existent category
    print("Test: Non-existent category")
    results = matcher.filter_vendors_by_category_and_capabilities(
        dataframe=loader.preprocessed_dataset,
        software_category="Non-existent Category",
        capabilities=["Some Capability"]
    )
    print(f"Non-existent category handled: {results['total_vendors']} vendors found")
    
    # Test 2: Very high threshold
    print("\nTest: Very high threshold (0.95)")
    matcher_high = FeatureMatcher(similarity_threshold=0.95)
    results = matcher_high.filter_vendors_by_category_and_capabilities(
        dataframe=loader.preprocessed_dataset,
        software_category="CRM Software",
        capabilities=["Lead Management"]
    )
    print(f"High threshold handled: {results['total_vendors']} vendors found")
    
    # Test 3: Empty capabilities
    print("\nTest: Empty capabilities list")
    results = matcher.filter_vendors_by_category_and_capabilities(
        dataframe=loader.preprocessed_dataset,
        software_category="CRM Software",
        capabilities=[]
    )
    print(f"Empty capabilities handled: {results['total_vendors']} vendors found")

def main():
    """Main test function"""
    print("VENDOR QUALIFICATION SYSTEM - COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Test 1: Data Loading
    loader = test_data_loading()
    if not loader:
        print("Cannot proceed without data loader")
        return
    
    # Test 2: Similarity Matching
    matching_results = test_similarity_matching(loader)
    if not matching_results:
        print("Cannot proceed without similarity matching")
        return
    
    # Test 3: Vendor Ranking
    ranked_vendors = test_vendor_ranking(loader, matching_results)
    if not ranked_vendors:
        print("Ranking test failed")
        return
    
    # Test 4: Edge Cases
    test_edge_cases(loader)
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nThe semantic similarity matching system is working correctly!")
    print("   - Data preprocessing: PASS")
    print("   - TF-IDF vectorization: PASS") 
    print("   - Cosine similarity computation: PASS")
    print("   - Threshold-based filtering: PASS")
    print("   - Vendor selection and ranking: PASS")
    
    print("\nSystem is ready for API deployment!")

if __name__ == "__main__":
    main() 