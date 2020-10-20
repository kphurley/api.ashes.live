from copy import deepcopy
from typing import Callable, NamedTuple
import urllib.parse

from pydantic import AnyHttpUrl

from api import db
from api.schemas.pagination import PaginationOptions, PaginatedResultsBase


def replace_offset(url: str, offset: int) -> str:
    """Updates the offset in the given URL's query string"""
    url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(url.query)
    if offset == 0 and "offset" in query_params:
        del query_params["offset"]
    else:
        query_params["offset"] = [offset]
    encoded_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.ParseResult(
        url.scheme, url.netloc, url.path, url.params, encoded_query, url.fragment
    ).geturl()


def paginated_results_for_query(
    query: db.Query,
    paging: PaginationOptions,
    url: str,
    row_to_dict: Callable[[db.RowProxy], dict] = None,
) -> PaginatedResultsBase:
    """Generic pagination results output"""
    # Fetch count and actual query data
    total_rows = query.count()
    rows = query.limit(paging.limit).offset(paging.offset).all()

    # Construct our next and previous links
    previous_url = None
    if paging.offset > 0:
        prev_offset = paging.offset - paging.limit
        if prev_offset < 0:
            prev_offset = 0
        previous_url = replace_offset(url, prev_offset)

    next_url = None
    next_offset = paging.offset + paging.limit
    if next_offset < total_rows:
        next_url = replace_offset(url, next_offset)

    # Construct our result rows and return
    if row_to_dict:
        row_list = [row_to_dict(x) for x in rows]
    elif len(query.column_descriptions) == 1:
        row_list = [x[0] for x in rows]
    else:
        row_list = rows
    return {
        "count": total_rows,
        "next": next_url,
        "previous": previous_url,
        "results": row_list,
    }