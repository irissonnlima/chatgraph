from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    type: str
    text: str
    customer_id: str
    channel: str
    customer_phone: str
    company_phone: str
    status: Optional[str] = None
