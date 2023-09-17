import argparse
import logging

import pytest
from pydantic import BaseModel, Field
from pytest import CaptureFixture

from argdantic import ArgField, ArgParser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_empty(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def empty():
        print("Hello world")

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world"


def test_repr():
    cli = ArgParser()

    @cli.command()
    def command1():
        pass

    @cli.command()
    def command2():
        pass

    LOG.debug(str(command1))
    LOG.debug(str(command2))
    LOG.debug(str(cli))
    assert cli.entrypoint is None
    assert isinstance(cli.commands, list)
    assert len(cli.commands) == 2
    assert repr(command1) == "<Command command1>"
    assert repr(command2) == "<Command command2>"
    assert repr(cli) == "<Parser(commands=[<Command command1>, <Command command2>])>"


def test_repr_named():
    cli = ArgParser(name="cli")

    @cli.command(name="cmd1")
    def command1():
        pass

    @cli.command(name="cmd2")
    def command2():
        pass

    LOG.debug(str(command1))
    LOG.debug(str(command2))
    LOG.debug(str(cli))
    assert cli.entrypoint is None
    assert isinstance(cli.commands, list)
    assert len(cli.commands) == 2
    assert repr(command1) == "<Command cmd1>"
    assert repr(command2) == "<Command cmd2>"
    assert repr(cli) == "<Parser 'cli'(commands=[<Command cmd1>, <Command cmd2>])>"


def test_empty_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def empty():
        print("Hello world")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage" in output.out.rstrip()
    assert "-h, --help  show this help message and exit" in output.out.rstrip()


def test_empty_help_named(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser(name="mark")

    @parser.command()
    def empty():
        print("Hello world")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage: mark" in output.out.rstrip()
    assert "-h, --help" in output.out.rstrip()
    assert "show this help message and exit" in output.out.rstrip()


def test_missing_annotation(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    with pytest.raises(AssertionError):

        @parser.command()
        def empty(a):
            print(f"Hello {a}")


def test_build_entrypoint(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def empty():
        print("Hello world")

    try:
        parser()
    except SystemExit:
        pass
    assert parser.entrypoint is not None
    assert isinstance(parser.entrypoint, argparse.ArgumentParser)


def test_multiple_commands(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def empty():
        print("Hello world")

    @parser.command()
    def empty2():
        print("Hello world 2")

    runner.invoke(parser, ["empty"])
    assert parser.entrypoint is not None
    assert isinstance(parser.entrypoint, argparse.ArgumentParser)
    assert len(parser.commands) == 2
    assert parser.commands[0].name == "empty"
    assert parser.commands[1].name == "empty2"
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world"
    runner.invoke(parser, ["empty2"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 2"


def test_add_parser_no_name():
    parser1 = ArgParser()
    parser2 = ArgParser()

    @parser1.command()
    def empty1():
        print("Hello world 1")

    @parser2.command()
    def empty2():
        print("Hello world 2")

    with pytest.raises(AssertionError):
        parser1.add_parser(parser2)


def test_add_parser_named(runner: CLIRunner, capsys: CaptureFixture):
    parser1 = ArgParser(name="parser1")
    parser2 = ArgParser(name="parser2")

    @parser1.command()
    def empty1():
        print("Hello world 1")

    @parser2.command()
    def empty2():
        print("Hello world 2")

    parser1.add_parser(parser2)
    assert len(parser1.commands) == 1
    assert len(parser1.groups) == 1
    assert len(parser2.commands) == 1
    assert len(parser2.groups) == 0
    runner.invoke(parser1, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert "usage: parser1" in output.err.rstrip()
    runner.invoke(parser1, ["empty1"])
    output = capsys.readouterr()
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 1"
    runner.invoke(parser1, ["parser2"])
    output = capsys.readouterr()
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 2"


def test_add_named_parser_force_group(runner: CLIRunner, capsys: CaptureFixture):
    parser1 = ArgParser(name="parser1", force_group=True)
    parser2 = ArgParser(name="parser2", force_group=True)

    @parser1.command()
    def empty1():
        print("Hello world 1")

    @parser2.command()
    def empty2():
        print("Hello world 2")

    parser1.add_parser(parser2)
    assert len(parser1.commands) == 1
    assert len(parser1.groups) == 1
    assert len(parser2.commands) == 1
    assert len(parser2.groups) == 0
    runner.invoke(parser1, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert "usage: parser1" in output.err.rstrip()
    runner.invoke(parser1, ["empty1"])
    output = capsys.readouterr()
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 1"
    runner.invoke(parser1, ["parser2"])
    output = capsys.readouterr()
    assert "usage:" in output.err.rstrip()
    runner.invoke(parser1, ["parser2", "empty2"])
    output = capsys.readouterr()
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 2"


def test_add_parser_pass_name(runner: CLIRunner, capsys: CaptureFixture):
    parser1 = ArgParser()
    parser2 = ArgParser()

    @parser1.command()
    def empty1():
        print("Hello world 1")

    @parser2.command()
    def empty2():
        print("Hello world 2")

    parser1.add_parser(parser2, name="parser2")
    assert len(parser1.commands) == 1
    assert len(parser1.groups) == 1
    assert len(parser2.commands) == 1
    assert len(parser2.groups) == 0
    runner.invoke(parser1, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert "usage:" in output.err.rstrip()
    runner.invoke(parser1, ["empty1"])
    output = capsys.readouterr()
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 1"
    runner.invoke(parser1, ["parser2"])
    output = capsys.readouterr()
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world 2"


def test_pydantic_model(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str
        b: int

    @parser.command()
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--cfg.a=hello", "--cfg.b=42"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "hello 42"


def test_field_description(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = Field(description="A string")
        b: int = Field(description="An integer")

    @parser.command()
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "A string" in output.out.rstrip()
    assert "An integer" in output.out.rstrip()


def test_field_default(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = Field("hello")
        b: int = Field(42)

    @parser.command()
    def empty(cfg: Config = Config()):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "hello 42"


def test_field_defaults_new_values(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = Field("hello")
        b: int = Field(42)

    @parser.command()
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--cfg.a=world", "--cfg.b=43"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "world 43"


def test_arg_field(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = ArgField(default="hello", description="A string")
        b: int = ArgField(default=42, description="An integer")

    @parser.command()
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "A string" in output.out.rstrip()
    assert "An integer" in output.out.rstrip()
    runner.invoke(parser, ["--cfg.a=world", "--cfg.b=43"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "world 43"


def test_arg_field_in_function(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def empty(
        a: str = ArgField(default="hello", description="A string"),
        b: int = ArgField(default=42, description="An integer"),
    ):
        print(f"{a} {b}")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "A string" in output.out.rstrip()
    assert "An integer" in output.out.rstrip()
    runner.invoke(parser, ["--a=world", "--b=43"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "world 43"


def test_arg_field_names(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = ArgField("--foo", "-f", default="hello", description="A string")
        b: int = ArgField("--bar", "-b", default=42, description="An integer")

    @parser.command()
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    stripped = output.out.rstrip()
    LOG.debug(stripped)
    assert output.err.rstrip() == ""
    assert "--cfg.a" in stripped
    assert "--cfg.b" in stripped
    assert "--foo" in stripped
    assert "--bar" in stripped
    assert "-f" in stripped
    assert "-b" in stripped
    assert "A string" in stripped
    assert "An integer" in stripped

    runner.invoke(parser, ["--cfg.a=world", "--cfg.b=43"])
    output = capsys.readouterr()
    stripped = output.out.rstrip()
    LOG.debug(stripped)
    assert output.err.rstrip() == ""
    assert stripped == "world 43"

    runner.invoke(parser, ["--foo=world", "--bar=43"])
    output = capsys.readouterr()
    stripped = output.out.rstrip()
    LOG.debug(stripped)
    assert output.err.rstrip() == ""
    assert stripped == "world 43"

    runner.invoke(parser, ["-f=world", "-b=43"])
    output = capsys.readouterr()
    stripped = output.out.rstrip()
    LOG.debug(stripped)
    assert output.err.rstrip() == ""
    assert stripped == "world 43"


def test_validation_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = ArgField("--foo", "-f", description="A string", min_length=10)
        b: int = ArgField("--bar", "-b", description="An integer", gt=43)

    @parser.command()
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--cfg.a=short", "--cfg.b=42"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert "cfg -> a: String should have at least 10 characters" in output.err.rstrip()
    assert "cfg -> b: Input should be greater than 43" in output.err.rstrip()
    assert output.out.rstrip() == ""

    runner.invoke(parser, ["--foo=verylongname", "--bar=44"])
    output = capsys.readouterr()
    stripped = output.out.rstrip()
    LOG.debug(stripped)
    assert output.err.rstrip() == ""
    assert stripped == "verylongname 44"


def test_singleton_multiple_arguments(runner: CLIRunner):
    parser = ArgParser()

    class Config(BaseModel):
        a: str
        b: int

    with pytest.raises(AssertionError):

        @parser.command(singleton=True)
        def empty(cfg: Config, seed: int):
            print(cfg, seed)


def test_singleton_without_model(runner: CLIRunner):
    parser = ArgParser()

    with pytest.raises(AssertionError):

        @parser.command(singleton=True)
        def empty(seed: int):
            print(seed)


def test_singleton_command(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    class Config(BaseModel):
        a: str = ArgField("--foo", "-f", description="A string", min_length=10)
        b: int = ArgField("--bar", "-b", description="An integer", gt=43)

    @parser.command(singleton=True)
    def empty(cfg: Config):
        print(f"{cfg.a} {cfg.b}")

    runner.invoke(parser, ["--a=short", "--b=42"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert "a: String should have at least 10 characters" in output.err.rstrip()
    assert "b: Input should be greater than 43" in output.err.rstrip()
    assert output.out.rstrip() == ""

    runner.invoke(parser, ["--foo=verylongname", "--bar=44"])
    output = capsys.readouterr()
    stripped = output.out.rstrip()
    LOG.debug(stripped)
    assert output.err.rstrip() == ""
    assert stripped == "verylongname 44"
