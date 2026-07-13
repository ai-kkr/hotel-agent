from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.from_template import FromTemplate
from ...models.html_only import HTMLOnly
from ...models.send_email_error_response import SendEmailErrorResponse
from ...models.sent_response import SentResponse
from ...models.text_and_html import TextAndHTML
from ...models.text_only import TextOnly
from ...types import Response


def _get_kwargs(
    *,
    body: FromTemplate | HTMLOnly | TextAndHTML | TextOnly,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/send",
    }

    if isinstance(body, TextOnly) or isinstance(body, HTMLOnly) or isinstance(body, TextAndHTML):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> SendEmailErrorResponse | SentResponse | None:
    if response.status_code == 200:
        response_200 = SentResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = SendEmailErrorResponse.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = SendEmailErrorResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = SendEmailErrorResponse.from_dict(response.json())

        return response_403

    if response.status_code == 500:
        response_500 = SendEmailErrorResponse.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[SendEmailErrorResponse | SentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: FromTemplate | HTMLOnly | TextAndHTML | TextOnly,
) -> Response[SendEmailErrorResponse | SentResponse]:
    """Send transactional email

     Send a single transactional email with text, HTML, or template content.

    Use this endpoint for:
    - Order confirmations
    - Password reset emails
    - Account notifications
    - Welcome emails
    - System alerts

    Args:
        body (FromTemplate | HTMLOnly | TextAndHTML | TextOnly):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SendEmailErrorResponse | SentResponse]
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
    body: FromTemplate | HTMLOnly | TextAndHTML | TextOnly,
) -> SendEmailErrorResponse | SentResponse | None:
    """Send transactional email

     Send a single transactional email with text, HTML, or template content.

    Use this endpoint for:
    - Order confirmations
    - Password reset emails
    - Account notifications
    - Welcome emails
    - System alerts

    Args:
        body (FromTemplate | HTMLOnly | TextAndHTML | TextOnly):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SendEmailErrorResponse | SentResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: FromTemplate | HTMLOnly | TextAndHTML | TextOnly,
) -> Response[SendEmailErrorResponse | SentResponse]:
    """Send transactional email

     Send a single transactional email with text, HTML, or template content.

    Use this endpoint for:
    - Order confirmations
    - Password reset emails
    - Account notifications
    - Welcome emails
    - System alerts

    Args:
        body (FromTemplate | HTMLOnly | TextAndHTML | TextOnly):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SendEmailErrorResponse | SentResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: FromTemplate | HTMLOnly | TextAndHTML | TextOnly,
) -> SendEmailErrorResponse | SentResponse | None:
    """Send transactional email

     Send a single transactional email with text, HTML, or template content.

    Use this endpoint for:
    - Order confirmations
    - Password reset emails
    - Account notifications
    - Welcome emails
    - System alerts

    Args:
        body (FromTemplate | HTMLOnly | TextAndHTML | TextOnly):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SendEmailErrorResponse | SentResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
