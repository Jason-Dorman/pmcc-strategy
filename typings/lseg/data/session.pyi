from . import OpenState

class Session:
    @property
    def open_state(self) -> OpenState: ...

def get_default() -> Session: ...
