import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from dotenv import load_dotenv
from ..gRPC.gRPCCall import WhatsappServiceClient, UserStateServiceClient
import os, re

load_dotenv()
app = typer.Typer()

@app.command()
def configs():
    """Recupera os IDs necessários."""
    console = Console()
    
    username = os.getenv('RABBIT_USER')
    password = os.getenv('RABBIT_PASS')
    url = os.getenv('RABBIT_URI')
    queue = os.getenv('RABBIT_QUEUE')
    prefetch = os.getenv('RABBIT_PREFETCH', 1)
    vhost = os.getenv('RABBIT_VHOST', '/')
    grpc = os.getenv('GRPC_URI')

    
    tableRabbit = Table(show_header=True, header_style="bold magenta", title="RabbitMQ Consumer")
    tableRabbit.add_column("Atributo", justify="center", style="cyan", no_wrap=True)
    tableRabbit.add_column("Valor", justify="center", style="magenta")

    tableRabbit.add_row("Virtual Host", vhost)
    tableRabbit.add_row("Prefetch Count", str(prefetch))
    tableRabbit.add_row("Queue Consume", queue)
    tableRabbit.add_row("AMQP URL", url)
    tableRabbit.add_row("Username", username)
    tableRabbit.add_row("Password", "******")
    
    
    tableGRPC = Table(show_header=True, header_style="bold magenta", title="gRPC Consumer")
    tableGRPC.add_column("Atributo", justify="center", style="cyan", no_wrap=True)
    tableGRPC.add_column("Valor", justify="center", style="magenta")
    
    tableGRPC.add_row("URI", grpc)
    
    console.print(tableGRPC, justify="center")
    console.print(tableRabbit, justify="center")

@app.command()
def campaigns(regex: str = typer.Option(None, "--regex", "-r", help="Filtro regex para campanhas.")):
    """Recupera as campanhas cadastradas."""
    grpc = os.getenv('GRPC_URI')
    
    wwp = WhatsappServiceClient(grpc)
    campaigns = wwp.get_all_campaigns()
    
    console = Console()
    tableGRPC = Table(show_header=True, header_style="bold magenta", title="Campaigns")
    tableGRPC.add_column("campaign_id", justify="center", style="cyan", no_wrap=True)
    tableGRPC.add_column("campaign_name", justify="center", style="magenta")
    tableGRPC.add_column("last_update", justify="center", style="magenta")
    
    # Aplicar filtro de regex, se fornecido
    filtered_campaigns = campaigns.campaigns
    if regex:
        pattern = re.compile(regex)
        filtered_campaigns = [
            campaign for campaign in campaigns.campaigns
            if pattern.search(campaign.campaign_name)
        ]
    
    for campaign in filtered_campaigns:
        tableGRPC.add_row(campaign.campaign_id, campaign.campaign_name, campaign.last_update)
    
    console.print(tableGRPC, justify="center")
    
@app.command()
def tabulations(
    regex: str = typer.Option(None, "--regex", "-r", help="Filtro regex para as tabulações.")
):
    """Recupera as tabulações cadastradas."""
    grpc = os.getenv('GRPC_URI')
    
    wwp = WhatsappServiceClient(grpc)
    tabulations = wwp.get_all_tabulations()
    
    console = Console()
    tableGRPC = Table(show_header=True, header_style="bold magenta", title="Tabulations")
    tableGRPC.add_column("tabulation_id", justify="center", style="cyan", no_wrap=True)
    tableGRPC.add_column("tabulation_name", justify="center", style="magenta")
    tableGRPC.add_column("tabulation_type", justify="center", style="magenta")
    tableGRPC.add_column("group_name", justify="center", style="magenta")
    tableGRPC.add_column("customer_service_survey_id", justify="center", style="magenta")
    tableGRPC.add_column("last_update", justify="center", style="magenta")
    
    # Aplicar filtro de regex, se fornecido
    filtered_tabulations = tabulations.tabulations
    if regex:
        pattern = re.compile(regex, re.IGNORECASE)
        filtered_tabulations = [
            tabulation for tabulation in tabulations.tabulations
            if (
                pattern.search(tabulation.tabulation_id) or
                pattern.search(tabulation.tabulation_name) or
                pattern.search(tabulation.tabulation_type) or
                pattern.search(tabulation.group_name) or
                (tabulation.customer_service_survey_id and pattern.search(tabulation.customer_service_survey_id)) or
                pattern.search(tabulation.last_update)
            )
        ]
    
    for tabulation in filtered_tabulations:
        tableGRPC.add_row(
            tabulation.tabulation_id,
            tabulation.tabulation_name,
            tabulation.tabulation_type,
            tabulation.group_name,
            tabulation.customer_service_survey_id or "N/A",
            tabulation.last_update,
        )
    
    console.print(tableGRPC, justify="center")


@app.command("ustate")
def user_state(
    regex: str = typer.Option(None, "--regex", "-r", help="Filtro regex para os estados do usuário.")
):
    """Recupera os UserState em operação no momento."""
    grpc = os.getenv('GRPC_URI')
    
    ustate = UserStateServiceClient(grpc)
    userstates = ustate.get_all_user_states()
    
    console = Console()
    tableGRPC = Table(show_header=True, header_style="bold magenta", title="User States")
    tableGRPC.add_column("user_id", justify="center", style="cyan", no_wrap=True)
    tableGRPC.add_column("menu_id", justify="center", style="magenta")
    tableGRPC.add_column("route", justify="center", style="magenta")
    tableGRPC.add_column("obs", justify="center", style="magenta")
    tableGRPC.add_column("date", justify="center", style="magenta")
    tableGRPC.add_column("direction", justify="center", style="magenta")
    
    # Aplicar filtro de regex, se fornecido
    filtered_user_states = userstates.user_states
    if regex:
        pattern = re.compile(regex, re.IGNORECASE)
        filtered_user_states = [
            userstate for userstate in userstates.user_states
            if (
                pattern.search(userstate.user_id) or
                pattern.search(userstate.menu_id) or
                pattern.search(userstate.route) or
                pattern.search(userstate.obs) or
                pattern.search(userstate.date) or
                pattern.search(str(userstate.direction))
            )
        ]
    
    for userstate in filtered_user_states:
        tableGRPC.add_row(
            userstate.user_id,
            userstate.menu_id,
            userstate.route,
            userstate.obs,
            userstate.date,
            str(userstate.direction),
        )
    
    console.print(tableGRPC, justify="center")

@app.command("del-ustate")
def delete_user_state(user_id: str = typer.Argument(..., help="ID do UserState a ser deletado.")):
    """Deleta um UserState em operação no momento."""
    grpc = os.getenv('GRPC_URI')
    
    ustate = UserStateServiceClient(grpc)
    
    # Chama o método para deletar o UserState usando o ID fornecido
    try:
        success = ustate.delete_user_state(user_id)
        if success:
            typer.echo(f"UserState com ID '{user_id}' deletado com sucesso.")
        else:
            typer.echo(f"Falha ao deletar UserState com ID '{user_id}'.", err=True)
    except Exception as e:
        typer.echo(f"Erro ao tentar deletar UserState: {e}", err=True)
    
def main():
    app()
