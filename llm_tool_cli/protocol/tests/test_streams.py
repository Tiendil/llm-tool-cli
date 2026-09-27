import io
import sys

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.protocol import write_output


class TestWriteOutput:
    @pytest.mark.parametrize("error", [False, True])
    @pytest.mark.parametrize("text", ["", "日本語", " trailing space \n\n", "line\r\n"])
    def test_supplied_text(self, mocker: MockerFixture, text: str, error: bool) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        mocker.patch.object(sys, "stdout", stdout)
        mocker.patch.object(sys, "stderr", stderr)

        write_output(text, error=error)

        assert stdout.getvalue() == ("" if error else text)
        assert stderr.getvalue() == (text if error else "")

    def test_current_stream(self, mocker: MockerFixture) -> None:
        first = io.StringIO()
        second = io.StringIO()
        mocker.patch.object(sys, "stdout", first)
        write_output("first")
        mocker.patch.object(sys, "stdout", second)
        write_output("second")

        assert first.getvalue() == "first"
        assert second.getvalue() == "second"

    def test_does_not_flush(self, mocker: MockerFixture) -> None:
        stream = io.StringIO()
        flush = mocker.spy(stream, "flush")
        mocker.patch.object(sys, "stdout", stream)

        write_output("text")

        assert stream.getvalue() == "text"
        flush.assert_not_called()

    def test_stream_failure(self, mocker: MockerFixture) -> None:
        stream = io.StringIO()
        mocker.patch.object(stream, "write", side_effect=OSError("write failed"))
        mocker.patch.object(sys, "stdout", stream)

        with pytest.raises(OSError, match="write failed"):
            write_output("text")
