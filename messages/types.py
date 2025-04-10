from pydantic import BaseModel, Field
from typing import Optional


class MyMessageType(BaseModel):
    """Message type used for communication between traffic simulation agents
    
    This class represents the standard message format used for all agent communication
    in the traffic simulation system.
    
    Attributes:
        content (str): The content/payload of the message
        source (str): The identifier of the sending agent
        message_id (Optional[str]): Optional unique identifier for the message
        timestamp (Optional[float]): Optional timestamp when the message was created
    """
    content: str
    source: str
    message_id: Optional[str] = None
    timestamp: Optional[float] = None