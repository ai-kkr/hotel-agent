from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.list_webhooks_response_200 import ListWebhooksResponse200
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/webhooks",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse | None
):
    if response.status_code == 200:
        response_200 = ListWebhooksResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = UnauthenticatedResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = PermissionsDeniedResponse.from_dict(response.json())

        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse
]:
    """List webhooks

     Returns all webhooks for the account.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> (
    ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse | None
):
    """List webhooks

     Returns all webhooks for the account.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse
]:
    """List webhooks

     Returns all webhooks for the account.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> (
    ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse | None
):
    """List webhooks

     Returns all webhooks for the account.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ListWebhooksResponse200 | PermissionsDeniedResponse | UnauthenticatedResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
