"""
Production-Grade Skills Dictionary
Comprehensive list of technical skills for resume matching
"""

SKILLS_DICT = {
    # Python & Web Frameworks
    'Python': ['python', 'py'],
    'Flask': ['flask'],
    'Django': ['django'],
    'FastAPI': ['fastapi', 'fast api'],
    'Tornado': ['tornado'],
    'Pyramid': ['pyramid'],
    
    # JavaScript/Node.js
    'JavaScript': ['javascript', 'js', 'es6', 'es5'],
    'TypeScript': ['typescript', 'ts'],
    'Node.js': ['node.js', 'nodejs', 'node js'],
    'React': ['react', 'reactjs'],
    'Vue.js': ['vue.js', 'vuejs', 'vue js'],
    'Angular': ['angular', 'angularjs'],
    'Express': ['express'],
    
    # Java
    'Java': ['java'],
    'Spring': ['spring', 'spring boot', 'springboot'],
    'Hibernate': ['hibernate'],
    
    # C#/.NET
    'C#': ['c#', 'csharp', 'c sharp'],
    '.NET': ['.net', 'dotnet'],
    'ASP.NET': ['asp.net', 'aspnet'],
    
    # Databases
    'PostgreSQL': ['postgresql', 'postgres', 'pg'],
    'MySQL': ['mysql'],
    'MongoDB': ['mongodb', 'mongo'],
    'Redis': ['redis'],
    'Elasticsearch': ['elasticsearch', 'elastic search'],
    'DynamoDB': ['dynamodb'],
    'Oracle': ['oracle'],
    'SQL Server': ['sql server', 'sqlserver'],
    'SQLite': ['sqlite'],
    
    # Cloud & DevOps
    'AWS': ['aws', 'amazon web services'],
    'Azure': ['azure', 'microsoft azure'],
    'Google Cloud': ['google cloud', 'gcp', 'google cloud platform'],
    'Docker': ['docker'],
    'Kubernetes': ['kubernetes', 'k8s'],
    'Terraform': ['terraform'],
    'Jenkins': ['jenkins'],
    'GitLab CI': ['gitlab ci', 'gitlab-ci'],
    'GitHub Actions': ['github actions'],
    'CircleCI': ['circleci', 'circle ci'],
    
    # Data Science & ML
    'Machine Learning': ['machine learning', 'ml'],
    'TensorFlow': ['tensorflow'],
    'PyTorch': ['pytorch', 'torch'],
    'Scikit-learn': ['scikit-learn', 'sklearn'],
    'Pandas': ['pandas'],
    'NumPy': ['numpy', 'np'],
    'Matplotlib': ['matplotlib'],
    'Seaborn': ['seaborn'],
    'Keras': ['keras'],
    'NLP': ['nlp', 'natural language processing'],
    'spaCy': ['spacy'],
    'NLTK': ['nltk'],
    
    # Version Control
    'Git': ['git'],
    'GitHub': ['github'],
    'GitLab': ['gitlab'],
    'Bitbucket': ['bitbucket'],
    'SVN': ['svn', 'subversion'],
    
    # Testing
    'Pytest': ['pytest'],
    'Unit Testing': ['unit testing', 'unit test'],
    'Integration Testing': ['integration testing'],
    'Jest': ['jest'],
    'Mocha': ['mocha'],
    'Selenium': ['selenium'],
    
    # Other Tech
    'REST API': ['rest api', 'rest', 'restful'],
    'GraphQL': ['graphql'],
    'WebSocket': ['websocket', 'web socket'],
    'Microservices': ['microservices', 'micro-services'],
    'Docker Compose': ['docker compose'],
    'Linux': ['linux'],
    'Unix': ['unix'],
    'Windows Server': ['windows server'],
    'Bash': ['bash', 'shell scripting'],
    'SQL': ['sql'],
    'NoSQL': ['nosql', 'no-sql'],
    'Message Queues': ['message queues', 'message queue'],
    'Kafka': ['kafka', 'apache kafka'],
    'RabbitMQ': ['rabbitmq', 'rabbit mq'],
    'Apache': ['apache'],
    'Nginx': ['nginx'],
    'AWS Lambda': ['aws lambda', 'lambda'],
    'Serverless': ['serverless'],
    'CI/CD': ['ci/cd', 'cicd'],
    'HTML': ['html', 'html5'],
    'CSS': ['css', 'css3'],
    'SASS': ['sass', 'scss'],
    'Tailwind': ['tailwind', 'tailwind css'],
    'Bootstrap': ['bootstrap'],
}

# Create reverse lookup (token -> skill_name)
def build_skill_lookup():
    """Build a reverse mapping from tokens to skill names"""
    lookup = {}
    for skill_name, tokens in SKILLS_DICT.items():
        for token in tokens:
            lookup[token.lower()] = skill_name
    return lookup

SKILL_LOOKUP = build_skill_lookup()

def extract_skills_from_text(text):
    """
    Extract skills from text using predefined dictionary
    
    Args:
        text (str): Input text (should be cleaned/lowercased)
    
    Returns:
        set: Set of extracted skill names (deduplicated)
    """
    if not text:
        return set()
    
    text_lower = text.lower()
    found_skills = set()
    
    # Match tokens against skill lookup
    for token, skill_name in SKILL_LOOKUP.items():
        # Use word boundaries to avoid partial matches
        import re
        pattern = r'\b' + re.escape(token) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill_name)
    
    return found_skills
