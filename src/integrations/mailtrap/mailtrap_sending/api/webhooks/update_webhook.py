from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.not_found_response import NotFoundResponse
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...models.unprocessable_entity import UnprocessableEntity
from ...models.update_webhook_body import UpdateWebhookBody
from ...models.update_webhook_response_200 import UpdateWebhookResponse200
from ...types import Response


def _get_kwargs(
    webhook_id: int,
    *,
    body: UpdateWebhookBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/webhooks/{webhook_id}".format(
            webhook_id=quote(str(webhook_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | UpdateWebhookResponse200
    | None
):
    if response.status_code == 200:
        response_200 = UpdateWebhookResponse200.from_dict(response.json())

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
    NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | UpdateWebhookResponse200
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    webhook_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateWebhookBody,
) -> Response[
    NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | UpdateWebhookResponse200
]:
    """Update a webhook

     Update an existing webhook.

    Args:
        webhook_id (int):  Example: 1.
        body (UpdateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | UpdateWebhookResponse200]
    """

    kwargs = _get_kwargs(
        webhook_id=webhook_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    webhook_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateWebhookBody,
) -> (
    NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | UpdateWebhookResponse200
    | None
):
    """Update a webhook

     Update an existing webhook.

    Args:
        webhook_id (int):  Example: 1.
        body (UpdateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | UpdateWebhookResponse200
    """

    return sync_detailed(
        webhook_id=webhook_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    webhook_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateWebhookBody,
) -> Response[
    NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | UpdateWebhookResponse200
]:
    """Update a webhook

     Update an existing webhook.

    Args:
        webhook_id (int):  Example: 1.
        body (UpdateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | UpdateWebhookResponse200]
    """

    kwargs = _get_kwargs(
        webhook_id=webhook_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    webhook_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateWebhookBody,
) -> (
    NotFoundResponse
    | PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | UpdateWebhookResponse200
    | None
):
    """Update a webhook

     Update an existing webhook.

    Args:
        webhook_id (int):  Example: 1.
        body (UpdateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        NotFoundResponse | PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | UpdateWebhookResponse200
    """

    return (
        await asyncio_detailed(
            webhook_id=webhook_id,
            client=client,
            body=body,
        )
    ).parsed
