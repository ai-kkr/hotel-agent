from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.not_found_response import NotFoundResponse
from ...models.rate_limit_exceeded_response import RateLimitExceededResponse
from ...models.sending_message import SendingMessage
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import Response


def _get_kwargs(
    sending_message_id: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/email_logs/{sending_message_id}".format(
            sending_message_id=quote(str(sending_message_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    NotFoundResponse
    | RateLimitExceededResponse
    | SendingMessage
    | UnauthenticatedResponse
    | None
):
    if response.status_code == 200:
        response_200 = SendingMessage.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = UnauthenticatedResponse.from_dict(response.json())

        return response_401

    if response.status_code == 404:
        response_404 = NotFoundResponse.from_dict(response.json())

        return response_404

    if response.status_code == 429:
        response_429 = RateLimitExceededResponse.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    NotFoundResponse
    | RateLimitExceededResponse
    | SendingMessage
    | UnauthenticatedResponse
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    sending_message_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    NotFoundResponse
    | RateLimitExceededResponse
    | SendingMessage
    | UnauthenticatedResponse
]:
    """Get an email log message by ID

     Returns a single message by message UUID. Message must belong to the account and a domain the token
    can access.

    Args:
        sending_message_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[NotFoundResponse | RateLimitExceededResponse | SendingMessage | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        sending_message_id=sending_message_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    sending_message_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> (
    NotFoundResponse
    | RateLimitExceededResponse
    | SendingMessage
    | UnauthenticatedResponse
    | None
):
    """Get an email log message by ID

     Returns a single message by message UUID. Message must belong to the account and a domain the token
    can access.

    Args:
        sending_message_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        NotFoundResponse | RateLimitExceededResponse | SendingMessage | UnauthenticatedResponse
    """

    return sync_detailed(
        sending_message_id=sending_message_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    sending_message_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    NotFoundResponse
    | RateLimitExceededResponse
    | SendingMessage
    | UnauthenticatedResponse
]:
    """Get an email log message by ID

     Returns a single message by message UUID. Message must belong to the account and a domain the token
    can access.

    Args:
        sending_message_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[NotFoundResponse | RateLimitExceededResponse | SendingMessage | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        sending_message_id=sending_message_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    sending_message_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> (
    NotFoundResponse
    | RateLimitExceededResponse
    | SendingMessage
    | UnauthenticatedResponse
    | None
):
    """Get an email log message by ID

     Returns a single message by message UUID. Message must belong to the account and a domain the token
    can access.

    Args:
        sending_message_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        NotFoundResponse | RateLimitExceededResponse | SendingMessage | UnauthenticatedResponse
    """

    return (
        await asyncio_detailed(
            sending_message_id=sending_message_id,
            client=client,
        )
    ).parsed
