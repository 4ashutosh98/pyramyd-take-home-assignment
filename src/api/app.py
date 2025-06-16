from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
import logging

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processing.data_loader import DataLoader
from similarity.feature_matcher import FeatureMatcher
from ranking.vendor_ranker import VendorRanker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vendor Qualification System",
    description="A system to qualify and rank software vendors based on semantic similarity matching of capabilities",
    version="1.0.0"
)

# Initialize components
try:
    data_loader = DataLoader("data/G2 software - CRM Category Product Overviews.csv")
    logger.info("Data loader initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize data loader: {e}")
    data_loader = None

feature_matcher = FeatureMatcher(similarity_threshold=0.5)
vendor_ranker = VendorRanker(feature_weight=0.7, rating_weight=0.3)

class VendorQuery(BaseModel):
    software_category: str
    capabilities: List[str]
    similarity_threshold: Optional[float] = 0.5
    top_n: Optional[int] = 10
    include_explanations: Optional[bool] = False

class VendorQualificationResponse(BaseModel):
    query: VendorQuery
    results: dict
    summary: dict

@app.post("/vendor_qualification", response_model=dict)
async def qualify_vendors(query: VendorQuery):
    """
    Qualify and rank vendors based on category and capabilities using semantic similarity matching.
    
    This endpoint:
    1. Filters vendors by software category
    2. Performs semantic similarity matching between desired capabilities and vendor features
    3. Selects vendors with features that meet the similarity threshold
    4. Ranks vendors based on similarity scores and ratings
    5. Returns top N qualified vendors
    
    Args:
        query (VendorQuery): Query containing software category, capabilities, and options
        
    Returns:
        dict: Comprehensive results including ranked vendors, matches, and analysis
    """
    try:
        if data_loader is None:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        logger.info(f"Processing vendor qualification query: {query.dict()}")
        
        # Update feature matcher threshold if provided
        if query.similarity_threshold:
            feature_matcher.similarity_threshold = query.similarity_threshold
        
        # Step 1: Filter vendors by category and find capability matches
        matching_results = feature_matcher.filter_vendors_by_category_and_capabilities(
            dataframe=data_loader.preprocessed_dataset,
            software_category=query.software_category,
            capabilities=query.capabilities
        )
        
        if not matching_results['matching_vendors']:
            return {
                "query": query.dict(),
                "results": {
                    "ranked_vendors": [],
                    "total_qualified_vendors": 0,
                    "message": f"No vendors found matching capabilities {query.capabilities} in category '{query.software_category}' with similarity threshold {query.similarity_threshold}"
                },
                "summary": matching_results,
                "analysis": {
                    "threshold_impact": f"Consider lowering similarity threshold (currently {query.similarity_threshold}) to find more matches",
                    "suggestions": [
                        "Try broader capability terms",
                        "Check if the software category exists in the dataset",
                        "Lower the similarity threshold to 0.4-0.5"
                    ]
                }
            }
        
        # Step 2: Add rating information to vendor data (from original dataset)
        enhanced_vendors = {}
        for vendor_key, vendor_data in matching_results['matching_vendors'].items():
            # Find rating from original data
            product_name = vendor_data['product_name']
            original_data = data_loader.data[data_loader.data['product_name'] == product_name]
            
            if not original_data.empty:
                rating = original_data.iloc[0].get('rating', 0.0)
                vendor_data['rating'] = rating
            else:
                vendor_data['rating'] = 0.0
            
            enhanced_vendors[vendor_key] = vendor_data
        
        # Step 3: Rank vendors
        ranked_vendors = vendor_ranker.rank_vendors(enhanced_vendors, top_n=query.top_n)
        
        # Step 4: Add explanations if requested
        if query.include_explanations:
            ranked_vendors = vendor_ranker.add_ranking_explanation(ranked_vendors)
        
        # Step 5: Generate summary statistics
        ranking_summary = vendor_ranker.get_ranking_summary(ranked_vendors)
        
        # Step 6: Prepare comprehensive response
        response = {
            "query": query.dict(),
            "results": {
                "ranked_vendors": ranked_vendors,
                "total_qualified_vendors": len(enhanced_vendors),
                "returned_vendors": len(ranked_vendors)
            },
            "matching_analysis": {
                "total_feature_matches": matching_results['total_matches'],
                "capabilities_searched": matching_results['capabilities_searched'],
                "category_searched": matching_results['category_searched'],
                "similarity_threshold_used": matching_results['similarity_threshold']
            },
            "ranking_summary": ranking_summary,
            "methodology": {
                "similarity_matching": {
                    "description": "Uses TF-IDF vectorization and cosine similarity to match capabilities with feature descriptions",
                    "threshold": query.similarity_threshold,
                    "text_processing": "Combines feature name and description, includes unigrams and bigrams"
                },
                "ranking": {
                    "description": f"Weighted combination of similarity score ({vendor_ranker.feature_weight}) and vendor rating ({vendor_ranker.rating_weight})",
                    "formula": "rank_score = feature_weight * max_similarity + rating_weight * normalized_rating"
                }
            }
        }
        
        # Add detailed matches for debugging if requested
        if query.include_explanations:
            response["detailed_matches"] = matching_results.get('raw_matches', [])[:50]  # Limit to first 50
        
        logger.info(f"Successfully processed query, returning {len(ranked_vendors)} vendors")
        return response
        
    except Exception as e:
        logger.error(f"Error processing vendor qualification: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/categories")
