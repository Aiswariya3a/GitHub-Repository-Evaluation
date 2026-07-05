from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from controllers import EvaluationController, ReportController, RepositoryController, SessionController
from services.container import ServiceContainer


ROOT = Path(__file__).resolve().parent


def create_app(service_container=None):
    app = Flask(__name__)
    app.secret_key = "repo-eval-workflow"
    app.extensions["services"] = service_container or ServiceContainer.build(ROOT)
    app.register_blueprint(SessionController.blueprint)
    app.register_blueprint(RepositoryController.blueprint)
    app.register_blueprint(EvaluationController.blueprint)
    app.register_blueprint(ReportController.blueprint)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
