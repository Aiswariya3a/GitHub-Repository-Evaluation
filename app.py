from pathlib import Path

from asgiref.wsgi import WsgiToAsgi
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from controllers import EvaluationController, ReportController, RepositoryController, RubricController, SessionController
from services.container import ServiceContainer


ROOT = Path(__file__).resolve().parent
# All HTTP routes are registered through controller blueprints; touching this
# factory also guarantees Flask reloads versioned rubric and dashboard changes.


def create_app(service_container=None):
    app = Flask(__name__)
    app.secret_key = "repo-eval-workflow"
    app.extensions["services"] = service_container or ServiceContainer.build(ROOT)
    app.register_blueprint(SessionController.blueprint)
    app.register_blueprint(RepositoryController.blueprint)
    app.register_blueprint(EvaluationController.blueprint)
    app.register_blueprint(ReportController.blueprint)
    app.register_blueprint(RubricController.blueprint)
    return app


app = WsgiToAsgi(create_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5001, reload=False)
