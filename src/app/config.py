import json
from pathlib import Path

import typer

from src.app import config_manager

app = typer.Typer()


@app.command()
def add_llm(
    llm_name: str = typer.Option(
        ..., prompt=True, help="Name under which the LLM will be stored"
    ),
    llm_class_path: str = typer.Option(
        ..., prompt=True, help="Class path of the LLM. E.g. langchain_openai.ChatOpenAI"
    ),
    llm_kwargs: str = typer.Option(
        ...,
        prompt=True,
        help="Keyword arguments to pass on the llm init passed as json",
    ),
) -> None:
    """
    Add a new LLM configuration which then can be used in other commands.
    """
    from src.service.llm_service import LLMConfig

    settings = config_manager.read_settings()
    if llm_name in settings.llms_config:
        typer.echo(f"LLM with name {llm_name} already exists", err=True)

    settings.llms_config[llm_name] = LLMConfig(
        llm_class_path=llm_class_path, llm_kwargs=json.loads(llm_kwargs)
    )
    if len(settings.llms_config) <= 2:
        settings.default_llm_name = llm_name
    config_manager.write_settings(settings)
    typer.echo(f"LLM with name {llm_name} added")


@app.command()
def remove_llm(
    llm_name: str = typer.Option(..., prompt=True, help="Name of the LLM to remove")
) -> None:
    """
    Remove an LLM configuration.
    """
    settings = config_manager.read_settings()
    if llm_name not in settings.llms_config:
        typer.echo(f"LLM with name {llm_name} does not exist", err=True)
        return

    settings.llms_config.pop(llm_name)
    config_manager.write_settings(settings)
    typer.echo(f"LLM with name {llm_name} removed")


@app.command()
def set_default_llm(
    llm_name: str = typer.Option(
        ..., prompt=True, help="Name of the LLM to set as default"
    )
) -> None:
    """
    Set an LLM as the default LLM.
    """
    settings = config_manager.read_settings()
    if llm_name not in settings.llms_config:
        typer.echo(f"LLM with name {llm_name} does not exist", err=True)
        return

    settings.default_llm_name = llm_name
    config_manager.write_settings(settings)
    typer.echo(f"LLM with name {llm_name} set as default")


@app.command()
def get_data_dir() -> None:
    """
    Get the data directory path. This is where the books and decks are stored.
    """
    settings = config_manager.read_settings()
    typer.echo(settings.data_dir)


@app.command()
def set_data_dir(
    data_dir: Path = typer.Option(..., prompt=True, help="Path to the data directory")
) -> None:
    """
    Set the data directory path. This is where the books and decks are stored.
    """
    settings = config_manager.read_settings()
    settings.data_dir = data_dir
    config_manager.write_settings(settings)
    typer.echo(f"Data directory set to {data_dir}")


@app.command()
def get_settings_dir() -> None:
    """
    Get the settings directory path. This is where the settings are stored.
    """
    settings = config_manager.read_settings()
    typer.echo(settings.settings_dir)


@app.command()
def set_logging_level(
    logging_level: str = typer.Option(
        ...,
        prompt=True,
        help="Logging level. E.g. DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
) -> None:
    """
    Set the logging level.
    """
    settings = config_manager.read_settings()
    settings.logger_level = logging_level
    config_manager.write_settings(settings)
    typer.echo(f"Logging level set to {logging_level}")
