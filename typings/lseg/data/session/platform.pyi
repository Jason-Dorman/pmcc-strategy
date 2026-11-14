from lseg.data.session import Session

class GrantPassword:
    def __init__(self, username: str, password: str) -> None: ...

class Definition:
    def __init__(
        self,
        name: str = "default",
        app_key: str | None = None,
        grant: GrantPassword | None = None,
        signon_control: bool = False,
    ) -> None: ...
    def get_session(self) -> Session: ...
