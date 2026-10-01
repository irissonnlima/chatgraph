import json
import os

from dotenv import load_dotenv

from chatgraph import ChatbotApp, UserCall


async def start(usercall: UserCall) -> None:
    """
    Bot de eco do modo stream: grava a observation e devolve
    `<menu>|<pod>|<texto>`. É também a fixture da validação na stack do
    router, que confere esse formato. Sem retorno (None), o pipeline fica no
    mesmo nó da rota.
    """
    bot = usercall.menu.name
    # O handler não conhece o pod do welcome; o eco recebe por env.
    pod = os.getenv('STREAM_ECHO_POD', '')
    text = usercall.content_message

    await usercall.set_observation(
        json.dumps({'bot': bot, 'pod': pod, 'text': text})
    )
    await usercall.send(f'{bot}|{pod}|{text}')


def main() -> None:
    load_dotenv()
    app = ChatbotApp()
    app.route('start')(start)
    app.start()


if __name__ == '__main__':
    main()
