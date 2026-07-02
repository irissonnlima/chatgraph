from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlatformState:
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.data

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> 'PlatformState':
        if data is None:
            return cls(data={})
        return cls(data=data)

    @property
    def as_voll(self) -> Optional['VollStateData']:
        try:
            return VollStateData(**self.data)
        except (TypeError, ValueError):
            return None

    def __bool__(self) -> bool:
        return bool(self.data)


@dataclass
class VollStateData:
    session_id: int
    customer_id: str
    platform: str
    protocol: str
    campaign: str
