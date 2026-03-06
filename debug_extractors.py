from app.core.extractor import TextExtractor, SectionDetector, ContactExtractor, EducationExtractor, ExperienceExtractor
import json

# Extract and detect sections
extractor = TextExtractor()
text = extractor.extract('final resume.pdf')
detector = SectionDetector()
sections = detector.detect_sections(text)

# Test ContactExtractor
contact_ext = ContactExtractor()
name, email, phones = contact_ext.extract_contact(text)
print('=== CONTACT EXTRACTION ===')
print(f"Name: {name}")
print(f"Email: {email}")
print(f"Phones: {phones}")

# Test EducationExtractor
edu_ext = EducationExtractor()
education = edu_ext.extract_education(sections.get('education', ''))
print('\n=== EDUCATION EXTRACTION ===')
print(f'Found {len(education)} education entries:')
print(json.dumps(education, indent=2))

# Test ExperienceExtractor
exp_ext = ExperienceExtractor()
experience = exp_ext.extract_experience(sections.get('experience', ''))
print('\n=== EXPERIENCE EXTRACTION ===')
print(f'Found {len(experience)} experience entries:')
print(json.dumps(experience, indent=2))
