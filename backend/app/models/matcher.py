"""
Matcher Model Module
ML classifier for resume-job matching using SVM
"""

import pickle
import os
import logging
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from app.utils.config import Config

logger = logging.getLogger(__name__)


class MatcherModel:
    """
    Resume-Job Matcher ML Model
    Uses SVM classifier to determine if resume matches job description
    """
    
    def __init__(self):
        """Initialize SVM model and scaler"""
        self.svm_model = None
        self.scaler = None
        self.is_trained = False
        self.load_model()
    
    def load_model(self):
        """Load pre-trained SVM model from disk"""
        try:
            model_path = os.path.join(Config.MODELS_FOLDER, 'svm_model.pkl')
            
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.svm_model = pickle.load(f)
                    self.is_trained = True
                logger.info("✓ Loaded pre-trained SVM model")
            else:
                logger.warning("SVM model not found, creating new one")
                self.svm_model = SVC(
                    kernel=Config.SVM_KERNEL,
                    C=1.0,
                    probability=True,
                    random_state=42
                )
            
            # Load scaler
            scaler_path = os.path.join(Config.MODELS_FOLDER, 'scaler.pkl')
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("✓ Loaded feature scaler")
            else:
                self.scaler = StandardScaler()
        
        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
            self.svm_model = SVC(kernel=Config.SVM_KERNEL, probability=True, random_state=42)
            self.scaler = StandardScaler()
    
    def train(self, X_train, y_train):
        """
        Train SVM classifier on labeled data
        
        Args:
            X_train (ndarray): Training features (n_samples, n_features)
            y_train (ndarray): Training labels (0 = no match, 1 = match)
        
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Training SVM on {len(X_train)} samples")
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X_train)
            
            # Train model
            self.svm_model.fit(X_scaled, y_train)
            
            # Calculate training accuracy
            train_accuracy = self.svm_model.score(X_scaled, y_train)
            logger.info(f"✓ SVM trained - Training accuracy: {train_accuracy:.4f}")
            
            # Save models
            self.save_model()
            
            self.is_trained = True
            return True
        
        except Exception as e:
            logger.error(f"SVM training failed: {str(e)}")
            return False
    
    def predict(self, features):
        """
        Predict match probability for given features
        
        Args:
            features (dict or ndarray): Feature vector
        
        Returns:
            dict: Prediction results with probability
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning default prediction")
            return {'match': False, 'probability': 0.0}
        
        try:
            # Convert dict to array if needed
            if isinstance(features, dict):
                features = np.array([list(features.values())])
            elif isinstance(features, list):
                features = np.array([features])
            else:
                features = features.reshape(1, -1)
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Predict
            prediction = self.svm_model.predict(features_scaled)[0]
            
            # Get probability
            probabilities = self.svm_model.predict_proba(features_scaled)[0]
            match_probability = float(probabilities[1])  # Probability of class 1 (match)
            
            logger.debug(f"Prediction: {prediction}, Probability: {match_probability:.4f}")
            
            return {
                'match': bool(prediction),
                'probability': match_probability,
                'confidence': max(probabilities)
            }
        
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return {'match': False, 'probability': 0.0, 'error': str(e)}
    
    def batch_predict(self, features_list):
        """
        Batch predict for multiple feature vectors
        
        Args:
            features_list (list): List of feature vectors or dicts
        
        Returns:
            list: List of prediction results
        """
        try:
            predictions = []
            
            for features in features_list:
                result = self.predict(features)
                predictions.append(result)
            
            logger.info(f"Batch prediction completed for {len(predictions)} items")
            return predictions
        
        except Exception as e:
            logger.error(f"Batch prediction failed: {str(e)}")
            return []
    
    def save_model(self):
        """Save trained model and scaler to disk"""
        try:
            os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
            
            # Save SVM model
            with open(os.path.join(Config.MODELS_FOLDER, 'svm_model.pkl'), 'wb') as f:
                pickle.dump(self.svm_model, f)
            
            # Save scaler
            with open(os.path.join(Config.MODELS_FOLDER, 'scaler.pkl'), 'wb') as f:
                pickle.dump(self.scaler, f)
            
            logger.info("✓ Models saved successfully")
            return True
        
        except Exception as e:
            logger.error(f"Model saving failed: {str(e)}")
            return False
    
    def get_model_info(self):
        """Get information about the model"""
        return {
            'is_trained': self.is_trained,
            'model_type': 'SVM',
            'kernel': Config.SVM_KERNEL if self.svm_model else None,
            'feature_scaler': 'StandardScaler'
        }
