from app.core.extractor import (
    TextExtractor, SectionDetector, ContactExtractor, SkillExtractor,
    EducationExtractor, ExperienceExtractor, OrganizationFilter, OutputCleaner, ResumeData
)
import json

# Replicate exact parse() method logic
file_path = 'final resume.pdf'
text_extractor = TextExtractor()
section_detector = SectionDetector()
contact_extractor = ContactExtractor()
skill_extractor = SkillExtractor()
education_extractor = EducationExtractor()
experience_extractor = ExperienceExtractor()
org_filter = OrganizationFilter()
output_cleaner = OutputCleaner()

# STEP 1: Text Extraction  
print("Step 1: Text Extraction")
raw_text = text_extractor.extract(file_path)
text = text_extractor.clean_text(raw_text)
print(f"  Extracted {len(text)} characters")

# STEP 2: Section Detection
print("\nStep 2: Section Detection")
sections = section_detector.detect_sections(text)
print(f"  Detected sections: {list(sections.keys())}")

# STEP 3: Contact Extraction
print("\nStep 3: Contact Extraction")
contact_text = sections.get("contact", "") + " " + text[:500]
name, email, phones = contact_extractor.extract_contact(contact_text)
print(f"  Contact: {name} | {email} | {phones}")

# STEP 4: Skill Extraction
print("\nStep 4: Skill Extraction")
skills_section = sections.get("skills", "") or text
skills = skill_extractor.extract_skills(skills_section)
print(f"  Skills found: {len(skills)}")

# STEP 5: Education Extraction
print("\nStep 5: Education Extraction")
education_section = sections.get("education", "")
education = education_extractor.extract_education(education_section)
print(f"  Education entries: {len(education)}")
print(f"  Education data: {education}")

# STEP 6: Experience Extraction
print("\nStep 6: Experience Extraction")
experience_section = sections.get("experience", "")
experience = experience_extractor.extract_experience(experience_section)
print(f"  Experience entries: {len(experience)}")
print(f"  Experience data (first 100 chars): {str(experience)[:100]}")

# STEP 7: Organization Filtering
print("\nStep 7: Organization Filtering")
org_text = experience_section + " " + sections.get("projects", "")
organizations = org_filter.filter_organizations(org_text)
print(f"  Organizations found: {len(organizations)}")

# STEP 8: Clean Final Output
print("\nStep 8: Creating ResumeData")
resume_data = ResumeData(
    name=name,
    email=email,
    phone=phones[0] if phones else "",
    skills=skills,
    education=education,
    experience=experience,
    organizations=organizations,
    summary=sections.get("summary", "")[:500]
)
print(f"  ResumeData.education: {resume_data.education}")
print(f"  ResumeData.experience: {resume_data.experience}")
print(f"  ResumeData.organizations: {resume_data.organizations}")

print("\nStep 8: Clean Final Output")
output = output_cleaner.clean_output(resume_data)
print(f"  Output keys: {list(output.keys())}")
print(f"  Output: {json.dumps(output, indent=2, default=str)[:500]}")
