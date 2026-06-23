from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    application_id: int | None = None
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
