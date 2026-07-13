from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.forbidden_error import ForbiddenError
from ...models.message_details import MessageDetails
from ...types import Response


def _get_kwargs(
    inbox_id: int,
    id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/inbound/inboxes/{inbox_id}/messages/{id}".format(
            inbox_id=quote(str(inbox_id), safe=""),
            id=quote(str(id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | ForbiddenError | MessageDetails | None:
    if response.status_code == 200:
        response_200 = MessageDetails.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ForbiddenError.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())

        return response_404

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorResponse | ForbiddenError | MessageDetails]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    inbox_id: int,
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorResponse | ForbiddenError | MessageDetails]:
    """Get a message

     Returns a single inbound message together with URLs for the
    raw `.eml` file and for each attachment, plus the decoded HTML and
    plain-text bodies. URLs expire after one hour.

    Args:
        inbox_id (int):  Example: 1.
        id (str):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | ForbiddenError | MessageDetails]
    """

    kwargs = _get_kwargs(
        inbox_id=inbox_id,
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    inbox_id: int,
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorResponse | ForbiddenError | MessageDetails | None:
    """Get a message

     Returns a single inbound message together with URLs for the
    raw `.eml` file and for each attachment, plus the decoded HTML and
    plain-text bodies. URLs expire after one hour.

    Args:
        inbox_id (int):  Example: 1.
        id (str):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | ForbiddenError | MessageDetails
    """

    return sync_detailed(
        inbox_id=inbox_id,
        id=id,
        client=client,
    ).parsed


async def asyncio_detailed(
    inbox_id: int,
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorResponse | ForbiddenError | MessageDetails]:
    """Get a message

     Returns a single inbound message together with URLs for the
    raw `.eml` file and for each attachment, plus the decoded HTML and
    plain-text bodies. URLs expire after one hour.

    Args:
        inbox_id (int):  Example: 1.
        id (str):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | ForbiddenError | MessageDetails]
    """

    kwargs = _get_kwargs(
        inbox_id=inbox_id,
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    inbox_id: int,
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorResponse | ForbiddenError | MessageDetails | None:
    """Get a message

     Returns a single inbound message together with URLs for the
    raw `.eml` file and for each attachment, plus the decoded HTML and
    plain-text bodies. URLs expire after one hour.

    Args:
        inbox_id (int):  Example: 1.
        id (str):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | ForbiddenError | MessageDetails
    """

    return (
        await asyncio_detailed(
            inbox_id=inbox_id,
            id=id,
            client=client,
        )
    ).parsed
