from __future__ import annotations

import logging

from pydantic import BaseModel
from pytest import CaptureFixture

from argdantic import ArgParser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)

# the only way this works is to define at module level
# inside the function this will not work, probably because of the forward reference
# see https://github.com/pydantic/pydantic/discussions/4521 for more info
parser = ArgParser()


class NestedModel(BaseModel):
    a: int
    b: float


class SimpleModel(BaseModel):
    a: int
    b: float
    c: NestedModel


def test_pydantic_forwardrefs(runner: CLIRunner, capsys: CaptureFixture):
    @parser.command()
    def pydantic_model_nested(model: SimpleModel):
        print(model.a, model.b, model.c.a, model.c.b)

    runner.invoke(parser, ["--model.a", "2", "--model.b", "2.0", "--model.c.a", "3", "--model.c.b", "3.0"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "2 2.0 3 3.0"
