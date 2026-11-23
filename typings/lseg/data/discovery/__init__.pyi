from pandas import DataFrame

def search(
    query: str | None = None,
    view: str = "SearchAll",
    filter: str | None = None,
    order_by: str | None = None,
    select: str | None = None,
    top: int = 10,
) -> DataFrame: ...
