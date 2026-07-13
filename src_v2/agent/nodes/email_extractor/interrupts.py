from typing import Literal

from pydantic import BaseModel


class WaitForHotelReply(BaseModel):
    """Interrupt to wait for a reply from the hotel before proceeding with the workflow."""

    type: Literal["wait_for_hotel_reply"] = "wait_for_hotel_reply"
