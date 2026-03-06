"""
Predefined Skills Dictionary for Resume Parsing

Comprehensive list of technical and professional skills
organized by category for efficient matching.
"""

SKILLS_DICT = {
    # Programming Languages
    "programming_languages": {
        "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
        "php", "kotlin", "swift", "objective-c", "scala", "r", "matlab", "perl", "bash",
        "shell", "groovy", "haskell", "clojure", "elixir", "erlang", "lua"
    },
    
    # Web Frameworks
    "web_frameworks": {
        "react", "angular", "vue", "svelte", "nextjs", "gatsby", "nuxt", "django",
        "flask", "fastapi", "spring", "spring boot", "express", "nodejs", "node.js",
        "nestjs", "asp.net", "dotnet", "rails", "sinatra", "laravel", "symfony",
        "phoenix", "ktor", "gin", "echo", "fiber", "iris"
    },
    
    # Frontend Technologies
    "frontend": {
        "html", "css", "scss", "sass", "less", "tailwind", "bootstrap", "material-ui",
        "material design", "webpack", "babel", "parcel", "vite", "rollup", "gulp",
        "grunt", "browserify", "jest", "vitest", "mocha", "jasmine", "karma",
        "cypress", "playwright", "selenium", "webdriver"
    },
    
    # Databases
    "databases": {
        "sql", "mysql", "postgresql", "oracle", "mssql", "mongodb", "cassandra",
        "dynamodb", "elasticsearch", "redis", "memcached", "sqlite", "mariadb",
        "cockroachdb", "firebase", "firestore", "bigquery", "snowflake", "redshift",
        "athena", "neo4j", "graph", "couchdb", "realm", "hbase", "solr"
    },
    
    # Cloud Platforms
    "cloud_platforms": {
        "aws", "azure", "gcp", "google cloud", "heroku", "digitalocean", "linode",
        "vultr", "ibm cloud", "oracle cloud", "alibaba cloud", "tencent cloud",
        "aws lambda", "cloud functions", "fargate", "ec2", "s3", "rds", "dynamodb",
        "azure vm", "app service", "cosmos db", "sql database", "storage account",
        "cloud storage", "compute engine", "app engine", "dataflow", "bigquery"
    },
    
    # DevOps & Tools
    "devops_tools": {
        "docker", "kubernetes", "git", "github", "gitlab", "bitbucket", "jenkins",
        "circleci", "travis", "github actions", "gitlab ci", "terraform", "ansible",
        "chef", "puppet", "docker compose", "docker swarm", "helm", "prometheus",
        "grafana", "elk", "newrelic", "datadog", "splunk", "cloudwatch", "stack driver"
    },
    
    # Machine Learning & AI
    "ml_ai": {
        "machine learning", "deep learning", "artificial intelligence", "tensorflow",
        "pytorch", "keras", "scikit-learn", "xgboost", "catboost", "lightgbm",
        "spacy", "nltk", "gensim", "huggingface", "transformers", "bert", "gpt",
        "llm", "rag", "langchain", "vector database", "pinecone", "weaviate",
        "milvus", "openai", "anthropic", "cohere", "mlflow", "wandb", "neptune"
    },
    
    # Data Processing
    "data_processing": {
        "pandas", "numpy", "scipy", "dask", "polars", "spark", "pyspark", "hadoop",
        "hive", "pig", "airflow", "luigi", "prefect", "dagster", "kafka", "rabbitmq",
        "nifi", "beam", "dataprep", "dataflow", "etl", "elt", "informatica", "talend"
    },
    
    # Big Data
    "big_data": {
        "hadoop", "spark", "pyspark", "hive", "pig", "kafka", "sqoop", "flume",
        "storm", "flink", "beam", "dataflow", "databricks", "snowflake", "redshift",
        "bigquery", "athena", "presto", "trino", "druid", "clickhouse", "timescaledb"
    },
    
    # Version Control
    "version_control": {
        "git", "github", "gitlab", "bitbucket", "svn", "mercurial", "perforce",
        "gitflow", "gitops", "git lfs", "git hooks"
    },
    
    # Testing
    "testing": {
        "unit testing", "integration testing", "e2e testing", "jest", "mocha",
        "jasmine", "vitest", "vitest", "cypress", "playwright", "selenium",
        "junit", "testng", "pytest", "unittest", "nose", "tox", "coverage",
        "mutation testing", "load testing", "jmeter", "locust", "gatling", "k6"
    },
    
    # API & Networking
    "api_networking": {
        "rest", "restful", "graphql", "grpc", "soap", "webhook", "oauth", "jwt",
        "saml", "api design", "openapi", "swagger", "postman", "insomnia", "httpie",
        "curl", "axios", "requests", "fetch", "websocket", "socket.io", "mqtt",
        "http2", "http3", "quic", "protobuf"
    },
    
    # Mobile Development
    "mobile_development": {
        "ios", "android", "react native", "flutter", "xamarin", "cordova", "ionic",
        "swift", "kotlin", "objective-c", "java android", "xcode", "android studio",
        "firebase mobile", "realm", "sqlite mobile"
    },
    
    # Project Management
    "project_management": {
        "agile", "scrum", "kanban", "jira", "asana", "monday", "trello", "linear",
        "github projects", "confluence", "notion", "clickup", "basecamp", "slack",
        "ms project", "smartsheet", "wrike", "monday.com"
    },
    
    # Security
    "security": {
        "cybersecurity", "information security", "application security", "network security",
        "encryption", "ssl", "tls", "oauth", "jwt", "saml", "mfa", "2fa", "owasp",
        "penetration testing", "vulnerability assessment", "siem", "ids", "ips",
        "firewall", "vpn", "tor", "pgp", "gnupg"
    },
    
    # Soft Skills
    "soft_skills": {
        "communication", "leadership", "teamwork", "problem solving", "critical thinking",
        "time management", "project management", "analytical skills", "attention to detail",
        "collaboration", "adaptability", "creativity", "negotiation", "presentation",
        "customer service", "conflict resolution", "mentoring", "coaching"
    },
    
    # Methodologies
    "methodologies": {
        "agile", "scrum", "kanban", "lean", "waterfall", "devops", "microservices",
        "monolithic", "serverless", "design patterns", "solid principles", "clean code",
        "tdd", "bdd", "ci/cd", "continuous integration", "continuous deployment"
    },
    
    # Other Technologies
    "other": {
        "linux", "windows", "macos", "unix", "containerization", "virtualization",
        "networking", "dns", "dhcp", "tcp/ip", "ip", "http", "ftp", "ssh", "telnet",
        "ldap", "kerberos", "radius", "tacacs", "snmp", "ntp", "nfs", "smb"
    }
}

# Flatten dictionary for fast lookup
SKILLS_SET = set()
for category_skills in SKILLS_DICT.values():
    SKILLS_SET.update(category_skills)

# Skills by lowercase for case-insensitive matching
SKILLS_LOWERCASE = {skill.lower(): skill for skill in SKILLS_SET}


def get_all_skills():
    """Return all skills as a set (lowercase)."""
    return SKILLS_SET


def normalize_skill_name(skill):
    """Normalize skill name to canonical form."""
    skill_lower = skill.lower().strip()
    return SKILLS_LOWERCASE.get(skill_lower, skill)


def is_skill(token):
    """Check if token is a known skill (case-insensitive)."""
    return token.lower().strip() in SKILLS_LOWERCASE
