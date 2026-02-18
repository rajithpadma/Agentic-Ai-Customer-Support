"""
Vision Module for Agentic AI Customer Support
FIXED: Loads models based on product name pattern: {ProductName}_good_bad_classifier.h5
Example: AirChef Fryo_good_bad_classifier.h5, Samsung TV_good_bad_classifier.h5
"""
import os
import re
import numpy as np
from typing import Dict, List, Optional
from PIL import Image
import io
import base64
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import IMAGE_CATEGORIES, CONFIDENCE_THRESHOLD

try:
    from tensorflow.keras.models import load_model
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("Warning: TensorFlow not installed. Vision features will use mock predictions.")


class VisionAnalyzer:
    """
    FIXED: Analyzes product images using product-specific models
    Model naming: {ProductName}_good_bad_classifier.h5
    """
    
    def __init__(self):
        self.model_dir = os.path.join(os.path.dirname(__file__), "model")
        self.models: Dict[str, any] = {}
        self.model_product_map: Dict[str, str] = {}  # Maps product name to model key
        self.categories = IMAGE_CATEGORIES
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        self.image_size = (224, 224)
        
        self._load_models()
    
    def _normalize_product_name(self, product_name: str) -> str:
        """
        Normalize product name for matching
        Removes special characters, extra spaces, converts to lowercase
        """
        if not product_name:
            return ""
        
        # Convert to lowercase and strip
        normalized = product_name.lower().strip()
        
        # Remove special characters except spaces and underscores
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _load_models(self):
        """
        Load all H5 models from the model directory
        Expected format: {ProductName}_good_bad_classifier.h5
        """
        if not TENSORFLOW_AVAILABLE:
            print("⚠️  TensorFlow not available - using mock predictions")
            return
        
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir, exist_ok=True)
            print(f"✅ Created model directory: {self.model_dir}")
            print(f"📁 Place your models here with format: ProductName_good_bad_classifier.h5")
            return
        
        model_files = [f for f in os.listdir(self.model_dir) if f.endswith('.h5')]
        
        if not model_files:
            print(f"⚠️  No H5 models found in: {self.model_dir}")
            print(f"📁 Place your models with format: ProductName_good_bad_classifier.h5")
            return
        
        print(f"\n{'='*60}")
        print(f"  LOADING VISION MODELS")
        print(f"{'='*60}\n")
        
        for filename in model_files:
            model_path = os.path.join(self.model_dir, filename)
            
            try:
                # Extract product name from filename
                # Format: ProductName_good_bad_classifier.h5
                if '_good_bad_classifier.h5' in filename:
                    product_name = filename.replace('_good_bad_classifier.h5', '')
                    normalized_name = self._normalize_product_name(product_name)
                    
                    # Load the model
                    model = load_model(model_path)
                    
                    # Store with both original and normalized names
                    model_key = product_name
                    self.models[model_key] = model
                    self.model_product_map[normalized_name] = model_key
                    
                    print(f"✅ Loaded: {filename}")
                    print(f"   Product: {product_name}")
                    print(f"   Normalized: {normalized_name}\n")
                    
                else:
                    # Try to load anyway but with warning
                    model_name = filename.replace('.h5', '')
                    model = load_model(model_path)
                    self.models[model_name] = model
                    print(f"⚠️  Loaded: {filename} (non-standard naming)")
                    print(f"   Expected format: ProductName_good_bad_classifier.h5\n")
                    
            except Exception as e:
                print(f"❌ Failed to load {filename}: {e}\n")
        
        if self.models:
            print(f"{'='*60}")
            print(f"  ✅ Total models loaded: {len(self.models)}")
            print(f"{'='*60}\n")
        else:
            print(f"❌ No models loaded successfully")
            print(f"📁 Place models in: {self.model_dir}")
            print(f"📝 Format: ProductName_good_bad_classifier.h5\n")
    
    def _find_model_for_product(self, product_id: str = None, product_name: str = None) -> Optional[any]:
        """
        Find the appropriate model for a given product
        Uses product_name matching with normalization
        """
        if not self.models:
            return None
        
        # If product_name provided, try to match with loaded models
        if product_name:
            normalized_input = self._normalize_product_name(product_name)
            
            # Direct match
            if normalized_input in self.model_product_map:
                model_key = self.model_product_map[normalized_input]
                print(f"✅ Found exact model match for '{product_name}': {model_key}")
                return self.models[model_key]
            
            # Partial match - check if product name contains any model name
            for norm_name, model_key in self.model_product_map.items():
                if norm_name in normalized_input or normalized_input in norm_name:
                    print(f"✅ Found partial model match for '{product_name}': {model_key}")
                    return self.models[model_key]
            
            # Try fuzzy matching with product name tokens
            input_tokens = set(normalized_input.split())
            best_match = None
            best_score = 0
            
            for norm_name, model_key in self.model_product_map.items():
                model_tokens = set(norm_name.split())
                # Calculate overlap
                overlap = len(input_tokens & model_tokens)
                if overlap > best_score:
                    best_score = overlap
                    best_match = model_key
            
            if best_match and best_score > 0:
                print(f"✅ Found fuzzy model match for '{product_name}': {best_match} (score: {best_score})")
                return self.models[best_match]
        
        # If product_id provided, try to get product details from database
        if product_id:
            try:
                from src.database.database import db_manager
                product = db_manager.get_product_by_id(product_id)
                if product:
                    db_product_name = product.get('product_name', product.get('name', ''))
                    if db_product_name:
                        print(f"📦 Retrieved product name from DB: {db_product_name}")
                        return self._find_model_for_product(None, db_product_name)
            except Exception as e:
                print(f"⚠️  Could not fetch product from database: {e}")
        
        # Fallback to first available model
        first_model_key = list(self.models.keys())[0]
        print(f"⚠️  No specific model found, using default: {first_model_key}")
        return self.models[first_model_key]
    
    def analyze_image(self, image_input: any, product_id: str = None, 
                     product_name: str = None, model_name: str = None) -> Dict:
        """
        FIXED: Analyze an image using product-specific model
        
        Args:
            image_input: Can be file path, base64 string, bytes, or PIL Image
            product_id: Product ID to select appropriate model
            product_name: Product name to select appropriate model (REQUIRED for best results)
            model_name: Specific model to use (optional, overrides auto-selection)
        
        Returns:
            Dict with category, confidence, and details
        """
        try:
            img = self._load_image(image_input)
            if img is None:
                return {"error": "Failed to load image"}
            
            print(f"\n{'='*60}")
            print(f"  IMAGE ANALYSIS")
            print(f"{'='*60}")
            print(f"Product ID: {product_id or 'Not provided'}")
            print(f"Product Name: {product_name or 'Not provided'}")
            print(f"{'='*60}\n")
            
            # Select appropriate model
            if model_name and model_name in self.models:
                model = self.models[model_name]
                print(f"✅ Using specified model: {model_name}")
            else:
                model = self._find_model_for_product(product_id, product_name)
            
            # If no model available, use mock
            if not model:
                print("⚠️  No model available, using mock prediction\n")
                return self._mock_prediction(img, product_id, product_name)
            
            img_array = self._preprocess_image(img)
            predictions = model.predict(img_array, verbose=0)
            result = self._process_predictions(predictions)
            
            # Add product context to result
            result["product_id"] = product_id
            result["product_name"] = product_name
            result["model_used"] = "Product-specific model"
            
            print(f"✅ Analysis complete: {result['category']} ({result['confidence']:.1%} confidence)\n")
            
            return result
            
        except Exception as e:
            print(f"❌ Error analyzing image: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _load_image(self, image_input: any) -> Optional[Image.Image]:
        """Load image from various input types"""
        try:
            if isinstance(image_input, str):
                if os.path.exists(image_input):
                    return Image.open(image_input).convert('RGB')
                elif image_input.startswith('data:image'):
                    base64_data = image_input.split(',')[1]
                    image_bytes = base64.b64decode(base64_data)
                    return Image.open(io.BytesIO(image_bytes)).convert('RGB')
                else:
                    image_bytes = base64.b64decode(image_input)
                    return Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            elif isinstance(image_input, bytes):
                return Image.open(io.BytesIO(image_input)).convert('RGB')
            
            elif isinstance(image_input, Image.Image):
                return image_input.convert('RGB')
            
            return None
                
        except Exception as e:
            print(f"Error loading image: {e}")
            return None
    
    def _preprocess_image(self, img: Image.Image) -> np.ndarray:
        """Preprocess image for model input"""
        img = img.resize(self.image_size)
        img_array = np.array(img)
        img_array = img_array.astype('float32') / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        return img_array
    
    def _process_predictions(self, predictions: np.ndarray) -> Dict:
        """Process model predictions into readable format"""
        predicted_class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class_idx])
        
        if predicted_class_idx < len(self.categories):
            category = self.categories[predicted_class_idx]
        else:
            category = "unknown"
        
        result = {
            "category": category,
            "confidence": confidence,
            "meets_threshold": confidence >= self.confidence_threshold,
            "all_predictions": {
                self.categories[i]: float(predictions[0][i])
                for i in range(min(len(predictions[0]), len(self.categories)))
            }
        }
        
        result["recommendation"] = self._get_recommendation(category, confidence)
        return result
    
    def _mock_prediction(self, img: Image.Image, product_id: str = None, 
                        product_name: str = None) -> Dict:
        """Generate mock prediction when no model is available"""
        width, height = img.size
        np.random.seed(int(width * height) % 1000)
        probs = np.random.dirichlet(np.ones(len(self.categories)))
        predicted_idx = np.argmax(probs)
        
        return {
            "category": self.categories[predicted_idx],
            "confidence": float(probs[predicted_idx]),
            "meets_threshold": probs[predicted_idx] >= self.confidence_threshold,
            "all_predictions": {
                cat: float(probs[i]) for i, cat in enumerate(self.categories)
            },
            "recommendation": self._get_recommendation(
                self.categories[predicted_idx], 
                probs[predicted_idx]
            ),
            "product_id": product_id,
            "product_name": product_name,
            "model_used": "Mock prediction (no model loaded)",
            "is_mock": True,
            "warning": "Using mock predictions - no H5 model loaded for this product"
        }
    
    def _get_recommendation(self, category: str, confidence: float) -> str:
        """Get recommendation based on image category"""
        recommendations = {
            "damaged_product": "Product appears damaged. Eligible for return or replacement.",
            "wrong_product": "Wrong product delivered. Eligible for immediate replacement.",
            "missing_parts": "Product has missing parts. Contact support for replacement parts.",
            "quality_issue": "Quality issue detected. May be eligible for return based on policy.",
            "packaging_damage": "Packaging is damaged. Check product condition.",
            "other": "Issue detected. Please describe the problem for assistance."
        }
        
        if confidence < self.confidence_threshold:
            return f"Low confidence ({confidence:.1%}). Please provide more details about the issue."
        
        return recommendations.get(category, "Please describe your issue for assistance.")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.models.keys())
    
    def get_model_info(self) -> Dict:
        """Get detailed information about loaded models"""
        return {
            "total_models": len(self.models),
            "models": list(self.models.keys()),
            "product_mappings": self.model_product_map,
            "model_directory": self.model_dir
        }
    
    def get_categories(self) -> List[str]:
        """Get list of supported categories"""
        return self.categories


# Create singleton instance
vision_analyzer = VisionAnalyzer()