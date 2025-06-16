from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

class FeatureMatcher:
    def __init__(self, similarity_threshold: float = 0.5):
        """
        Initialize the FeatureMatcher with a similarity threshold.
        
        Args:
            similarity_threshold (float): Minimum similarity score to consider features as matching
        """
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            lowercase=True,
            max_features=5000,
            ngram_range=(1, 2)  # Include both unigrams and bigrams
        )
        self.logger = logging.getLogger(__name__)

    def _prepare_feature_text(self, feature_name: str, feature_description: str) -> str:
        """
        Combine feature name and description into a single text for vectorization.
        
        Args:
            feature_name (str): Name of the feature
            feature_description (str): Description of the feature
            
        Returns:
            str: Combined text for semantic matching
        """
        # Handle None/NaN values
        name = str(feature_name) if feature_name and str(feature_name) != 'nan' else ""
        desc = str(feature_description) if feature_description and str(feature_description) != 'nan' else ""
        
        # Combine name and description, giving more weight to the name
        combined_text = f"{name} {name} {desc}".strip() 
        return combined_text if combined_text else "unknown feature"

    def compute_similarity_matrix(self, capabilities: List[str], feature_texts: List[str]) -> np.ndarray:
        """
        Compute similarity matrix between capabilities and feature texts.
        
        Args:
            capabilities (List[str]): List of desired capabilities
            feature_texts (List[str]): List of feature text representations
            
        Returns:
            np.ndarray: Similarity matrix of shape (len(capabilities), len(feature_texts))
        """
        if not capabilities or not feature_texts:
            return np.array([])
        
        # Combine all texts for fitting the vectorizer
        all_texts = capabilities + feature_texts
        
        try:
            # Fit and transform all texts
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Split back into capabilities and features
            capability_vectors = tfidf_matrix[:len(capabilities)]
            feature_vectors = tfidf_matrix[len(capabilities):]
            
            # Compute cosine similarity matrix
            similarity_matrix = cosine_similarity(capability_vectors, feature_vectors)
            
            return similarity_matrix
            
        except Exception as e:
            self.logger.error(f"Error computing similarity matrix: {e}")
            return np.zeros((len(capabilities), len(feature_texts)))

    def find_matching_features(self, 
                             capabilities: List[str], 
                             features_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Find features that match the given capabilities above the similarity threshold.
        
        Args:
            capabilities (List[str]): List of desired capabilities
            features_df (pd.DataFrame): DataFrame with feature information
            
        Returns:
            List[Dict[str, Any]]: List of matching features with similarity scores
        """
        if features_df.empty or not capabilities:
            return []
        
        # Prepare feature texts for similarity computation
        feature_texts = []
        for _, row in features_df.iterrows():
            feature_text = self._prepare_feature_text(
                row.get('Feature_name', ''), 
                row.get('Feature_description', '')
            )
            feature_texts.append(feature_text)
        
        # Compute similarity matrix
        similarity_matrix = self.compute_similarity_matrix(capabilities, feature_texts)
        
        if similarity_matrix.size == 0:
            return []
        
        # Find matches above threshold
        matches = []
        for cap_idx, capability in enumerate(capabilities):
            for feat_idx, (_, feature_row) in enumerate(features_df.iterrows()):
                similarity_score = similarity_matrix[cap_idx, feat_idx]
                
                if similarity_score >= self.similarity_threshold:
                    match = {
                        'product_name': feature_row.get('product_name', ''),
                        'vendor': feature_row.get('seller', ''),
                        'main_category': feature_row.get('main_category', ''),
                        'feature_category': feature_row.get('Features_Category', ''),
                        'feature_name': feature_row.get('Feature_name', ''),
                        'feature_description': feature_row.get('Feature_description', ''),
                        'feature_percent': feature_row.get('Feature_percent', 0),
                        'feature_review_count': feature_row.get('Feature_review', 0),
                        'matched_capability': capability,
                        'similarity_score': float(similarity_score),
                        'feature_text': feature_texts[feat_idx]
                    }
                    matches.append(match)
        
        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        self.logger.info(f"Found {len(matches)} feature matches above threshold {self.similarity_threshold}")
        return matches

    def select_matching_vendors(self, matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Compile vendors that have at least one matching feature.
        
        Args:
            matches (List[Dict[str, Any]]): List of feature matches
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of vendors with their matching features
        """
        vendors = {}
        
        for match in matches:
            vendor_key = f"{match['product_name']}_{match['vendor']}"
            
            if vendor_key not in vendors:
                vendors[vendor_key] = {
                    'product_name': match['product_name'],
                    'vendor': match['vendor'],
                    'main_category': match['main_category'],
                    'matching_features': [],
                    'matched_capabilities': set(),
                    'max_similarity_score': 0.0,
                    'avg_similarity_score': 0.0,
                    'total_matches': 0
                }
            
            # Add this feature match
            vendors[vendor_key]['matching_features'].append({
                'feature_category': match['feature_category'],
                'feature_name': match['feature_name'],
                'feature_description': match['feature_description'],
                'feature_percent': match['feature_percent'],
                'feature_review_count': match['feature_review_count'],
                'matched_capability': match['matched_capability'],
                'similarity_score': match['similarity_score']
            })
            
            # Update vendor-level statistics
            vendors[vendor_key]['matched_capabilities'].add(match['matched_capability'])
            vendors[vendor_key]['max_similarity_score'] = max(
                vendors[vendor_key]['max_similarity_score'], 
                match['similarity_score']
            )
            vendors[vendor_key]['total_matches'] += 1
        
        # Calculate average similarity scores
        for vendor_data in vendors.values():
            if vendor_data['total_matches'] > 0:
                avg_score = sum(f['similarity_score'] for f in vendor_data['matching_features']) / vendor_data['total_matches']
                vendor_data['avg_similarity_score'] = avg_score
                vendor_data['matched_capabilities'] = list(vendor_data['matched_capabilities'])
        
        self.logger.info(f"Selected {len(vendors)} vendors with matching features")
        return vendors

    def filter_vendors_by_category_and_capabilities(self, 
                                                  dataframe: pd.DataFrame, 
                                                  software_category: str, 
                                                  capabilities: List[str]) -> Dict[str, Any]:
        """
        Main method to filter vendors by category and find those matching desired capabilities.
        
        Args:
            dataframe (pd.DataFrame): Input dataframe containing vendor data
            software_category (str): Software category to filter by
            capabilities (List[str]): List of desired capabilities
            
        Returns:
            Dict[str, Any]: Results containing matching vendors and statistics
        """
        self.logger.info(f"Filtering vendors for category '{software_category}' with capabilities: {capabilities}")
        
        # Filter by category first
        if software_category and software_category.lower() != 'all':
            category_filtered = dataframe[
                dataframe['main_category'].str.contains(software_category, case=False, na=False)
            ]
        else:
            category_filtered = dataframe.copy()
        
        self.logger.info(f"Found {len(category_filtered)} features in category '{software_category}'")
        
        if category_filtered.empty:
            return {
                'matching_vendors': {},
                'total_vendors': 0,
                'total_matches': 0,
                'capabilities_searched': capabilities,
                'category_searched': software_category,
                'similarity_threshold': self.similarity_threshold
            }
        
        # Find matching features
        matches = self.find_matching_features(capabilities, category_filtered)
        
        # Select matching vendors
        matching_vendors = self.select_matching_vendors(matches)
        
        return {
            'matching_vendors': matching_vendors,
            'total_vendors': len(matching_vendors),
            'total_matches': len(matches),
            'capabilities_searched': capabilities,
            'category_searched': software_category,
            'similarity_threshold': self.similarity_threshold,
            'raw_matches': matches  # Include for debugging/analysis
        }

    # old methods
    def compute_similarity(self, vendor_features: List[str], query_features: List[str]) -> float:
        """
        Compute average similarity score between vendor features and query features.
        
        Args:
            vendor_features (List[str]): List of vendor features
            query_features (List[str]): List of features to match against
            
        Returns:
            float: Average similarity score between 0 and 1
        """
        if not vendor_features or not query_features:
            return 0.0
        
        similarity_matrix = self.compute_similarity_matrix(query_features, vendor_features)
        
        if similarity_matrix.size == 0:
            return 0.0
        
        # Return the maximum similarity score across all capability-feature pairs
        return float(np.max(similarity_matrix))

    def filter_by_similarity(self, vendors: List[Dict[str, Any]], query_features: List[str]) -> List[Dict[str, Any]]:
        """
        Filter vendors based on feature similarity threshold.
        
        Args:
            vendors (List[Dict[str, Any]]): List of vendor dictionaries with features
            query_features (List[str]): List of features to match against
            
        Returns:
            List[Dict[str, Any]]: Filtered list of vendors that meet similarity threshold
        """
        filtered_vendors = []
        
        for vendor in vendors:
            vendor_features = vendor.get('features', [])
            if isinstance(vendor_features, str):
                vendor_features = [vendor_features]
            
            similarity_score = self.compute_similarity(vendor_features, query_features)
            
            if similarity_score >= self.similarity_threshold:
                vendor_copy = vendor.copy()
                vendor_copy['similarity_score'] = similarity_score
                filtered_vendors.append(vendor_copy)
        
        return filtered_vendors
