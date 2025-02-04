from typing import Optional, Union

messageTypes = Union[str, float, int]
MessageTypes = (str, float, int)


TITLE_MAX_LENGTH = 20
DETAIL_MAX_LENGTH = 72


class Button:
    """
    Representa uma lista rápida de botões.

    Atributos:
        typeButton (str): O tipo do botão.
        title (str): O texto do botão.
        detail (str): A descrição do botão.
        absolute_text (bool): Se True, o texto não será modificado.

    Limitações:
        O título do botão deve ter no máximo 20 caracteres.
        A descrição do botão deve ter no máximo 72 caracteres.
    """

    def __init__(
        self,
        title: Optional[str] = None,
        detail: Optional[str] = None,
        typeButton: Optional[str]="postback",
        absolute_text: Optional[bool] = False,
    ) -> None:

        self.absolute_text = absolute_text

        if not absolute_text and detail:
            detail = detail.replace("\t", "")

        assert (
            len(title) <= TITLE_MAX_LENGTH
        ), f"O texto do botão deve ter no máximo {TITLE_MAX_LENGTH} caracteres."
        if detail:
            assert (
                len(detail) <= DETAIL_MAX_LENGTH
            ), f"A descrição do botão deve ter no máximo {DETAIL_MAX_LENGTH} caracteres."

        self.type = typeButton
        self.title = title
        self.detail = detail

    def to_dict(self):
        return {
            "type": self.type,
            "title": self.title,
            "detail": self.detail,
        }


class Message:
    """
    Representa uma mensagem universal enviada pelo chatbot.

    Atributos:
        type (str): O tipo da mensagem.
        url (str): A URL da mensagem.
        filename (str): O nome do arquivo da mensagem.
        title (str): O título da mensagem.
        detail (str): A descrição da mensagem.
        caption (str): A legenda da mensagem.
        buttons (list[Button]): A lista de botões da mensagem.
        absolute_text (bool): Se True, o texto não será modificado.
    """

    def __init__(
        self,
        detail: Optional[str] = None,
        title: Optional[str] = None,
        caption: Optional[str] = None,
        type: Optional[str]="message",
        url: Optional[str] = None,
        filename: Optional[str] = None,
        buttons: Optional[list[Button]] = None,
        display_button: Optional[Button] = None,
        absolute_text: Optional[bool] = False,
    ) -> None:
        self.absolute_text = absolute_text

        if not absolute_text and type == "message":
            detail = detail.replace("\t", "")

        self.type = type
        self.url = url
        self.filename = filename
        self.title = title
        self.detail = detail
        self.caption = caption
        self.buttons = buttons or []
        self.display_button = display_button

    def to_dict(self):
        return {
            "message": {
                "type": self.type,
                "url": self.url,
                "filename": self.filename,
                "title": self.title,
                "detail": self.detail,
                "caption": self.caption,
            },
            "buttons": [button.to_dict() for button in self.buttons],
            "display_button": self.display_button.to_dict() if self.display_button else None, 
        }
