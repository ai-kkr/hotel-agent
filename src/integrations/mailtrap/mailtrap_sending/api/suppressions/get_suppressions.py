import datetime
from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.bad_request_response import BadRequestResponse
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.rate_limit_exceeded_response import RateLimitExceededResponse
from ...models.suppression import Suppression
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    email: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    last_id: UUID | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["email"] = email

    json_start_time: str | Unset = UNSET
    if not isinstance(start_time, Unset):
        json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time: str | Unset = UNSET
    if not isinstance(end_time, Unset):
        json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    json_last_id: str | Unset = UNSET
    if not isinstance(last_id, Unset):
        json_last_id = str(last_id)
    params["last_id"] = json_last_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/suppressions",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[Suppression]
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = Suppression.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = BadRequestResponse.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = UnauthenticatedResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = PermissionsDeniedResponse.from_dict(response.json())

        return response_403

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
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[Suppression]
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
    email: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    last_id: UUID | Unset = UNSET,
) -> Response[
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[Suppression]
]:
    """List suppressions

     List and search suppressed email addresses. Returns up to 1000 suppressions per request. Use
    `last_id` for cursor-based pagination through large lists.

    Suppressed addresses will not receive any emails from your account.

    Rate limit: 10 requests per minute per account.

    Args:
        email (str | Unset):  Example: suppressed@example.com.
        start_time (datetime.datetime | Unset):  Example: 2025-01-01T00:00:00Z.
        end_time (datetime.datetime | Unset):  Example: 2025-12-31T23:59:59Z.
        last_id (UUID | Unset):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[Suppression]]
    """

    kwargs = _get_kwargs(
        email=email,
        start_time=start_time,
        end_time=end_time,
        last_id=last_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    email: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    last_id: UUID | Unset = UNSET,
) -> (
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[Suppression]
    | None
):
    """List suppressions

     List and search suppressed email addresses. Returns up to 1000 suppressions per request. Use
    `last_id` for cursor-based pagination through large lists.

    Suppressed addresses will not receive any emails from your account.

    Rate limit: 10 requests per minute per account.

    Args:
        email (str | Unset):  Example: suppressed@example.com.
        start_time (datetime.datetime | Unset):  Example: 2025-01-01T00:00:00Z.
        end_time (datetime.datetime | Unset):  Example: 2025-12-31T23:59:59Z.
        last_id (UUID | Unset):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[Suppression]
    """

    return sync_detailed(
        client=client,
        email=email,
        start_time=start_time,
        end_time=end_time,
        last_id=last_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    email: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    last_id: UUID | Unset = UNSET,
) -> Response[
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[Suppression]
]:
    """List suppressions

     List and search suppressed email addresses. Returns up to 1000 suppressions per request. Use
    `last_id` for cursor-based pagination through large lists.

    Suppressed addresses will not receive any emails from your account.

    Rate limit: 10 requests per minute per account.

    Args:
        email (str | Unset):  Example: suppressed@example.com.
        start_time (datetime.datetime | Unset):  Example: 2025-01-01T00:00:00Z.
        end_time (datetime.datetime | Unset):  Example: 2025-12-31T23:59:59Z.
        last_id (UUID | Unset):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[Suppression]]
    """

    kwargs = _get_kwargs(
        email=email,
        start_time=start_time,
        end_time=end_time,
        last_id=last_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    email: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    last_id: UUID | Unset = UNSET,
) -> (
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[Suppression]
    | None
):
    """List suppressions

     List and search suppressed email addresses. Returns up to 1000 suppressions per request. Use
    `last_id` for cursor-based pagination through large lists.

    Suppressed addresses will not receive any emails from your account.

    Rate limit: 10 requests per minute per account.

    Args:
        email (str | Unset):  Example: suppressed@example.com.
        start_time (datetime.datetime | Unset):  Example: 2025-01-01T00:00:00Z.
        end_time (datetime.datetime | Unset):  Example: 2025-12-31T23:59:59Z.
        last_id (UUID | Unset):  Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[Suppression]
    """

    return (
        await asyncio_detailed(
            client=client,
            email=email,
            start_time=start_time,
            end_time=end_time,
            last_id=last_id,
        )
    ).parsed
