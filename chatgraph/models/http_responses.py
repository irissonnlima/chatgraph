from dataclasses import dataclass


@dataclass
class RouterResponses:
    status: bool
    message: str
    data: dict | list | None = None

    @staticmethod
    def from_dict(data: dict) -> 'RouterResponses':
        return RouterResponses(
            status=data.get('status', False),
            message=data.get('message', ''),
            data=data.get('data'),
        )
