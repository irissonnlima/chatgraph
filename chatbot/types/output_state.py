from typing import Union

messageTypes = Union[str, float, int, None]


class ChatbotResponse:
    def __init__(
        self, message: messageTypes = None, route: str = None
    ) -> None:
        self.message = message
        self.route = route

class RedirectResponse:
    def __init__(self, route: str) -> None:
        self.route = route