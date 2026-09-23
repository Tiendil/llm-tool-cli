from collections.abc import Mapping


class Error(Exception):
    """Base exception with a diagnostic code and structured context.

    Details are copied shallowly. Record fields ``type``, ``code``, and ``message``
    take precedence over details with the same keys. Callers own the JSON
    compatibility of detail values when serializing records.
    """

    code: str = "error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(type(self).__name__ if message is None else message)

        if code is not None:
            self.code = code

        self.details: dict[str, object] = dict(details) if details is not None else {}

    @property
    def message(self) -> str:
        return super().__str__()

    def as_record(self) -> dict[str, object]:
        return {
            **self.details,
            "type": "error",
            "code": self.code,
            "message": self.message,
        }
