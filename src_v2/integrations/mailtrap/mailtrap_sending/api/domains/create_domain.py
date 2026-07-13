from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_domain_body import CreateDomainBody
from ...models.domain import Domain
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...models.unprocessable_entity import UnprocessableEntity
from ...types import Response


def _get_kwargs(
    *,
    body: CreateDomainBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/domains",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Domain
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
    Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
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
    body: CreateDomainBody,
) -> Response[
    Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
]:
    """Create domain

     Create a domain for email authentication. After creation, verify the domain by adding DNS records.

    **Process:**
    1. Create the domain
    2. Add DNS records (SPF, DKIM, DMARC)
    3. Verify the records
    4. Start sending emails

    Args:
        body (CreateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: CreateDomainBody,
) -> (
    Domain
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    """Create domain

     Create a domain for email authentication. After creation, verify the domain by adding DNS records.

    **Process:**
    1. Create the domain
    2. Add DNS records (SPF, DKIM, DMARC)
    3. Verify the records
    4. Start sending emails

    Args:
        body (CreateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateDomainBody,
) -> Response[
    Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
]:
    """Create domain

     Create a domain for email authentication. After creation, verify the domain by adding DNS records.

    **Process:**
    1. Create the domain
    2. Add DNS records (SPF, DKIM, DMARC)
    3. Verify the records
    4. Start sending emails

    Args:
        body (CreateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CreateDomainBody,
) -> (
    Domain
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    """Create domain

     Create a domain for email authentication. After creation, verify the domain by adding DNS records.

    **Process:**
    1. Create the domain
    2. Add DNS records (SPF, DKIM, DMARC)
    3. Verify the records
    4. Start sending emails

    Args:
        body (CreateDomainBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Domain | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
