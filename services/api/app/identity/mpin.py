"""The customer's MPIN: 6 digits. The admin gives every customer the same kind
of first MPIN, the last 6 digits of their mobile number, and the customer must
change it at the first sign-in."""
import re

MPIN_LENGTH = 6


def default_mpin(mobile: str) -> str:
    """The MPIN a customer starts with: the last 6 digits of the mobile number."""
    return mobile[-MPIN_LENGTH:]


def mpin_problem(mpin: str, mobile: str | None = None) -> str | None:
    """What is wrong with a new MPIN, if anything."""
    if not re.fullmatch(rf"\d{{{MPIN_LENGTH}}}", mpin):
        return f"Use exactly {MPIN_LENGTH} digits."
    if mobile and mpin == default_mpin(mobile):
        return "Choose an MPIN that is different from the one you were given."
    return None
