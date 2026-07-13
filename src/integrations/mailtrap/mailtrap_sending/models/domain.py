from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.domain_compliance_status import DomainComplianceStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.domain_dns_records_item import DomainDnsRecordsItem
    from ..models.domain_permissions import DomainPermissions


T = TypeVar("T", bound="Domain")


@_attrs_define
class Domain:
    """
    Example:
        {'id': 435, 'domain_name': 'mailtrap.io', 'demo': False, 'compliance_status': 'compliant', 'dns_verified': True,
            'dns_verified_at': '2024-12-26T09:40:44.161Z', 'dns_records': [{'key': 'verification', 'domain':
            've6wza2rbpe60x7z.mailtrap.io', 'type': 'CNAME', 'value': 'smtp.mailtrap.live', 'status': 'pass', 'name':
            've6wza2rbpe60x7z'}, {'key': 'spf', 'domain': 'mailtrap.io', 'type': 'TXT', 'value': 'v=spf1
            include:_spf.smtp.mailtrap.live ~all', 'status': 'pass', 'name': ''}, {'key': 'dkim1', 'domain':
            'rwmt1._domainkey.mailtrap.io', 'type': 'CNAME', 'value': 'rwmt1.dkim.smtp.mailtrap.live', 'status': 'pass',
            'name': 'rwmt1._domainkey'}, {'key': 'dkim2', 'domain': 'rwmt2._domainkey.mailtrap.io', 'type': 'CNAME',
            'value': 'rwmt2.dkim.smtp.mailtrap.live', 'status': 'pass', 'name': 'rwmt2._domainkey'}, {'key': 'dmarc',
            'domain': '_dmarc.mailtrap.io', 'type': 'TXT', 'value': 'v=DMARC1; p=none; rua=mailto:dmarc@smtp.mailtrap.live;
            ruf=mailto:dmarc@smtp.mailtrap.live; rf=afrf; pct=100', 'status': 'pass', 'name': '_dmarc'}, {'key':
            'link_verification', 'domain': 'mt-link.mailtrap.io', 'type': 'CNAME', 'value': 't.mailtrap.live', 'status':
            'pass', 'name': 'mt-link'}], 'open_tracking_enabled': True, 'click_tracking_enabled': True,
            'auto_unsubscribe_link_enabled': True, 'custom_domain_tracking_enabled': True, 'health_alerts_enabled': True,
            'critical_alerts_enabled': True, 'alert_recipient_email': 'john.doe@mailtrap.io', 'permissions': {'can_read':
            True, 'can_update': True, 'can_destroy': True}}

    Attributes:
        id (int | Unset):
        domain_name (str | Unset):
        demo (bool | Unset):
        compliance_status (DomainComplianceStatus | Unset): Indicates the compliance verification status of the domain.
            The domain must reach `compliant` status before you can send emails
            in production.

            - `demo` - A demo domain provided by Mailtrap. Can only send emails to the account owner.
            - `demo_exhausted` - A demo domain that has used up its sending allowance. Cannot send emails.
            - `unverified_dns` - Domain DNS records have not been verified yet. Open your domain on the
            [Domains](https://mailtrap.io/domains) page and follow the [Sending Domain
            Setup](https://docs.mailtrap.io/email-api-smtp/setup/sending-domain) guide.
            - `missing_company_info` - Account is missing required company information. Go to [Company
            Information](https://mailtrap.io/settings/account?current_tab=company_information) and fill in the required
            details.
            - `under_review` - Domain is undergoing automatic compliance review. No action needed — typically completes
            within 2 minutes.
            - `awaiting_questionnaire` - Automatic review required additional information. Open your domain on the
            [Domains](https://mailtrap.io/domains) page and fill in the compliance questionnaire.
            - `awaiting_card_verification` - Compliance questionnaire was submitted but credit card identity verification is
            still needed. Open your domain on the [Domains](https://mailtrap.io/domains) page and enter card details. The
            charged amount is refunded immediately and the card is not stored.
            - `non_compliant` - Domain did not pass compliance checks. Sending is not allowed. Contact [Mailtrap
            Support](mailto:support@mailtrap.io) for details and next steps.
            - `compliant` - Domain has passed all compliance checks and is ready to send emails.
            - `suspended` - Domain sending has been suspended. Contact [Mailtrap Support](mailto:support@mailtrap.io) to
            resolve the issue.
        dns_verified (bool | Unset):
        dns_verified_at (None | str | Unset):  Example: 2024-12-26T09:40:44.161Z.
        dns_records (list[DomainDnsRecordsItem] | Unset):
        open_tracking_enabled (bool | Unset):
        click_tracking_enabled (bool | Unset):
        auto_unsubscribe_link_enabled (bool | Unset):
        custom_domain_tracking_enabled (bool | Unset):
        health_alerts_enabled (bool | Unset):
        critical_alerts_enabled (bool | Unset):
        alert_recipient_email (None | str | Unset):
        permissions (DomainPermissions | Unset):
    """

    id: int | Unset = UNSET
    domain_name: str | Unset = UNSET
    demo: bool | Unset = UNSET
    compliance_status: DomainComplianceStatus | Unset = UNSET
    dns_verified: bool | Unset = UNSET
    dns_verified_at: None | str | Unset = UNSET
    dns_records: list[DomainDnsRecordsItem] | Unset = UNSET
    open_tracking_enabled: bool | Unset = UNSET
    click_tracking_enabled: bool | Unset = UNSET
    auto_unsubscribe_link_enabled: bool | Unset = UNSET
    custom_domain_tracking_enabled: bool | Unset = UNSET
    health_alerts_enabled: bool | Unset = UNSET
    critical_alerts_enabled: bool | Unset = UNSET
    alert_recipient_email: None | str | Unset = UNSET
    permissions: DomainPermissions | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        domain_name = self.domain_name

        demo = self.demo

        compliance_status: str | Unset = UNSET
        if not isinstance(self.compliance_status, Unset):
            compliance_status = self.compliance_status.value

        dns_verified = self.dns_verified

        dns_verified_at: None | str | Unset
        if isinstance(self.dns_verified_at, Unset):
            dns_verified_at = UNSET
        else:
            dns_verified_at = self.dns_verified_at

        dns_records: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.dns_records, Unset):
            dns_records = []
            for dns_records_item_data in self.dns_records:
                dns_records_item = dns_records_item_data.to_dict()
                dns_records.append(dns_records_item)

        open_tracking_enabled = self.open_tracking_enabled

        click_tracking_enabled = self.click_tracking_enabled

        auto_unsubscribe_link_enabled = self.auto_unsubscribe_link_enabled

        custom_domain_tracking_enabled = self.custom_domain_tracking_enabled

        health_alerts_enabled = self.health_alerts_enabled

        critical_alerts_enabled = self.critical_alerts_enabled

        alert_recipient_email: None | str | Unset
        if isinstance(self.alert_recipient_email, Unset):
            alert_recipient_email = UNSET
        else:
            alert_recipient_email = self.alert_recipient_email

        permissions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.permissions, Unset):
            permissions = self.permissions.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if domain_name is not UNSET:
            field_dict["domain_name"] = domain_name
        if demo is not UNSET:
            field_dict["demo"] = demo
        if compliance_status is not UNSET:
            field_dict["compliance_status"] = compliance_status
        if dns_verified is not UNSET:
            field_dict["dns_verified"] = dns_verified
        if dns_verified_at is not UNSET:
            field_dict["dns_verified_at"] = dns_verified_at
        if dns_records is not UNSET:
            field_dict["dns_records"] = dns_records
        if open_tracking_enabled is not UNSET:
            field_dict["open_tracking_enabled"] = open_tracking_enabled
        if click_tracking_enabled is not UNSET:
            field_dict["click_tracking_enabled"] = click_tracking_enabled
        if auto_unsubscribe_link_enabled is not UNSET:
            field_dict["auto_unsubscribe_link_enabled"] = auto_unsubscribe_link_enabled
        if custom_domain_tracking_enabled is not UNSET:
            field_dict["custom_domain_tracking_enabled"] = (
                custom_domain_tracking_enabled
            )
        if health_alerts_enabled is not UNSET:
            field_dict["health_alerts_enabled"] = health_alerts_enabled
        if critical_alerts_enabled is not UNSET:
            field_dict["critical_alerts_enabled"] = critical_alerts_enabled
        if alert_recipient_email is not UNSET:
            field_dict["alert_recipient_email"] = alert_recipient_email
        if permissions is not UNSET:
            field_dict["permissions"] = permissions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.domain_dns_records_item import DomainDnsRecordsItem
        from ..models.domain_permissions import DomainPermissions

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        domain_name = d.pop("domain_name", UNSET)

        demo = d.pop("demo", UNSET)

        _compliance_status = d.pop("compliance_status", UNSET)
        compliance_status: DomainComplianceStatus | Unset
        if isinstance(_compliance_status, Unset):
            compliance_status = UNSET
        else:
            compliance_status = DomainComplianceStatus(_compliance_status)

        dns_verified = d.pop("dns_verified", UNSET)

        def _parse_dns_verified_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        dns_verified_at = _parse_dns_verified_at(d.pop("dns_verified_at", UNSET))

        _dns_records = d.pop("dns_records", UNSET)
        dns_records: list[DomainDnsRecordsItem] | Unset = UNSET
        if _dns_records is not UNSET:
            dns_records = []
            for dns_records_item_data in _dns_records:
                dns_records_item = DomainDnsRecordsItem.from_dict(dns_records_item_data)

                dns_records.append(dns_records_item)

        open_tracking_enabled = d.pop("open_tracking_enabled", UNSET)

        click_tracking_enabled = d.pop("click_tracking_enabled", UNSET)

        auto_unsubscribe_link_enabled = d.pop("auto_unsubscribe_link_enabled", UNSET)

        custom_domain_tracking_enabled = d.pop("custom_domain_tracking_enabled", UNSET)

        health_alerts_enabled = d.pop("health_alerts_enabled", UNSET)

        critical_alerts_enabled = d.pop("critical_alerts_enabled", UNSET)

        def _parse_alert_recipient_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        alert_recipient_email = _parse_alert_recipient_email(
            d.pop("alert_recipient_email", UNSET)
        )

        _permissions = d.pop("permissions", UNSET)
        permissions: DomainPermissions | Unset
        if isinstance(_permissions, Unset):
            permissions = UNSET
        else:
            permissions = DomainPermissions.from_dict(_permissions)

        domain = cls(
            id=id,
            domain_name=domain_name,
            demo=demo,
            compliance_status=compliance_status,
            dns_verified=dns_verified,
            dns_verified_at=dns_verified_at,
            dns_records=dns_records,
            open_tracking_enabled=open_tracking_enabled,
            click_tracking_enabled=click_tracking_enabled,
            auto_unsubscribe_link_enabled=auto_unsubscribe_link_enabled,
            custom_domain_tracking_enabled=custom_domain_tracking_enabled,
            health_alerts_enabled=health_alerts_enabled,
            critical_alerts_enabled=critical_alerts_enabled,
            alert_recipient_email=alert_recipient_email,
            permissions=permissions,
        )

        domain.additional_properties = d
        return domain

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
