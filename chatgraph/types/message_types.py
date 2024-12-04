from typing import Optional, Union

messageTypes = Union[str, float, int]
MessageTypes = (str, float, int)

class Message:
    """
    Representa uma mensagem enviada ou recebida pelo chatbot.
    
    Atributos:
        message (str): O conteúdo textual da mensagem.
        absolute_text (bool): Se True, o texto não será modificado.
    """
    
    def __init__(
        self, 
        text:str,
        absolute_text: bool = False,
        ) -> None:
        self.absolute_text = absolute_text
        
        if not absolute_text:
            text = text.replace('\t', '')
            
        self.text = text

class Button:
    """
    Representa uma lista rápida de botões.
    
    Atributos:
        text (str): O texto da mensagem.
        buttons (list[str]): A lista de botões.
        title (str): O título da mensagem.
        caption (str): A legenda da mensagem.
        absolute_text (bool): Se True, o texto não será modificado.
    
    Limitações:
        O número máximo de botões é 3.
        O texto do botão deve ter no máximo 20 caracteres.
    """
    def __init__(
        self, 
        text:str, 
        buttons: list[str],
        title: Optional[str] = None,
        caption: Optional[str] = None,
        absolute_text: bool = False,
        ) -> None:
        self.absolute_text = absolute_text
        
        if not absolute_text:
            text = text.replace('\t', '')
        
        assert len(buttons) <= 3, "O número máximo de botões é 3."
        
        for button in buttons:
            assert len(button) <= 20, "O texto do botão deve ter no máximo 20 caracteres."
        
        self.text = text
        self.buttons = buttons
        self.title = title
        self.caption = caption

class ListElements:
    """
    Representa uma lista de elementos.
    
    atributos:
        text (str): O texto da mensagem.
        title (str): O título da mensagem.
        button_title (str): O título do botão.
        elements (list[dict]): A lista de elementos.
        caption (str): A legenda da mensagem.
        absolute_text (bool): Se True, o texto não será modificado.
    
    Limitações:
        O número máximo de elementos é 10.
        O título do elemento deve ter no máximo 24 caracteres.
        A descrição do elemento deve ter no máximo 72 caracteres.
    """
    def __init__(
        self, 
        text:str,
        button_title: str,
        elements: dict,
        title: Optional[str] = None,
        caption: Optional[str] = None,
        absolute_text: bool = False,
        ) -> None:
        self.absolute_text = absolute_text
        
        if not absolute_text:
            text = text.replace('\t', '')
        
        assert len(elements) <= 10, "O número máximo de elementos é 10."
        
        for key, value in elements.items():
            assert len(key) <= 24, "O título do elemento deve ter no máximo 24 caracteres."
            assert len(value) <= 72, "A descrição do elemento deve ter no máximo 72 caracteres."
        
        self.text = text
        self.title = title
        self.button_title = button_title
        self.elements = elements
        self.caption = caption


