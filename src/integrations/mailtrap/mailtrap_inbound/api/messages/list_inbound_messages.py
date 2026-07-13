from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.forbidden_error import ForbiddenError
from ...models.messages_list_response import MessagesListResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    inbox_id: int,
    *,
    last_id: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["last_id"] = last_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/inbound/inboxes/{inbox_id}/messages".format(
            inbox_id=quote(str(inbox_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | ForbiddenError | MessagesListResponse | None:
    if response.status_code == 200:
        response_200 = MessagesListResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | ForbiddenError | MessagesListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    inbox_id: int,
    *,
    client: AuthenticatedClient | Client,
    last_id: str | Unset = UNSET,
) -> Response[ErrorResponse | ForbiddenError | MessagesListResponse]:
    """List messages

     Returns inbound messages received by the inbox, ordered by
    `received_at` descending.

    List responses use cursor pagination. When more results are available
    the response includes a `last_id`; pass it back as the `last_id` query
    parameter to get the next page. When `last_id` is `null` you have
    reached the end.

    Args:
        inbox_id (int):  Example: 1.
        last_id (str | Unset):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | ForbiddenError | MessagesListResponse]
    """

    kwargs = _get_kwargs(
        inbox_id=inbox_id,
        last_id=last_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    inbox_id: int,
    *,
    client: AuthenticatedClient | Client,
    last_id: str | Unset = UNSET,
) -> ErrorResponse | ForbiddenError | MessagesListResponse | None:
    """List messages

     Returns inbound messages received by the inbox, ordered by
    `received_at` descending.

    List responses use cursor pagination. When more results are available
    the response includes a `last_id`; pass it back as the `last_id` query
    parameter to get the next page. When `last_id` is `null` you have
    reached the end.

    Args:
        inbox_id (int):  Example: 1.
        last_id (str | Unset):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | ForbiddenError | MessagesListResponse
    """

    return sync_detailed(
        inbox_id=inbox_id,
        client=client,
        last_id=last_id,
    ).parsed


async def asyncio_detailed(
    inbox_id: int,
    *,
    client: AuthenticatedClient | Client,
    last_id: str | Unset = UNSET,
) -> Response[ErrorResponse | ForbiddenError | MessagesListResponse]:
    """List messages

     Returns inbound messages received by the inbox, ordered by
    `received_at` descending.

    List responses use cursor pagination. When more results are available
    the response includes a `last_id`; pass it back as the `last_id` query
    parameter to get the next page. When `last_id` is `null` you have
    reached the end.

    Args:
        inbox_id (int):  Example: 1.
        last_id (str | Unset):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | ForbiddenError | MessagesListResponse]
    """

    kwargs = _get_kwargs(
        inbox_id=inbox_id,
        last_id=last_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    inbox_id: int,
    *,
    client: AuthenticatedClient | Client,
    last_id: str | Unset = UNSET,
) -> ErrorResponse | ForbiddenError | MessagesListResponse | None:
    """List messages

     Returns inbound messages received by the inbox, ordered by
    `received_at` descending.

    List responses use cursor pagination. When more results are available
    the response includes a `last_id`; pass it back as the `last_id` query
    parameter to get the next page. When `last_id` is `null` you have
    reached the end.

    Args:
        inbox_id (int):  Example: 1.
        last_id (str | Unset):  Example: 1700000000000123.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | ForbiddenError | MessagesListResponse
    """

    return (
        await asyncio_detailed(
            inbox_id=inbox_id,
            client=client,
            last_id=last_id,
        )
    ).parsed
