"""
states.py - ConversationHandler state constants
"""

from enum import IntEnum, auto


class UserStates(IntEnum):
    # Browsing
    BROWSING_CATEGORIES = auto()
    SELECTING_QUANTITY  = auto()
    CUSTOM_QUANTITY     = auto()
    AWAITING_PAYMENT    = auto()
    UPLOADING_SS        = auto()     # payment screenshot

class AdminStates(IntEnum):
    # Category management
    ADD_CATEGORY_NAME   = auto()
    ADD_CATEGORY_PRICE  = auto()
    EDIT_CATEGORY_PICK  = auto()
    EDIT_CATEGORY_NAME  = auto()
    EDIT_CATEGORY_PRICE = auto()
    DELETE_CATEGORY_PICK= auto()

    # Stock management
    ADD_STOCK_PICK_CAT  = auto()
    ADD_STOCK_ITEMS     = auto()

    # Pricing
    SET_PRICE_PICK_CAT  = auto()
    SET_PRICE_VALUE     = auto()

    # QR / UPI
    UPLOAD_QR           = auto()
    SET_UPI_ID          = auto()

    # Broadcast
    BROADCAST_MSG       = auto()

    # Manual stock adjust
    MANUAL_STOCK_PICK   = auto()
    MANUAL_STOCK_DELTA  = auto()

    # Reject reason
    REJECT_REASON       = auto()

    # Ban
    BAN_USER_ID         = auto()
    UNBAN_USER_ID       = auto()
