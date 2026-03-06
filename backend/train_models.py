"""
Model Training Script
Trains and saves ML models for resume matching
Run this script to initialize the models

Usage:
    python train_models.py
"""

import logging
import os
from app.services.nlp_service import NLPService
from app.services.similarity_service import SimilarityService
from app.models.matcher import MatcherModel
from app.utils.config import Config
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_similarity_models():
    """Train TF-IDF and SVD models on sample documents"""
    
    logger.info("=" * 60)
    logger.info("Training Similarity Models (TF-IDF + SVD)")
    logger.info("=" * 60)
    
    # Sample training documents (in production, use real job descriptions)
    sample_documents = [
        """
        Senior Python Developer
        We are looking for an experienced Python developer with expertise in Flask and Django.
        Required: 5+ years experience with Python, REST APIs, PostgreSQL, Git.
        Skills: Python, Flask, Django, FastAPI, SQL, AWS, Docker, Kubernetes.
        """,
        
        """
        Full Stack JavaScript Developer
        Build modern web applications with React and Node.js.
        Requirements: JavaScript, TypeScript, React, Express.js, MongoDB, Redis.
        Nice to have: GraphQL, Microservices, DevOps, CI/CD pipelines.
        """,
        
        """
        Data Science Engineer
        Work with machine learning models and data pipelines.
        Required: Python, Pandas, NumPy, Scikit-learn, TensorFlow, PyTorch.
        Experience: SQL, Apache Spark, AWS/GCP, Statistical Analysis.
        """,
        
        """
        DevOps Engineer
        Manage cloud infrastructure and deployment pipelines.
        Skills: Docker, Kubernetes, AWS, Terraform, CI/CD, Jenkins, GitLab.
        Experience: Linux, Infrastructure as Code, Monitoring, Security.
        """,
        
        """
        Java Enterprise Developer
        Develop scalable enterprise applications.
        Required: Java 11+, Spring Framework, Microservices, REST APIs.
        Technologies: Spring Boot, Docker, Kubernetes, PostgreSQL, RabbitMQ.
        """,
        
        """
        Mobile App Developer (iOS/Android)
        Create native and cross-platform mobile applications.
        Skills: Swift, Kotlin, React Native, Flutter, Firebase.
        Experience: App Store, Play Store, User Experience, Performance.
        """,
        
        """
        Machine Learning Engineer
        Build and deploy ML models for production.
        Required: Python, TensorFlow, PyTorch, Deep Learning, NLP.
        Skills: Computer Vision, NLP, Time Series, Model Deployment, MLOps.
        """,
        
        """
        Cloud Architect
        Design and implement cloud solutions.
        Experience: AWS, Azure, GCP, Networking, Security, Cost Optimization.
        Skills: Terraform, CloudFormation, Infrastructure Planning.
        """,
    ]
    
    try:
        similarity_service = SimilarityService()
        
        # Train models
        success = similarity_service.train_models(sample_documents)
        
        if success:
            logger.info("✓ TF-IDF Vectorizer trained and saved")
            logger.info("✓ SVD Transformer trained and saved")
            logger.info(f"✓ Models saved to: {Config.MODELS_FOLDER}")
            return True
        else:
            logger.error("✗ Model training failed")
            return False
    
    except Exception as e:
        logger.error(f"✗ Error training models: {str(e)}", exc_info=True)
        return False


def train_ml_classifier():
    """Train SVM classification model"""
    
    logger.info("\n" + "=" * 60)
    logger.info("Training ML Classifier (SVM)")
    logger.info("=" * 60)
    
    try:
        # Sample training data
        # In production: collect real resume-job pairs and label them
        # 1 = good match, 0 = poor match
        
        sample_features = [
            # Good matches
            {'num_skills': 12, 'num_entities': 8, 'num_education': 2,
             'has_email': 1, 'has_phone': 1, 'text_length': 2000, 'num_words': 350},
            {'num_skills': 15, 'num_entities': 10, 'num_education': 3,
             'has_email': 1, 'has_phone': 1, 'text_length': 2500, 'num_words': 420},
            {'num_skills': 10, 'num_entities': 7, 'num_education': 2,
             'has_email': 1, 'has_phone': 0, 'text_length': 1800, 'num_words': 300},
            
            # Poor matches
            {'num_skills': 2, 'num_entities': 2, 'num_education': 1,
             'has_email': 0, 'has_phone': 0, 'text_length': 500, 'num_words': 80},
            {'num_skills': 3, 'num_entities': 3, 'num_education': 1,
             'has_email': 1, 'has_phone': 0, 'text_length': 700, 'num_words': 120},
            {'num_skills': 1, 'num_entities': 1, 'num_education': 0,
             'has_email': 0, 'has_phone': 0, 'text_length': 400, 'num_words': 60},
        ]
        
        # Convert to numpy array
        X_train = np.array([list(f.values()) for f in sample_features])
        y_train = np.array([1, 1, 1, 0, 0, 0])  # Labels
        
        matcher = MatcherModel()
        
        # Train the model
        success = matcher.train(X_train, y_train)
        
        if success:
            logger.info("✓ SVM Classifier trained")
            logger.info("✓ Feature Scaler fitted")
            logger.info(f"✓ Models saved to: {Config.MODELS_FOLDER}")
            return True
        else:
            logger.error("✗ Classifier training failed")
            return False
    
    except Exception as e:
        logger.error(f"✗ Error training classifier: {str(e)}", exc_info=True)
        return False


def verify_nlp_model():
    """Verify spaCy NLP model is available"""
    
    logger.info("\n" + "=" * 60)
    logger.info("Verifying NLP Model")
    logger.info("=" * 60)
    
    try:
        nlp_service = NLPService()
        
        if nlp_service.nlp:
            test_text = "John Smith works at Google as a Python developer."
            entities = nlp_service.extract_entities(test_text)
            skills = nlp_service.extract_skills("Python, Flask, Docker, Kubernetes")
            
            logger.info("✓ spaCy NLP model loaded")
            logger.info(f"✓ Extracted entities: {entities}")
            logger.info(f"✓ Extracted skills: {skills}")
            return True
        else:
            logger.error("✗ spaCy model not loaded")
            logger.error("Run: python -m spacy download en_core_web_sm")
            return False
    
    except Exception as e:
        logger.error(f"✗ Error verifying NLP: {str(e)}", exc_info=True)
        return False


def main():
    """Main training routine"""
    
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "AI RESUME MATCHER - MODEL TRAINING" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Create required directories
    os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
    os.makedirs(Config.LOGS_FOLDER, exist_ok=True)
    
    logger.info(f"Models directory: {Config.MODELS_FOLDER}")
    logger.info(f"Logs directory: {Config.LOGS_FOLDER}")
    
    # Train models
    results = {
        'nlp_verification': verify_nlp_model(),
        'similarity_models': train_similarity_models(),
        'ml_classifier': train_ml_classifier(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✓ SUCCESS" if result else "✗ FAILED"
        print(f"{name.replace('_', ' ').title()}: {status}")
    
    all_success = all(results.values())
    
    print("=" * 60)
    
    if all_success:
        print("\n✨ All models trained successfully!")
        print("You can now start the application with: python run.py\n")
    else:
        print("\n⚠️  Some models failed to train.")
        print("Check the errors above and try again.\n")
    
    return all_success


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
