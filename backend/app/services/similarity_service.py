"""
Similarity Service Module
Handles text vectorization and similarity computation using TF-IDF and Cosine Similarity
"""

import pickle
import os
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from app.utils.config import Config

logger = logging.getLogger(__name__)


class SimilarityService:
    """
    Similarity Service
    Computes similarity scores between resumes and job descriptions
    """
    
    def __init__(self):
        """Initialize vectorizer and SVD transformer"""
        self.tfidf_vectorizer = None
        self.svd_transformer = None
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models from disk"""
        try:
            # Load TF-IDF vectorizer
            tfidf_path = os.path.join(Config.MODELS_FOLDER, 'tfidf_vectorizer.pkl')
            if os.path.exists(tfidf_path):
                with open(tfidf_path, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
                logger.info("✓ Loaded TF-IDF vectorizer")
            else:
                logger.warning("TF-IDF vectorizer not found, will create new one")
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=Config.TF_IDF_MAX_FEATURES,
                    stop_words='english',
                    ngram_range=(1, 2)
                )
            
            # Load SVD transformer
            svd_path = os.path.join(Config.MODELS_FOLDER, 'svd_transformer.pkl')
            if os.path.exists(svd_path):
                with open(svd_path, 'rb') as f:
                    self.svd_transformer = pickle.load(f)
                logger.info("✓ Loaded SVD transformer")
            else:
                logger.warning("SVD transformer not found, will create new one")
                self.svd_transformer = TruncatedSVD(
                    n_components=Config.SVD_N_COMPONENTS,
                    random_state=42
                )
        
        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
    
    def train_models(self, documents):
        """
        Train TF-IDF and SVD models on document corpus
        Should be called during initial setup with sample documents
        
        Args:
            documents (list): List of text documents
        
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Training models on {len(documents)} documents")
            
            # Train TF-IDF vectorizer
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
            logger.info(f"TF-IDF matrix shape: {tfidf_matrix.shape}")
            
            # Train SVD transformer
            self.svd_transformer.fit(tfidf_matrix)
            logger.info(f"SVD explained variance: {sum(self.svd_transformer.explained_variance_ratio_):.4f}")
            
            # Save models
            self.save_models()
            
            logger.info("✓ Models trained and saved successfully")
            return True
        
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            return False
    
    def save_models(self):
        """Save trained models to disk"""
        try:
            os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
            
            # Save TF-IDF vectorizer
            with open(os.path.join(Config.MODELS_FOLDER, 'tfidf_vectorizer.pkl'), 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
            
            # Save SVD transformer
            with open(os.path.join(Config.MODELS_FOLDER, 'svd_transformer.pkl'), 'wb') as f:
                pickle.dump(self.svd_transformer, f)
            
            logger.info("✓ Models saved successfully")
            return True
        
        except Exception as e:
            logger.error(f"Model saving failed: {str(e)}")
            return False
    
    def vectorize_text(self, text, use_svd=True):
        """
        Convert text to TF-IDF vector representation
        
        Args:
            text (str): Input text
            use_svd (bool): Apply SVD dimensionality reduction
        
        Returns:
            ndarray: Vector representation or None if failed
        """
        try:
            if not self.tfidf_vectorizer:
                logger.error("TF-IDF vectorizer not initialized")
                return None
            
            # Vectorize text
            vector = self.tfidf_vectorizer.transform([text])
            
            # Apply SVD if requested
            if use_svd and self.svd_transformer:
                vector = self.svd_transformer.transform(vector)
            
            return vector
        
        except Exception as e:
            logger.error(f"Text vectorization failed: {str(e)}")
            return None
    
    def compute_similarity(self, text1, text2):
        """
        Compute cosine similarity between two texts
        
        Args:
            text1 (str): First text (resume)
            text2 (str): Second text (job description)
        
        Returns:
            float: Similarity score (0-1)
        """
        try:
            # Vectorize both texts
            vec1 = self.vectorize_text(text1)
            vec2 = self.vectorize_text(text2)
            
            if vec1 is None or vec2 is None:
                logger.error("Vectorization failed")
                return 0.0
            
            # Compute cosine similarity
            similarity = cosine_similarity(vec1, vec2)[0][0]
            
            logger.debug(f"Similarity score: {similarity:.4f}")
            return float(similarity)
        
        except Exception as e:
            logger.error(f"Similarity computation failed: {str(e)}")
            return 0.0
    
    def batch_compute_similarity(self, resume_text, job_descriptions):
        """
        Compute similarity between one resume and multiple job descriptions
        
        Args:
            resume_text (str): Resume text
            job_descriptions (list): List of job description texts
        
        Returns:
            list: List of (job_desc, similarity_score) tuples sorted by score
        """
        try:
            resume_vec = self.vectorize_text(resume_text)
            
            if resume_vec is None:
                return []
            
            similarities = []
            
            for job_desc in job_descriptions:
                job_vec = self.vectorize_text(job_desc)
                
                if job_vec is not None:
                    similarity = cosine_similarity(resume_vec, job_vec)[0][0]
                    similarities.append((job_desc, float(similarity)))
            
            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Computed similarity for {len(similarities)} job descriptions")
            return similarities
        
        except Exception as e:
            logger.error(f"Batch similarity computation failed: {str(e)}")
            return []