async def get_available_categories():
    """
    Get list of available software categories in the dataset.
    
    Returns:
        dict: Available categories and their counts
    """
    try:
        if data_loader is None:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        categories = data_loader.data['main_category'].value_counts().to_dict()
        
        return {
            "available_categories": categories,
            "total_categories": len(categories),
            "total_products": len(data_loader.data)
        }
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendors")
async def get_vendors_by_category(category: Optional[str] = None):
    """
    Get vendors filtered by category.
    
    Args:
        category (str, optional): Software category to filter by
        
    Returns:
        dict: List of vendors in the specified category
    """
    try:
        if data_loader is None:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        if category:
            filtered_data = data_loader.data[
                data_loader.data['main_category'].str.contains(category, case=False, na=False)
            ]
        else:
            filtered_data = data_loader.data
        
        vendors = filtered_data[['product_name', 'seller', 'rating', 'main_category']].drop_duplicates()
        
        # Convert to records and handle NaN values
        vendors_list = vendors.fillna(0).to_dict('records')
        
        return {
            "vendors": vendors_list,
            "total_vendors": len(vendors),
            "category_filter": category
        }
        
    except Exception as e:
        logger.error(f"Error getting vendors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/features")
async def get_common_features(category: Optional[str] = None, limit: Optional[int] = 20):
    """
    Get most common features in the dataset or by category.
    
    Args:
        category (str, optional): Software category to filter by
        limit (int): Maximum number of features to return
        
    Returns:
        dict: Most common features and their frequencies
    """
    try:
        if data_loader is None:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        if category:
            filtered_data = data_loader.preprocessed_dataset[
                data_loader.preprocessed_dataset['main_category'].str.contains(category, case=False, na=False)
            ]
        else:
            filtered_data = data_loader.preprocessed_dataset
        
        feature_counts = filtered_data['Feature_name'].value_counts().head(limit)
        
        return {
            "common_features": feature_counts.to_dict(),
            "total_unique_features": len(filtered_data['Feature_name'].unique()),
            "category_filter": category
        }
        
    except Exception as e:
        logger.error(f"Error getting features: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "data_loader_status": "initialized" if data_loader else "failed",
        "total_products": len(data_loader.data) if data_loader else 0,
        "total_features": len(data_loader.preprocessed_dataset) if data_loader else 0
    }

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Vendor Qualification System API",
        "version": "1.0.0",
        "description": "Semantic similarity-based vendor qualification and ranking system",
        "endpoints": {
            "POST /vendor_qualification": "Main endpoint for vendor qualification",
            "GET /categories": "Get available software categories",
            "GET /vendors": "Get vendors by category",
            "GET /features": "Get common features",
            "GET /health": "Health check"
        },
        "example_query": {
            "software_category": "CRM Software",
            "capabilities": ["Lead Management", "Email Marketing"],
            "similarity_threshold": 0.5,
            "top_n": 10,
            "include_explanations": True
        }
    } 