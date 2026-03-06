"""
Main Application Entry Point
Configures and runs the Flask application
"""

import os
import logging
from dotenv import load_dotenv
from app import create_app
from config import config_by_name, ProductionConfig

load_dotenv()

ENV = os.environ.get('FLASK_ENV', 'development')
ConfigClass = config_by_name.get(ENV, config_by_name['development'])

if ENV == 'production':
    ProductionConfig.validate_required()

app = create_app(config_class=ConfigClass)


@app.shell_context_processor
def make_shell_context():
    from app.models.resume import Resume
    from app.models.job import Job
    from app.services.nlp_service import NLPService
    from app.services.ml_service import MLService

    return {
        'Resume': Resume,
        'Job': Job,
        'NLPService': NLPService,
        'MLService': MLService,
    }


if __name__ == '__main__':
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 60)
    print("AI RESUME MATCHER")
    print("=" * 60)
    print(f"Environment : {ENV.upper()}")
    print(f"Debug       : {app.debug}")
    print(f"Listen      : 0.0.0.0:5000")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET  /               Frontend")
    print("  POST /api/upload/resume")
    print("  POST /api/match/similarity")
    print("  GET  /api/dashboard/stats")
    print("=" * 60 + "\n")

    logger.info("Starting Resume Matcher Application")

    # Disable the watchdog reloader to avoid frequent restarts on Windows
    # that interrupt long-running file extraction requests.
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.debug,
        use_reloader=False,
    )
