"""
Resume Model Module
Defines the Resume data model and processing pipeline
"""

import logging
import resume_parser_production
from app.services.file_service import FileService
from app.utils.validators import validate_text_length

logger = logging.getLogger(__name__)


class ResumeModel:
    """
    Resume Data Model
    Represents a resume with parsed information and computed features
    MVC Pattern - Model layer
    """
    
    def __init__(self, filepath=None, resume_text=None):
        """
        Initialize resume model
        
        Args:
            filepath (str): Path to resume file
            resume_text (str): Pre-extracted resume text
        """
        self.filepath = filepath
        self.raw_text = resume_text
        self.cleaned_text = None
        
        # Extracted information
        self.entities = {}
        self.skills = []
        self.contact_info = {}
        self.education = []
        
        # Features for matching
        self.features = {}
        self.similarity_scores = {}  # Job description -> similarity score mapping
        
        # Metadata
        self.parsed = False
        self.error_message = None
    
    def load_from_file(self):
        """
        Load and extract text from resume file
        
        Returns:
            bool: Success status
        """
        if not self.filepath:
            self.error_message = "No filepath provided"
            return False
        
        try:
            success, content = FileService.extract_text(self.filepath)
            
            if success:
                self.raw_text = content
                logger.info(f"✓ Loaded resume: {len(self.raw_text)} characters")
                return True
            else:
                self.error_message = content
                logger.error(f"Failed to load resume: {content}")
                return False
        
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Error loading resume: {str(e)}")
            return False
    
    def parse(self):
        """
        Parse resume and extract information using production-grade NLP pipeline
        
        Returns:
            bool: Success status
        """
        if not self.raw_text:
            self.error_message = "No resume text available"
            return False
        
        try:
            # Validate text length
            is_valid, error = validate_text_length(self.raw_text, min_length=100)
            if not is_valid:
                self.error_message = error
                return False
            
            # Use new production-grade parser
            parse_result = resume_parser_production.parse_resume(self.raw_text)
            
            # Extract results from comprehensive parsing
            self.cleaned_text = self.raw_text  # Use raw text since new parser doesn't clean
            
            # Map parsed results to model attributes
            if parse_result.name:
                self.contact_info['name'] = parse_result.name
            
            self.contact_info['emails'] = [parse_result.email] if parse_result.email else []
            self.contact_info['phones'] = [parse_result.phone] if parse_result.phone else []
            
            # Skills are already clean and deduplicated from comprehensive parsing
            self.skills = parse_result.skills
            
            # Education is structured (list of dicts with degree, institution, year)
            self.education = [edu.to_dict() if hasattr(edu, 'to_dict') else {
                'degree': edu.degree,
                'institution': edu.institution,
                'year_range': edu.year_range,
            } for edu in parse_result.education]
            
            # Store organizations and locations in entities
            self.entities = {
                'organizations': parse_result.organizations,
                'locations': [],
                'experience': [exp.to_dict() if hasattr(exp, 'to_dict') else {
                    'title': exp.title,
                    'company': exp.company,
                    'location': exp.location,
                    'duration': exp.duration,
                } for exp in parse_result.experience]
            }
            
            self.parsed = True
            logger.info(f"✓ Resume parsed successfully - {len(self.skills)} skills, {len(self.education)} degrees")
            
            return True
        
        except Exception as e:
            self.error_message = f"Parsing error: {str(e)}"
            logger.error(f"Resume parsing failed: {str(e)}")
            return False
    
    def extract_features(self):
        """
        Extract feature vectors for ML models
        
        Returns:
            dict: Feature dictionary
        """
        if not self.parsed:
            logger.warning("Resume must be parsed before extracting features")
            return {}
        
        try:
            self.features = {
                'num_skills': len(self.skills),
                'num_entities': sum(len(ents) for ents in self.entities.values()),
                'num_education': len(self.education),
                'has_email': len(self.contact_info.get('emails', [])) > 0,
                'has_phone': len(self.contact_info.get('phones', [])) > 0,
                'text_length': len(self.cleaned_text),
                'num_words': len(self.cleaned_text.split())
            }
            
            logger.debug(f"Extracted features: {self.features}")
            return self.features
        
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            return {}
    
    def to_dict(self):
        """
        Convert resume to dictionary (for API responses)
        
        Returns:
            dict: Resume data dictionary
        """
        return {
            'filepath': self.filepath,
            'parsed': self.parsed,
            'raw_text': self.raw_text,
            'cleaned_text': self.cleaned_text,
            'skills': self.skills,
            'contact_info': self.contact_info,
            'education': self.education,
            'entities': self.entities,
            'features': self.features,
            'similarity_scores': self.similarity_scores,
            'error': self.error_message
        }
