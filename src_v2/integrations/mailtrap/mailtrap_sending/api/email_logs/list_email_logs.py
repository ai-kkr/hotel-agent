from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.bad_request_response import BadRequestResponse
from ...models.email_logs_list_filters import EmailLogsListFilters
from ...models.email_logs_list_response import EmailLogsListResponse
from ...models.not_found_response import NotFoundResponse
from ...models.rate_limit_exceeded_response import RateLimitExceededResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    search_after: UUID | Unset = UNSET,
    filters: EmailLogsListFilters | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_search_after: str | Unset = UNSET
    if not isinstance(search_after, Unset):
        json_search_after = str(search_after)
    params["search_after"] = json_search_after

    json_filters: dict[str, Any] | Unset = UNSET
    if not isinstance(filters, Unset):
        json_filters = filters.to_dict()
    if not isinstance(json_filters, Unset):
        params.update(json_filters)

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/email_logs",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    BadRequestResponse
    | EmailLogsListResponse
    | NotFoundResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | None
):
    if response.status_code == 200:
        response_200 = EmailLogsListResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = BadRequestResponse.from_dict(response.json())

        return response_400

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
    BadRequestResponse
    | EmailLogsListResponse
    | NotFoundResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
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
    search_after: UUID | Unset = UNSET,
    filters: EmailLogsListFilters | Unset = UNSET,
) -> Response[
    BadRequestResponse
    | EmailLogsListResponse
    | NotFoundResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
]:
    """List email logs

     Returns a paginated list of email logs (messages) for the account.
    Results are restricted to domains the authenticated token has access to.
    Invalid or unknown filters are ignored. Results are ordered by sent_at descending.

    Args:
        search_after (UUID | Unset):
        filters (EmailLogsListFilters | Unset): Key-value map of filter name to filter spec. Each
            spec has operator and optional value.
            Date range uses sent_after / sent_before at top level of filters (see below).
            In query params, array values use bracket notation:
            `filters[field][value][]=a&filters[field][value][]=b`.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BadRequestResponse | EmailLogsListResponse | NotFoundResponse | RateLimitExceededResponse | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        search_after=search_after,
        filters=filters,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    search_after: UUID | Unset = UNSET,
    filters: EmailLogsListFilters | Unset = UNSET,
) -> (
    BadRequestResponse
    | EmailLogsListResponse
    | NotFoundResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | None
):
    """List email logs

     Returns a paginated list of email logs (messages) for the account.
    Results are restricted to domains the authenticated token has access to.
    Invalid or unknown filters are ignored. Results are ordered by sent_at descending.

    Args:
        search_after (UUID | Unset):
        filters (EmailLogsListFilters | Unset): Key-value map of filter name to filter spec. Each
            spec has operator and optional value.
            Date range uses sent_after / sent_before at top level of filters (see below).
            In query params, array values use bracket notation:
            `filters[field][value][]=a&filters[field][value][]=b`.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BadRequestResponse | EmailLogsListResponse | NotFoundResponse | RateLimitExceededResponse | UnauthenticatedResponse
    """

    return sync_detailed(
        client=client,
        search_after=search_after,
        filters=filters,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    search_after: UUID | Unset = UNSET,
    filters: EmailLogsListFilters | Unset = UNSET,
) -> Response[
    BadRequestResponse
    | EmailLogsListResponse
    | NotFoundResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
]:
    """List email logs

     Returns a paginated list of email logs (messages) for the account.
    Results are restricted to domains the authenticated token has access to.
    Invalid or unknown filters are ignored. Results are ordered by sent_at descending.

    Args:
        search_after (UUID | Unset):
        filters (EmailLogsListFilters | Unset): Key-value map of filter name to filter spec. Each
            spec has operator and optional value.
            Date range uses sent_after / sent_before at top level of filters (see below).
            In query params, array values use bracket notation:
            `filters[field][value][]=a&filters[field][value][]=b`.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BadRequestResponse | EmailLogsListResponse | NotFoundResponse | RateLimitExceededResponse | UnauthenticatedResponse]
    """

    kwargs = _get_kwargs(
        search_after=search_after,
        filters=filters,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    search_after: UUID | Unset = UNSET,
    filters: EmailLogsListFilters | Unset = UNSET,
) -> (
    BadRequestResponse
    | EmailLogsListResponse
    | NotFoundResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | None
):
    """List email logs

     Returns a paginated list of email logs (messages) for the account.
    Results are restricted to domains the authenticated token has access to.
    Invalid or unknown filters are ignored. Results are ordered by sent_at descending.

    Args:
        search_after (UUID | Unset):
        filters (EmailLogsListFilters | Unset): Key-value map of filter name to filter spec. Each
            spec has operator and optional value.
            Date range uses sent_after / sent_before at top level of filters (see below).
            In query params, array values use bracket notation:
            `filters[field][value][]=a&filters[field][value][]=b`.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BadRequestResponse | EmailLogsListResponse | NotFoundResponse | RateLimitExceededResponse | UnauthenticatedResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            search_after=search_after,
            filters=filters,
        )
    ).parsed
