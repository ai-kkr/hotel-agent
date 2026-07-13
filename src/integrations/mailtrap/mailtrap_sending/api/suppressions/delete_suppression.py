from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.not_found_response import NotFoundResponse
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.suppression import Suppression
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import Response


def _get_kwargs(
    suppression_id: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/suppressions/{suppression_id}".format(
            suppression_id=quote(str(suppression_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    NotFoundResponse
    | PermissionsDeniedResponse
    | Suppression
    | UnauthenticatedResponse
    | None
):
    if response.status_code == 200:
        response_200 = Suppression.from_dict(response.json())

        return response_200

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
    NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    suppression_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse
]:
    r"""Delete suppression

     Remove an email from the suppression list to allow sending again.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Args:
        suppression_id (UUID):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        suppression_id=suppression_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    suppression_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> (
    NotFoundResponse
    | PermissionsDeniedResponse
    | Suppression
    | UnauthenticatedResponse
    | None
):
    r"""Delete suppression

     Remove an email from the suppression list to allow sending again.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Args:
        suppression_id (UUID):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse
    """

    return sync_detailed(
        suppression_id=suppression_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    suppression_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse
]:
    r"""Delete suppression

     Remove an email from the suppression list to allow sending again.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Args:
        suppression_id (UUID):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        suppression_id=suppression_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    suppression_id: UUID,
    *,
    client: AuthenticatedClient | Client,
) -> (
    NotFoundResponse
    | PermissionsDeniedResponse
    | Suppression
    | UnauthenticatedResponse
    | None
):
    r"""Delete suppression

     Remove an email from the suppression list to allow sending again.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Args:
        suppression_id (UUID):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        NotFoundResponse | PermissionsDeniedResponse | Suppression | UnauthenticatedResponse
    """

    return (
        await asyncio_detailed(
            suppression_id=suppression_id,
            client=client,
        )
    ).parsed
