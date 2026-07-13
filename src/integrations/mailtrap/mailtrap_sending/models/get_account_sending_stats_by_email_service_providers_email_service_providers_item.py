from enum import Enum


class GetAccountSendingStatsByEmailServiceProvidersEmailServiceProvidersItem(str, Enum):
    AMAZON_SES_SIMPLE_EMAIL_SERVICE = "Amazon SES (Simple Email Service)"
    BARRACUDA_EMAIL_PROTECTION = "Barracuda Email Protection"
    CISCO_EMAIL_PROTECTION = "Cisco Email Protection"
    COMCAST = "Comcast"
    FASTMAIL = "FastMail"
    GMX_NET = "GMX.net"
    GODADDY = "GoDaddy"
    GOOGLE = "Google"
    GOOGLE_WORKSPACE = "Google Workspace"
    HEY = "Hey"
    ICLOUD = "iCloud"
    LINODE_HOSTED = "Linode hosted"
    MIMECAST_EMAIL_PROTECTION = "Mimecast Email Protection"
    NAVER = "Naver"
    OFFICE_365 = "Office 365"
    OUTLOOK = "Outlook"
    OVH_HOSTED = "OVH hosted"
    PROOFPOINT_EMAIL_PROTECTION = "Proofpoint Email Protection"
    PROTONMAIL = "ProtonMail"
    RACKSPACE = "Rackspace"
    SEZNAM = "Seznam"
    SPECTRUM = "Spectrum"
    SYMANTEC_EMAIL_PROTECTION = "Symantec Email Protection"
    YAHOO = "Yahoo"
    YANDEX = "Yandex"
    ZOHO_EMAIL = "Zoho Email"

    def __str__(self) -> str:
        return str(self.value)
