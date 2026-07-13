from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_webhook_body import CreateWebhookBody
from ...models.permissions_denied_response import PermissionsDeniedResponse
from ...models.unauthenticated_response import UnauthenticatedResponse
from ...models.unprocessable_entity import UnprocessableEntity
from ...models.webhook_create_response import WebhookCreateResponse
from ...types import Response


def _get_kwargs(
    *,
    body: CreateWebhookBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/webhooks",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | WebhookCreateResponse
    | None
):
    if response.status_code == 200:
        response_200 = WebhookCreateResponse.from_dict(response.json())

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
    PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | WebhookCreateResponse
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
    body: CreateWebhookBody,
) -> Response[
    PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | WebhookCreateResponse
]:
    """Create a webhook

     Create a new webhook for the account. The response includes a
    `signing_secret` that is used to [verify webhook signatures](https://docs.mailtrap.io/email-api-
    smtp/advanced/webhooks#webhook-signature-verification).

    Args:
        body (CreateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | WebhookCreateResponse]
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
    body: CreateWebhookBody,
) -> (
    PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | WebhookCreateResponse
    | None
):
    """Create a webhook

     Create a new webhook for the account. The response includes a
    `signing_secret` that is used to [verify webhook signatures](https://docs.mailtrap.io/email-api-
    smtp/advanced/webhooks#webhook-signature-verification).

    Args:
        body (CreateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | WebhookCreateResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateWebhookBody,
) -> Response[
    PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | WebhookCreateResponse
]:
    """Create a webhook

     Create a new webhook for the account. The response includes a
    `signing_secret` that is used to [verify webhook signatures](https://docs.mailtrap.io/email-api-
    smtp/advanced/webhooks#webhook-signature-verification).

    Args:
        body (CreateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | WebhookCreateResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CreateWebhookBody,
) -> (
    PermissionsDeniedResponse
    | UnauthenticatedResponse
    | UnprocessableEntity
    | WebhookCreateResponse
    | None
):
    """Create a webhook

     Create a new webhook for the account. The response includes a
    `signing_secret` that is used to [verify webhook signatures](https://docs.mailtrap.io/email-api-
    smtp/advanced/webhooks#webhook-signature-verification).

    Args:
        body (CreateWebhookBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PermissionsDeniedResponse | UnauthenticatedResponse | UnprocessableEntity | WebhookCreateResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
