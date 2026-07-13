from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.not_found_response import NotFoundResponse
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import Response


def _get_kwargs(
    domain_id: int,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/domains/{domain_id}".format(
            domain_id=quote(str(domain_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | None
):
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 401:
        response_401 = UnauthenticatedResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = PermissionsDeniedResponse.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = NotFoundResponse.from_dict(response.json())

        return response_404

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse
]:
    """Delete domain

     Remove a domain from your account

    Args:
        domain_id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        domain_id=domain_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> (
    Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | None
):
    """Delete domain

     Remove a domain from your account

    Args:
        domain_id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse
    """

    return sync_detailed(
        domain_id=domain_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse
]:
    """Delete domain

     Remove a domain from your account

    Args:
        domain_id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        domain_id=domain_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
) -> (
    Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | None
):
    """Delete domain

     Remove a domain from your account

    Args:
        domain_id (int):  Example: 1.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse
    """

    return (
        await asyncio_detailed(
            domain_id=domain_id,
            client=client,
        )
    ).parsed
