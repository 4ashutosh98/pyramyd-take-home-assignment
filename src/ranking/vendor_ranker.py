from typing import List, Dict, Any
import numpy as np
import logging

class VendorRanker:
    def __init__(self, feature_weight: float = 0.7, rating_weight: float = 0.3):
        """
        Initialize the VendorRanker with weights for different ranking factors.
        
        Args:
            feature_weight (float): Weight for feature similarity in ranking
            rating_weight (float): Weight for vendor rating in ranking
        """
        self.feature_weight = feature_weight
        self.rating_weight = rating_weight
        self.logger = logging.getLogger(__name__)

    def compute_rank_score(self, vendor_data: Dict[str, Any], similarity_score: float = None) -> float:
        """
        Compute overall rank score for a vendor.
        
        Args:
            vendor_data (Dict[str, Any]): Vendor information including rating and similarity data
            similarity_score (float, optional): Override similarity score if provided
            
        Returns:
            float: Overall rank score (0-1, higher is better)
        """
        # Get similarity score
        if similarity_score is not None:
            sim_score = similarity_score
        else:
            # Use average similarity score as per requirements - vendors with multiple matches
            # should be ranked by their average similarity across all matched features
            sim_score = vendor_data.get('avg_similarity_score', 0.0)
        
        # Normalize similarity score to 0-1 range
        sim_score = max(0.0, min(1.0, sim_score))
        
        # Get vendor rating
        rating = vendor_data.get('rating', 0.0)
        if isinstance(rating, str):
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = 0.0
        
        # Normalize rating to 0-1 scale
        normalized_rating = rating / 5.0 if rating > 0 else 0.0
        normalized_rating = max(0.0, min(1.0, normalized_rating))
        
        # Compute weighted score
        final_score = (self.feature_weight * sim_score) + (self.rating_weight * normalized_rating)
        
        return final_score

    def rank_vendors(self, vendors_dict: Dict[str, Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Rank vendors based on similarity scores and ratings.
        
        Args:
            vendors_dict (Dict[str, Dict[str, Any]]): Dictionary of vendors with their data
            top_n (int): Number of top vendors to return
            
        Returns:
            List[Dict[str, Any]]: Ranked list of top N vendors
        """
        if not vendors_dict:
            return []
        
        ranked_vendors = []
        
        for vendor_key, vendor_data in vendors_dict.items():
            # Compute rank score
            rank_score = self.compute_rank_score(vendor_data)
            
            # Create vendor result with ranking information
            vendor_result = {
                'vendor_key': vendor_key,
                'product_name': vendor_data.get('product_name', ''),
                'vendor': vendor_data.get('vendor', ''),
                'main_category': vendor_data.get('main_category', ''),
                'rank_score': rank_score,
                'max_similarity_score': vendor_data.get('max_similarity_score', 0.0),
                'avg_similarity_score': vendor_data.get('avg_similarity_score', 0.0),
                'total_matches': vendor_data.get('total_matches', 0),
                'matched_capabilities': vendor_data.get('matched_capabilities', []),
                'matching_features': vendor_data.get('matching_features', []),
                'rating': vendor_data.get('rating', 0.0)
            }
            
            ranked_vendors.append(vendor_result)
        
        # Sort by rank score (descending)
        ranked_vendors.sort(key=lambda x: x['rank_score'], reverse=True)
        
        # Return top N vendors
        top_vendors = ranked_vendors[:top_n]
        
        self.logger.info(f"Ranked {len(vendors_dict)} vendors, returning top {len(top_vendors)}")
        
        return top_vendors

    '''def rank_vendors_old(self, vendors: List[Dict[str, Any]], similarity_scores: List[float], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        old method: Rank vendors based on similarity scores and ratings.
        
        Args:
            vendors (List[Dict[str, Any]]): List of vendor dictionaries
            similarity_scores (List[float]): List of similarity scores for each vendor
            top_n (int): Number of top vendors to return
            
        Returns:
            List[Dict[str, Any]]: Ranked list of top N vendors
        """
        if not vendors or not similarity_scores or len(vendors) != len(similarity_scores):
            return []
        
        ranked_vendors = []
        
        for i, (vendor, sim_score) in enumerate(zip(vendors, similarity_scores)):
            # Compute rank score
            rank_score = self.compute_rank_score(vendor, sim_score)
            
            # Create vendor result
            vendor_result = vendor.copy()
            vendor_result.update({
                'rank_score': rank_score,
                'similarity_score': sim_score
            })
            
            ranked_vendors.append(vendor_result)
        
        # Sort by rank score (descending)
        ranked_vendors.sort(key=lambda x: x['rank_score'], reverse=True)
        
        return ranked_vendors[:top_n]'''

    def add_ranking_explanation(self, ranked_vendors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add explanation of ranking methodology to vendor results.
        
        Args:
            ranked_vendors (List[Dict[str, Any]]): List of ranked vendors
            
        Returns:
            List[Dict[str, Any]]: Vendors with ranking explanations added
        """
        for vendor in ranked_vendors:
            # Use average similarity score for explanation consistency
            sim_score = vendor.get('avg_similarity_score', 0.0)
            rating = vendor.get('rating', 0.0)
            normalized_rating = rating / 5.0 if rating > 0 else 0.0
            
            explanation = {
                'ranking_methodology': {
                    'feature_weight': self.feature_weight,
                    'rating_weight': self.rating_weight,
                    'similarity_component': sim_score * self.feature_weight,
                    'rating_component': normalized_rating * self.rating_weight,
                    'final_score': vendor.get('rank_score', 0.0)
                },
                'score_breakdown': f"Rank Score = ({self.feature_weight} * {sim_score:.3f}) + ({self.rating_weight} * {normalized_rating:.3f}) = {vendor.get('rank_score', 0.0):.3f}"
            }
            
            vendor['ranking_explanation'] = explanation
        
        return ranked_vendors

    def get_ranking_summary(self, ranked_vendors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of the ranking results.
        
        Args:
            ranked_vendors (List[Dict[str, Any]]): List of ranked vendors
            
        Returns:
            Dict[str, Any]: Ranking summary statistics
        """
        if not ranked_vendors:
            return {
                'total_vendors': 0,
                'score_range': {'min': 0, 'max': 0},
                'avg_score': 0,
                'methodology': {
                    'feature_weight': self.feature_weight,
                    'rating_weight': self.rating_weight
                }
            }
        
        scores = [v.get('rank_score', 0.0) for v in ranked_vendors]
        
        return {
            'total_vendors': len(ranked_vendors),
            'score_range': {
                'min': min(scores),
                'max': max(scores)
            },
            'avg_score': sum(scores) / len(scores),
            'methodology': {
                'feature_weight': self.feature_weight,
                'rating_weight': self.rating_weight,
                'description': f"Final score = {self.feature_weight} * similarity_score + {self.rating_weight} * normalized_rating"
            },
            'top_vendor': {
                'name': ranked_vendors[0].get('product_name', ''),
                'score': ranked_vendors[0].get('rank_score', 0.0)
            } if ranked_vendors else None
        } 