from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.domain import Domain
from ...models.not_found_response import NotFoundResponse
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...models.unprocessable_entity import UnprocessableEntity
from ...models.update_domain_body import UpdateDomainBody
from ...types import Response


def _get_kwargs(
    domain_id: int,
    *,
    body: UpdateDomainBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/domains/{domain_id}".format(
            domain_id=quote(str(domain_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Domain
    | NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    if response.status_code == 200:
        response_200 = Domain.from_dict(response.json())

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

    if response.status_code == 422:
        response_422 = UnprocessableEntity.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Domain
    | NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
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
    body: UpdateDomainBody,
) -> Response[
    Domain
    | NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
]:
    """Update domain

     Update configuration settings for a domain.

    Args:
        domain_id (int):  Example: 1.
        body (UpdateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Domain | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        domain_id=domain_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDomainBody,
) -> (
    Domain
    | NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    """Update domain

     Update configuration settings for a domain.

    Args:
        domain_id (int):  Example: 1.
        body (UpdateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Domain | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
    """

    return sync_detailed(
        domain_id=domain_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDomainBody,
) -> Response[
    Domain
    | NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
]:
    """Update domain

     Update configuration settings for a domain.

    Args:
        domain_id (int):  Example: 1.
        body (UpdateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Domain | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        domain_id=domain_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    domain_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDomainBody,
) -> (
    Domain
    | NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    """Update domain

     Update configuration settings for a domain.

    Args:
        domain_id (int):  Example: 1.
        body (UpdateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Domain | NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
    """

    return (
        await asyncio_detailed(
            domain_id=domain_id,
            client=client,
            body=body,
        )
    ).parsed
