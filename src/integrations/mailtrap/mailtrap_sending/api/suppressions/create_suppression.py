from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_suppression_body import CreateSuppressionBody
from ...models.create_suppression_response_201 import CreateSuppressionResponse201
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.rate_limit_exceeded_response import RateLimitExceededResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...models.unprocessable_entity import UnprocessableEntity
from ...types import Response


def _get_kwargs(
    *,
    body: CreateSuppressionBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/suppressions",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    CreateSuppressionResponse201
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    if response.status_code == 201:
        response_201 = CreateSuppressionResponse201.from_dict(response.json())

        return response_201

    if response.status_code == 401:
        response_401 = UnauthenticatedResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = PermissionsDeniedResponse.from_dict(response.json())

        return response_403

    if response.status_code == 422:
        response_422 = UnprocessableEntity.from_dict(response.json())

        return response_422

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
    CreateSuppressionResponse201
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
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
    *,
    client: AuthenticatedClient | Client,
    body: CreateSuppressionBody,
) -> Response[
    CreateSuppressionResponse201
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
]:
    r"""Create suppression

     Add an email address to the suppression list. Suppressed addresses will not receive any emails from
    your account.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Rate limit: 10 requests per minute per account.

    Args:
        body (CreateSuppressionBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateSuppressionResponse201 | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | UnprocessableEntity]
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
    body: CreateSuppressionBody,
) -> (
    CreateSuppressionResponse201
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    r"""Create suppression

     Add an email address to the suppression list. Suppressed addresses will not receive any emails from
    your account.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Rate limit: 10 requests per minute per account.

    Args:
        body (CreateSuppressionBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateSuppressionResponse201 | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | UnprocessableEntity
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateSuppressionBody,
) -> Response[
    CreateSuppressionResponse201
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
]:
    r"""Create suppression

     Add an email address to the suppression list. Suppressed addresses will not receive any emails from
    your account.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Rate limit: 10 requests per minute per account.

    Args:
        body (CreateSuppressionBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateSuppressionResponse201 | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CreateSuppressionBody,
) -> (
    CreateSuppressionResponse201
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | None
):
    r"""Create suppression

     Add an email address to the suppression list. Suppressed addresses will not receive any emails from
    your account.

    {% hint style=\"warning\" %}
    This endpoint requires admin-level access.
    {% endhint %}

    Rate limit: 10 requests per minute per account.

    Args:
        body (CreateSuppressionBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateSuppressionResponse201 | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | UnprocessableEntity
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
