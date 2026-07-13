from enum import Enum


class AttachmentContentDispositionType3Type1(str, Enum):
    ATTACHMENT = "attachment"
    INLINE = "inline"

    def __str__(self) -> str:
        return str(self.value)
