import sys


def write_output(text: str, *, error: bool = False) -> None:
    """Write supplied text to the current standard output or error stream."""
    stream = sys.stderr if error else sys.stdout
    stream.write(text)
