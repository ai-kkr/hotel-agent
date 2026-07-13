from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.folder import Folder
from ...models.folder_input import FolderInput
from ...models.forbidden_error import ForbiddenError
from ...models.unprocessable_entity import UnprocessableEntity
from ...types import Response


def _get_kwargs(
    folder_id: int,
    *,
    body: FolderInput,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/inbound/folders/{folder_id}".format(
            folder_id=quote(str(folder_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorResponse | Folder | ForbiddenError | UnprocessableEntity | None:
    if response.status_code == 200:
        response_200 = Folder.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorResponse.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ForbiddenError.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())

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
) -> Response[ErrorResponse | Folder | ForbiddenError | UnprocessableEntity]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    folder_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: FolderInput,
) -> Response[ErrorResponse | Folder | ForbiddenError | UnprocessableEntity]:
    """Update a folder

     Update an inbound folder.

    Args:
        folder_id (int):  Example: 1.
        body (FolderInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | Folder | ForbiddenError | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    folder_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: FolderInput,
) -> ErrorResponse | Folder | ForbiddenError | UnprocessableEntity | None:
    """Update a folder

     Update an inbound folder.

    Args:
        folder_id (int):  Example: 1.
        body (FolderInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | Folder | ForbiddenError | UnprocessableEntity
    """

    return sync_detailed(
        folder_id=folder_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    folder_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: FolderInput,
) -> Response[ErrorResponse | Folder | ForbiddenError | UnprocessableEntity]:
    """Update a folder

     Update an inbound folder.

    Args:
        folder_id (int):  Example: 1.
        body (FolderInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | Folder | ForbiddenError | UnprocessableEntity]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    folder_id: int,
    *,
    client: AuthenticatedClient | Client,
    body: FolderInput,
) -> ErrorResponse | Folder | ForbiddenError | UnprocessableEntity | None:
    """Update a folder

     Update an inbound folder.

    Args:
        folder_id (int):  Example: 1.
        body (FolderInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | Folder | ForbiddenError | UnprocessableEntity
    """

    return (
        await asyncio_detailed(
            folder_id=folder_id,
            client=client,
            body=body,
        )
    ).parsed
