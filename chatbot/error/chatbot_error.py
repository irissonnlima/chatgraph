class ChatbotError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'ChatbotError: {self.message}'


class ChatbotMessageError(Exception):
    def __init__(self, customer_id: str, message: str):
        self.customer_id = customer_id
        self.message = f'{message} ID recebido: {customer_id}'
        super().__init__(self.message)

    def __str__(self):
        return f'InvalidCustomerIDError: {self.message}'
