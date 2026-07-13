import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.bad_request_response import BadRequestResponse
from ...models.get_account_sending_stats_by_domains_email_service_providers_item import (
    GetAccountSendingStatsByDomainsEmailServiceProvidersItem,
)
from ...models.get_account_sending_stats_by_domains_response_200_item import (
    GetAccountSendingStatsByDomainsResponse200Item,
)
from ...models.get_account_sending_stats_by_domains_sending_streams_item import (
    GetAccountSendingStatsByDomainsSendingStreamsItem,
)
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.rate_limit_exceeded_response import RateLimitExceededResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    start_date: datetime.date,
    end_date: datetime.date,
    domain_ids: list[int] | Unset = UNSET,
    sending_streams: list[GetAccountSendingStatsByDomainsSendingStreamsItem]
    | Unset = UNSET,
    categories: list[str] | Unset = UNSET,
    email_service_providers: list[
        GetAccountSendingStatsByDomainsEmailServiceProvidersItem
    ]
    | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_start_date = start_date.isoformat()
    params["start_date"] = json_start_date

    json_end_date = end_date.isoformat()
    params["end_date"] = json_end_date

    json_domain_ids: list[int] | Unset = UNSET
    if not isinstance(domain_ids, Unset):
        json_domain_ids = domain_ids

    params["domain_ids[]"] = json_domain_ids

    json_sending_streams: list[str] | Unset = UNSET
    if not isinstance(sending_streams, Unset):
        json_sending_streams = []
        for sending_streams_item_data in sending_streams:
            sending_streams_item = sending_streams_item_data.value
            json_sending_streams.append(sending_streams_item)

    params["sending_streams[]"] = json_sending_streams

    json_categories: list[str] | Unset = UNSET
    if not isinstance(categories, Unset):
        json_categories = categories

    params["categories[]"] = json_categories

    json_email_service_providers: list[str] | Unset = UNSET
    if not isinstance(email_service_providers, Unset):
        json_email_service_providers = []
        for email_service_providers_item_data in email_service_providers:
            email_service_providers_item = email_service_providers_item_data.value
            json_email_service_providers.append(email_service_providers_item)

    params["email_service_providers[]"] = json_email_service_providers

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/stats/domains",
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
    | list[GetAccountSendingStatsByDomainsResponse200Item]
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = (
                GetAccountSendingStatsByDomainsResponse200Item.from_dict(
                    response_200_item_data
                )
            )

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
    | list[GetAccountSendingStatsByDomainsResponse200Item]
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
    start_date: datetime.date,
    end_date: datetime.date,
    domain_ids: list[int] | Unset = UNSET,
    sending_streams: list[GetAccountSendingStatsByDomainsSendingStreamsItem]
    | Unset = UNSET,
    categories: list[str] | Unset = UNSET,
    email_service_providers: list[
        GetAccountSendingStatsByDomainsEmailServiceProvidersItem
    ]
    | Unset = UNSET,
) -> Response[
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[GetAccountSendingStatsByDomainsResponse200Item]
]:
    """Get Sending Stats by Domains

     Get account sending stats by domains. Use filters to get specific stats.

    Args:
        start_date (datetime.date):  Example: 2025-01-01.
        end_date (datetime.date):  Example: 2025-12-31.
        domain_ids (list[int] | Unset):  Example: [3938, 3939].
        sending_streams (list[GetAccountSendingStatsByDomainsSendingStreamsItem] | Unset):
            Example: ['transactional', 'bulk'].
        categories (list[str] | Unset):  Example: ['Welcome Email', 'Password Reset'].
        email_service_providers (list[GetAccountSendingStatsByDomainsEmailServiceProvidersItem] |
            Unset):  Example: ['Google', 'Yahoo'].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[GetAccountSendingStatsByDomainsResponse200Item]]
    """

    kwargs = _get_kwargs(
        start_date=start_date,
        end_date=end_date,
        domain_ids=domain_ids,
        sending_streams=sending_streams,
        categories=categories,
        email_service_providers=email_service_providers,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    start_date: datetime.date,
    end_date: datetime.date,
    domain_ids: list[int] | Unset = UNSET,
    sending_streams: list[GetAccountSendingStatsByDomainsSendingStreamsItem]
    | Unset = UNSET,
    categories: list[str] | Unset = UNSET,
    email_service_providers: list[
        GetAccountSendingStatsByDomainsEmailServiceProvidersItem
    ]
    | Unset = UNSET,
) -> (
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[GetAccountSendingStatsByDomainsResponse200Item]
    | None
):
    """Get Sending Stats by Domains

     Get account sending stats by domains. Use filters to get specific stats.

    Args:
        start_date (datetime.date):  Example: 2025-01-01.
        end_date (datetime.date):  Example: 2025-12-31.
        domain_ids (list[int] | Unset):  Example: [3938, 3939].
        sending_streams (list[GetAccountSendingStatsByDomainsSendingStreamsItem] | Unset):
            Example: ['transactional', 'bulk'].
        categories (list[str] | Unset):  Example: ['Welcome Email', 'Password Reset'].
        email_service_providers (list[GetAccountSendingStatsByDomainsEmailServiceProvidersItem] |
            Unset):  Example: ['Google', 'Yahoo'].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[GetAccountSendingStatsByDomainsResponse200Item]
    """

    return sync_detailed(
        client=client,
        start_date=start_date,
        end_date=end_date,
        domain_ids=domain_ids,
        sending_streams=sending_streams,
        categories=categories,
        email_service_providers=email_service_providers,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    start_date: datetime.date,
    end_date: datetime.date,
    domain_ids: list[int] | Unset = UNSET,
    sending_streams: list[GetAccountSendingStatsByDomainsSendingStreamsItem]
    | Unset = UNSET,
    categories: list[str] | Unset = UNSET,
    email_service_providers: list[
        GetAccountSendingStatsByDomainsEmailServiceProvidersItem
    ]
    | Unset = UNSET,
) -> Response[
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[GetAccountSendingStatsByDomainsResponse200Item]
]:
    """Get Sending Stats by Domains

     Get account sending stats by domains. Use filters to get specific stats.

    Args:
        start_date (datetime.date):  Example: 2025-01-01.
        end_date (datetime.date):  Example: 2025-12-31.
        domain_ids (list[int] | Unset):  Example: [3938, 3939].
        sending_streams (list[GetAccountSendingStatsByDomainsSendingStreamsItem] | Unset):
            Example: ['transactional', 'bulk'].
        categories (list[str] | Unset):  Example: ['Welcome Email', 'Password Reset'].
        email_service_providers (list[GetAccountSendingStatsByDomainsEmailServiceProvidersItem] |
            Unset):  Example: ['Google', 'Yahoo'].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[GetAccountSendingStatsByDomainsResponse200Item]]
    """

    kwargs = _get_kwargs(
        start_date=start_date,
        end_date=end_date,
        domain_ids=domain_ids,
        sending_streams=sending_streams,
        categories=categories,
        email_service_providers=email_service_providers,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    start_date: datetime.date,
    end_date: datetime.date,
    domain_ids: list[int] | Unset = UNSET,
    sending_streams: list[GetAccountSendingStatsByDomainsSendingStreamsItem]
    | Unset = UNSET,
    categories: list[str] | Unset = UNSET,
    email_service_providers: list[
        GetAccountSendingStatsByDomainsEmailServiceProvidersItem
    ]
    | Unset = UNSET,
) -> (
    BadRequestResponse
    | PermissionsDeniedResponse
    | RateLimitExceededResponse
    | UnauthenticatedResponse
    | list[GetAccountSendingStatsByDomainsResponse200Item]
    | None
):
    """Get Sending Stats by Domains

     Get account sending stats by domains. Use filters to get specific stats.

    Args:
        start_date (datetime.date):  Example: 2025-01-01.
        end_date (datetime.date):  Example: 2025-12-31.
        domain_ids (list[int] | Unset):  Example: [3938, 3939].
        sending_streams (list[GetAccountSendingStatsByDomainsSendingStreamsItem] | Unset):
            Example: ['transactional', 'bulk'].
        categories (list[str] | Unset):  Example: ['Welcome Email', 'Password Reset'].
        email_service_providers (list[GetAccountSendingStatsByDomainsEmailServiceProvidersItem] |
            Unset):  Example: ['Google', 'Yahoo'].

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BadRequestResponse | PermissionsDeniedResponse | RateLimitExceededResponse | UnauthenticatedResponse | list[GetAccountSendingStatsByDomainsResponse200Item]
    """

    return (
        await asyncio_detailed(
            client=client,
            start_date=start_date,
            end_date=end_date,
            domain_ids=domain_ids,
            sending_streams=sending_streams,
            categories=categories,
            email_service_providers=email_service_providers,
        )
    ).parsed
