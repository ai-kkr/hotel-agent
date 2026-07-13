from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.batch_email_request import BatchEmailRequest
from ...models.batch_sent_response import BatchSentResponse
from ...models.send_email_error_response import SendEmailErrorResponse
from ...types import Response


def _get_kwargs(
    *,
    body: BatchEmailRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/batch",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> BatchSentResponse | SendEmailErrorResponse | None:
    if response.status_code == 200:
        response_200 = BatchSentResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = SendEmailErrorResponse.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = SendEmailErrorResponse.from_dict(response.json())

        return response_401

    if response.status_code == 500:
        response_500 = SendEmailErrorResponse.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[BatchSentResponse | SendEmailErrorResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: BatchEmailRequest,
) -> Response[BatchSentResponse | SendEmailErrorResponse]:
    """Batch send emails

     Send up to 500 transactional emails in a single API call. Each email can have unique recipients and
    content while sharing base properties.

    **Limits:**
    - Maximum 500 messages per call
    - Maximum 50 MB total payload size (including attachments)

    **Note:** The endpoint returns HTTP 200 even if individual messages fail. Check the `responses`
    array for individual message status.

    Args:
        body (BatchEmailRequest): Send multiple emails in a single API call (up to 500)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BatchSentResponse | SendEmailErrorResponse]
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
    body: BatchEmailRequest,
) -> BatchSentResponse | SendEmailErrorResponse | None:
    """Batch send emails

     Send up to 500 transactional emails in a single API call. Each email can have unique recipients and
    content while sharing base properties.

    **Limits:**
    - Maximum 500 messages per call
    - Maximum 50 MB total payload size (including attachments)

    **Note:** The endpoint returns HTTP 200 even if individual messages fail. Check the `responses`
    array for individual message status.

    Args:
        body (BatchEmailRequest): Send multiple emails in a single API call (up to 500)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BatchSentResponse | SendEmailErrorResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: BatchEmailRequest,
) -> Response[BatchSentResponse | SendEmailErrorResponse]:
    """Batch send emails

     Send up to 500 transactional emails in a single API call. Each email can have unique recipients and
    content while sharing base properties.

    **Limits:**
    - Maximum 500 messages per call
    - Maximum 50 MB total payload size (including attachments)

    **Note:** The endpoint returns HTTP 200 even if individual messages fail. Check the `responses`
    array for individual message status.

    Args:
        body (BatchEmailRequest): Send multiple emails in a single API call (up to 500)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BatchSentResponse | SendEmailErrorResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: BatchEmailRequest,
) -> BatchSentResponse | SendEmailErrorResponse | None:
    """Batch send emails

     Send up to 500 transactional emails in a single API call. Each email can have unique recipients and
    content while sharing base properties.

    **Limits:**
    - Maximum 500 messages per call
    - Maximum 50 MB total payload size (including attachments)

    **Note:** The endpoint returns HTTP 200 even if individual messages fail. Check the `responses`
    array for individual message status.

    Args:
        body (BatchEmailRequest): Send multiple emails in a single API call (up to 500)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BatchSentResponse | SendEmailErrorResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
