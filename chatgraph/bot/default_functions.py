from ..types.usercall import UserCall
from ..models.message import Message, Button
from ..types.end_types import (
    RedirectResponse,
    EndChatResponse,
    TransferToHuman,
    TransferToMenu,
)
from ..types.route import Route


async def voltar(route: Route, userCall: UserCall) -> RedirectResponse:
    """
    Função para voltar à rota anterior.
    Args:
        route (Route): A rota atual do chatbot.
        usercall (UserCall): O objeto UserCall associado à chamada do usuário.
    """

    previous = route.get_previous()
    userCall.console.print(
        f"Voltando rota. ({route.current}) -> ({previous.current})", style="bold yellow"
    )
    return RedirectResponse(previous.current_node)
