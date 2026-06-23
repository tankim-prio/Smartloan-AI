from app.models.user import User
from app.models.application import Application
from app.models.application_document import ApplicationDocument
from app.models.extracted_text import ExtractedText
from app.models.extracted_field import ExtractedField
from app.models.review import Review
from app.models.notification import Notification
from app.models.ml_model import MLModel
from app.models.prediction import Prediction

__all__ = [
    "User",
    "Application",
    "ApplicationDocument",
    "ExtractedText",
    "ExtractedField",
    "Review",
    "Notification",
    "MLModel",
    "Prediction",
]
