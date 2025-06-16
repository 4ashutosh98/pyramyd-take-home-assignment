import pandas as pd
from typing import List, Dict, Any
import json

class DataLoader:
    def __init__(self, file_path: str):
        """
        Initialize the DataLoader with the path to the CSV file.
        
        Args:
            file_path (str): Path to the CSV file containing vendor data
        """
        self.file_path = file_path
        self.data = pd.read_csv(file_path)
        self.preprocessed_dataset = self.preprocess_data()

    def preprocess_data(self) -> pd.DataFrame:
        """
        Load and preprocess the vendor data from CSV.
        
        Returns:
            pd.DataFrame: Processed vendor data
        """
        # Create a copy to avoid modifying original data
        df = self.data.copy()
        
        # Drop columns that exist in the dataset (handle missing columns gracefully)
        columns_to_drop = [
            'ownership', 'total_revenue', 'highest_rated_features', 'lowest_rated_features', 
            'official_screenshots', 'official_videos', 'user_ratings', 'badge', 
            'what_is_description', 'seller_description', 'position_against_competitors', 
            'competitors', 'official_downloads'
        ]
        
        # Only drop columns that actually exist
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        df = df.drop(columns=existing_columns_to_drop)
        
        # Process Features column - handle NaN values properly
        def safe_json_parse(x):
            if pd.isna(x) or x is None:
                return None
            if isinstance(x, str):
                try:
                    return json.loads(x)
                except json.JSONDecodeError:
                    return None
            return None
        
        df['Features'] = df['Features'].apply(safe_json_parse)
        
        # Filter out rows with no features for exploding
        df_with_features = df[df['Features'].notna()].copy()
        df_without_features = df[df['Features'].isna()].copy()
        
        if len(df_with_features) == 0:
            # If no features data, return original df with additional columns
            df['Features_Category'] = None
            df['Feature_name'] = None
            df['Feature_description'] = None
            df['Feature_percent'] = None
            df['Feature_review'] = None
            return df.drop(columns=['Features'])
        
        # Explode the Features column (each category becomes a row)
        df_exploded = df_with_features.explode('Features').reset_index(drop=True)
        
        # Extract category information
        df_exploded['Features_Category'] = df_exploded['Features'].apply(
            lambda x: x.get('Category', None) if isinstance(x, dict) else None
        )
        df_exploded['Features_list'] = df_exploded['Features'].apply(
            lambda x: x.get('features', []) if isinstance(x, dict) else []
        )
        
        # Drop the original Features column
        df_exploded = df_exploded.drop(columns=['Features'])
        
        # Explode the features list (each feature becomes a row)
        df_exploded2 = df_exploded.explode('Features_list').reset_index(drop=True)
        
        # Extract individual feature information
        df_exploded2['Feature_description'] = df_exploded2['Features_list'].apply(
            lambda x: x.get('description', '') if isinstance(x, dict) else ''
        )
        df_exploded2['Feature_name'] = df_exploded2['Features_list'].apply(
            lambda x: x.get('name', '') if isinstance(x, dict) else ''
        ) 
        df_exploded2['Feature_percent'] = df_exploded2['Features_list'].apply(
            lambda x: x.get('percent', 0) if isinstance(x, dict) else 0
        )
        df_exploded2['Feature_review'] = df_exploded2['Features_list'].apply(
            lambda x: x.get('review', 0) if isinstance(x, dict) else 0
        )
        
        # Drop the Features_list column
        df_exploded2 = df_exploded2.drop(columns=['Features_list'])
        
        return df_exploded2

    def get_vendors_by_category(self, category: str) -> pd.DataFrame:
        """
        Filter vendors by main category.
        
        Args:
            category (str): Software category to filter by
            
        Returns:
            pd.DataFrame: Filtered vendor data
        """
        return self.preprocessed_dataset[
            self.preprocessed_dataset['main_category'] == category
        ]

    def get_vendor_features(self, vendor_name: str) -> List[str]:
        """
        Extract features for a specific vendor.
        
        Args:
            vendor_name (str): Name of the vendor
            
        Returns:
            List[str]: List of vendor features
        """
        vendor_data = self.preprocessed_dataset[
            self.preprocessed_dataset['product_name'] == vendor_name
        ]
        return vendor_data['Feature_name'].dropna().tolist()

    def get_vendors_by_features(self, features: List[str]) -> pd.DataFrame:
        """
        Filter vendors by features.
        
        Args:
            features (List[str]): List of features to filter by
            
        Returns:
            pd.DataFrame: Filtered vendor data
        """
        return self.preprocessed_dataset[
            self.preprocessed_dataset['Feature_name'].isin(features)
        ]
    