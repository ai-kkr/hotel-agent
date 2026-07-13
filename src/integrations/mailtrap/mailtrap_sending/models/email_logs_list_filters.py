from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.filter_category import FilterCategory
    from ..models.filter_ci_contain_string import FilterCiContainString
    from ..models.filter_ci_equal_string import FilterCiEqualString
    from ..models.filter_clicks_count import FilterClicksCount
    from ..models.filter_contain_string import FilterContainString
    from ..models.filter_domain_id import FilterDomainId
    from ..models.filter_email_service_provider import FilterEmailServiceProvider
    from ..models.filter_empty_string import FilterEmptyString
    from ..models.filter_equal_string import FilterEqualString
    from ..models.filter_events import FilterEvents
    from ..models.filter_opens_count import FilterOpensCount
    from ..models.filter_sending_stream import FilterSendingStream
    from ..models.filter_status import FilterStatus


T = TypeVar("T", bound="EmailLogsListFilters")


@_attrs_define
class EmailLogsListFilters:
    """Key-value map of filter name to filter spec. Each spec has operator and optional value.
    Date range uses sent_after / sent_before at top level of filters (see below).
    In query params, array values use bracket notation: `filters[field][value][]=a&filters[field][value][]=b`.

        Attributes:
            sent_after (datetime.datetime | Unset): Start of sent-at range (ISO 8601). Must be before or equal to
                sent_before. Example: 2025-01-01T00:00:00Z.
            sent_before (datetime.datetime | Unset): End of sent-at range (ISO 8601). Must be after or equal to sent_after.
                Example: 2025-01-31T23:59:59Z.
            to (FilterCiContainString | FilterCiEqualString | Unset):  Example: {'operator': 'ci_equal', 'value':
                'recipient@example.com'}.
            from_ (FilterCiContainString | FilterCiEqualString | Unset):  Example: {'operator': 'ci_contain', 'value':
                'noreply@example.com'}.
            subject (FilterCiContainString | FilterCiEqualString | FilterEmptyString | Unset):  Example: {'operator':
                'ci_contain', 'value': 'Order confirmation'}.
            status (FilterStatus | Unset):
            events (FilterEvents | Unset):
            clicks_count (FilterClicksCount | Unset):  Example: {'operator': 'greater_than', 'value': 0}.
            opens_count (FilterOpensCount | Unset):  Example: {'operator': 'equal', 'value': 1}.
            client_ip (FilterContainString | FilterEqualString | Unset):  Example: {'operator': 'equal', 'value':
                '203.0.113.42'}.
            sending_ip (FilterContainString | FilterEqualString | Unset):  Example: {'operator': 'contain', 'value':
                '192.0.2'}.
            email_service_provider_response (FilterCiContainString | FilterCiEqualString | Unset):  Example: {'operator':
                'ci_contain', 'value': 'User unknown'}.
            email_service_provider (FilterEmailServiceProvider | Unset):  Example: {'operator': 'equal', 'value': 'Google'}.
            recipient_mx (FilterCiContainString | FilterCiEqualString | Unset):  Example: {'operator': 'ci_equal', 'value':
                'gmail-smtp-in.l.google.com'}.
            category (FilterCategory | Unset):  Example: {'operator': 'equal', 'value': 'Welcome Email'}.
            domain_id (FilterDomainId | Unset):  Example: {'operator': 'equal', 'value': 3938}.
            sending_stream (FilterSendingStream | Unset):  Example: {'operator': 'equal', 'value': 'transactional'}.
    """

    sent_after: datetime.datetime | Unset = UNSET
    sent_before: datetime.datetime | Unset = UNSET
    to: FilterCiContainString | FilterCiEqualString | Unset = UNSET
    from_: FilterCiContainString | FilterCiEqualString | Unset = UNSET
    subject: FilterCiContainString | FilterCiEqualString | FilterEmptyString | Unset = (
        UNSET
    )
    status: FilterStatus | Unset = UNSET
    events: FilterEvents | Unset = UNSET
    clicks_count: FilterClicksCount | Unset = UNSET
    opens_count: FilterOpensCount | Unset = UNSET
    client_ip: FilterContainString | FilterEqualString | Unset = UNSET
    sending_ip: FilterContainString | FilterEqualString | Unset = UNSET
    email_service_provider_response: (
        FilterCiContainString | FilterCiEqualString | Unset
    ) = UNSET
    email_service_provider: FilterEmailServiceProvider | Unset = UNSET
    recipient_mx: FilterCiContainString | FilterCiEqualString | Unset = UNSET
    category: FilterCategory | Unset = UNSET
    domain_id: FilterDomainId | Unset = UNSET
    sending_stream: FilterSendingStream | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.filter_ci_contain_string import FilterCiContainString
        from ..models.filter_ci_equal_string import FilterCiEqualString
        from ..models.filter_equal_string import FilterEqualString

        sent_after: str | Unset = UNSET
        if not isinstance(self.sent_after, Unset):
            sent_after = self.sent_after.isoformat()

        sent_before: str | Unset = UNSET
        if not isinstance(self.sent_before, Unset):
            sent_before = self.sent_before.isoformat()

        to: dict[str, Any] | Unset
        if isinstance(self.to, Unset):
            to = UNSET
        elif isinstance(self.to, FilterCiEqualString):
            to = self.to.to_dict()
        else:
            to = self.to.to_dict()

        from_: dict[str, Any] | Unset
        if isinstance(self.from_, Unset):
            from_ = UNSET
        elif isinstance(self.from_, FilterCiEqualString):
            from_ = self.from_.to_dict()
        else:
            from_ = self.from_.to_dict()

        subject: dict[str, Any] | Unset
        if isinstance(self.subject, Unset):
            subject = UNSET
        elif isinstance(self.subject, FilterCiEqualString) or isinstance(self.subject, FilterCiContainString):
            subject = self.subject.to_dict()
        else:
            subject = self.subject.to_dict()

        status: dict[str, Any] | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.to_dict()

        events: dict[str, Any] | Unset = UNSET
        if not isinstance(self.events, Unset):
            events = self.events.to_dict()

        clicks_count: dict[str, Any] | Unset = UNSET
        if not isinstance(self.clicks_count, Unset):
            clicks_count = self.clicks_count.to_dict()

        opens_count: dict[str, Any] | Unset = UNSET
        if not isinstance(self.opens_count, Unset):
            opens_count = self.opens_count.to_dict()

        client_ip: dict[str, Any] | Unset
        if isinstance(self.client_ip, Unset):
            client_ip = UNSET
        elif isinstance(self.client_ip, FilterEqualString):
            client_ip = self.client_ip.to_dict()
        else:
            client_ip = self.client_ip.to_dict()

        sending_ip: dict[str, Any] | Unset
        if isinstance(self.sending_ip, Unset):
            sending_ip = UNSET
        elif isinstance(self.sending_ip, FilterEqualString):
            sending_ip = self.sending_ip.to_dict()
        else:
            sending_ip = self.sending_ip.to_dict()

        email_service_provider_response: dict[str, Any] | Unset
        if isinstance(self.email_service_provider_response, Unset):
            email_service_provider_response = UNSET
        elif isinstance(self.email_service_provider_response, FilterCiEqualString):
            email_service_provider_response = (
                self.email_service_provider_response.to_dict()
            )
        else:
            email_service_provider_response = (
                self.email_service_provider_response.to_dict()
            )

        email_service_provider: dict[str, Any] | Unset = UNSET
        if not isinstance(self.email_service_provider, Unset):
            email_service_provider = self.email_service_provider.to_dict()

        recipient_mx: dict[str, Any] | Unset
        if isinstance(self.recipient_mx, Unset):
            recipient_mx = UNSET
        elif isinstance(self.recipient_mx, FilterCiEqualString):
            recipient_mx = self.recipient_mx.to_dict()
        else:
            recipient_mx = self.recipient_mx.to_dict()

        category: dict[str, Any] | Unset = UNSET
        if not isinstance(self.category, Unset):
            category = self.category.to_dict()

        domain_id: dict[str, Any] | Unset = UNSET
        if not isinstance(self.domain_id, Unset):
            domain_id = self.domain_id.to_dict()

        sending_stream: dict[str, Any] | Unset = UNSET
        if not isinstance(self.sending_stream, Unset):
            sending_stream = self.sending_stream.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if sent_after is not UNSET:
            field_dict["sent_after"] = sent_after
        if sent_before is not UNSET:
            field_dict["sent_before"] = sent_before
        if to is not UNSET:
            field_dict["to"] = to
        if from_ is not UNSET:
            field_dict["from"] = from_
        if subject is not UNSET:
            field_dict["subject"] = subject
        if status is not UNSET:
            field_dict["status"] = status
        if events is not UNSET:
            field_dict["events"] = events
        if clicks_count is not UNSET:
            field_dict["clicks_count"] = clicks_count
        if opens_count is not UNSET:
            field_dict["opens_count"] = opens_count
        if client_ip is not UNSET:
            field_dict["client_ip"] = client_ip
        if sending_ip is not UNSET:
            field_dict["sending_ip"] = sending_ip
        if email_service_provider_response is not UNSET:
            field_dict["email_service_provider_response"] = (
                email_service_provider_response
            )
        if email_service_provider is not UNSET:
            field_dict["email_service_provider"] = email_service_provider
        if recipient_mx is not UNSET:
            field_dict["recipient_mx"] = recipient_mx
        if category is not UNSET:
            field_dict["category"] = category
        if domain_id is not UNSET:
            field_dict["domain_id"] = domain_id
        if sending_stream is not UNSET:
            field_dict["sending_stream"] = sending_stream

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.filter_category import FilterCategory
        from ..models.filter_ci_contain_string import FilterCiContainString
        from ..models.filter_ci_equal_string import FilterCiEqualString
        from ..models.filter_clicks_count import FilterClicksCount
        from ..models.filter_contain_string import FilterContainString
        from ..models.filter_domain_id import FilterDomainId
        from ..models.filter_email_service_provider import FilterEmailServiceProvider
        from ..models.filter_empty_string import FilterEmptyString
        from ..models.filter_equal_string import FilterEqualString
        from ..models.filter_events import FilterEvents
        from ..models.filter_opens_count import FilterOpensCount
        from ..models.filter_sending_stream import FilterSendingStream
        from ..models.filter_status import FilterStatus

        d = dict(src_dict)
        _sent_after = d.pop("sent_after", UNSET)
        sent_after: datetime.datetime | Unset
        if isinstance(_sent_after, Unset):
            sent_after = UNSET
        else:
            sent_after = datetime.datetime.fromisoformat(_sent_after)

        _sent_before = d.pop("sent_before", UNSET)
        sent_before: datetime.datetime | Unset
        if isinstance(_sent_before, Unset):
            sent_before = UNSET
        else:
            sent_before = datetime.datetime.fromisoformat(_sent_before)

        def _parse_to(
            data: object,
        ) -> FilterCiContainString | FilterCiEqualString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_to_type_0 = FilterCiEqualString.from_dict(data)

                return componentsschemas_filter_to_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_to_type_1 = FilterCiContainString.from_dict(data)

            return componentsschemas_filter_to_type_1

        to = _parse_to(d.pop("to", UNSET))

        def _parse_from_(
            data: object,
        ) -> FilterCiContainString | FilterCiEqualString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_from_type_0 = FilterCiEqualString.from_dict(
                    data
                )

                return componentsschemas_filter_from_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_from_type_1 = FilterCiContainString.from_dict(data)

            return componentsschemas_filter_from_type_1

        from_ = _parse_from_(d.pop("from", UNSET))

        def _parse_subject(
            data: object,
        ) -> FilterCiContainString | FilterCiEqualString | FilterEmptyString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_subject_type_0 = FilterCiEqualString.from_dict(
                    data
                )

                return componentsschemas_filter_subject_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_subject_type_1 = (
                    FilterCiContainString.from_dict(data)
                )

                return componentsschemas_filter_subject_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_subject_type_2 = FilterEmptyString.from_dict(data)

            return componentsschemas_filter_subject_type_2

        subject = _parse_subject(d.pop("subject", UNSET))

        _status = d.pop("status", UNSET)
        status: FilterStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = FilterStatus.from_dict(_status)

        _events = d.pop("events", UNSET)
        events: FilterEvents | Unset
        if isinstance(_events, Unset):
            events = UNSET
        else:
            events = FilterEvents.from_dict(_events)

        _clicks_count = d.pop("clicks_count", UNSET)
        clicks_count: FilterClicksCount | Unset
        if isinstance(_clicks_count, Unset):
            clicks_count = UNSET
        else:
            clicks_count = FilterClicksCount.from_dict(_clicks_count)

        _opens_count = d.pop("opens_count", UNSET)
        opens_count: FilterOpensCount | Unset
        if isinstance(_opens_count, Unset):
            opens_count = UNSET
        else:
            opens_count = FilterOpensCount.from_dict(_opens_count)

        def _parse_client_ip(
            data: object,
        ) -> FilterContainString | FilterEqualString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_client_ip_type_0 = FilterEqualString.from_dict(
                    data
                )

                return componentsschemas_filter_client_ip_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_client_ip_type_1 = FilterContainString.from_dict(
                data
            )

            return componentsschemas_filter_client_ip_type_1

        client_ip = _parse_client_ip(d.pop("client_ip", UNSET))

        def _parse_sending_ip(
            data: object,
        ) -> FilterContainString | FilterEqualString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_sending_ip_type_0 = (
                    FilterEqualString.from_dict(data)
                )

                return componentsschemas_filter_sending_ip_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_sending_ip_type_1 = FilterContainString.from_dict(
                data
            )

            return componentsschemas_filter_sending_ip_type_1

        sending_ip = _parse_sending_ip(d.pop("sending_ip", UNSET))

        def _parse_email_service_provider_response(
            data: object,
        ) -> FilterCiContainString | FilterCiEqualString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_email_service_provider_response_type_0 = (
                    FilterCiEqualString.from_dict(data)
                )

                return componentsschemas_filter_email_service_provider_response_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_email_service_provider_response_type_1 = (
                FilterCiContainString.from_dict(data)
            )

            return componentsschemas_filter_email_service_provider_response_type_1

        email_service_provider_response = _parse_email_service_provider_response(
            d.pop("email_service_provider_response", UNSET)
        )

        _email_service_provider = d.pop("email_service_provider", UNSET)
        email_service_provider: FilterEmailServiceProvider | Unset
        if isinstance(_email_service_provider, Unset):
            email_service_provider = UNSET
        else:
            email_service_provider = FilterEmailServiceProvider.from_dict(
                _email_service_provider
            )

        def _parse_recipient_mx(
            data: object,
        ) -> FilterCiContainString | FilterCiEqualString | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_filter_recipient_mx_type_0 = (
                    FilterCiEqualString.from_dict(data)
                )

                return componentsschemas_filter_recipient_mx_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_filter_recipient_mx_type_1 = (
                FilterCiContainString.from_dict(data)
            )

            return componentsschemas_filter_recipient_mx_type_1

        recipient_mx = _parse_recipient_mx(d.pop("recipient_mx", UNSET))

        _category = d.pop("category", UNSET)
        category: FilterCategory | Unset
        if isinstance(_category, Unset):
            category = UNSET
        else:
            category = FilterCategory.from_dict(_category)

        _domain_id = d.pop("domain_id", UNSET)
        domain_id: FilterDomainId | Unset
        if isinstance(_domain_id, Unset):
            domain_id = UNSET
        else:
            domain_id = FilterDomainId.from_dict(_domain_id)

        _sending_stream = d.pop("sending_stream", UNSET)
        sending_stream: FilterSendingStream | Unset
        if isinstance(_sending_stream, Unset):
            sending_stream = UNSET
        else:
            sending_stream = FilterSendingStream.from_dict(_sending_stream)

        email_logs_list_filters = cls(
            sent_after=sent_after,
            sent_before=sent_before,
            to=to,
            from_=from_,
            subject=subject,
            status=status,
            events=events,
            clicks_count=clicks_count,
            opens_count=opens_count,
            client_ip=client_ip,
            sending_ip=sending_ip,
            email_service_provider_response=email_service_provider_response,
            email_service_provider=email_service_provider,
            recipient_mx=recipient_mx,
            category=category,
            domain_id=domain_id,
            sending_stream=sending_stream,
        )

        email_logs_list_filters.additional_properties = d
        return email_logs_list_filters

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
