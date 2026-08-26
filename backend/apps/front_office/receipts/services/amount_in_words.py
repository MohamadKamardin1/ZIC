"""Front Office Receipts — amount in words (Prompt 8).

Converts a decimal receipt amount into an English-language written form used on
the printable receipt, e.g. ``100000.00 TZS`` -> "One Hundred Thousand Tanzanian
Shillings Only". The currency is parameterized; the unit/subunit names come from
a small reference map with a sensible default for unknown codes.
"""

from decimal import ROUND_HALF_UP, Decimal

_ONES = (
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
)

_TENS = (
    "",
    "",
    "Twenty",
    "Thirty",
    "Forty",
    "Fifty",
    "Sixty",
    "Seventy",
    "Eighty",
    "Ninety",
)

_SCALES = ("", "Thousand", "Million", "Billion", "Trillion", "Quadrillion")

CURRENCY_UNITS = {
    "TZS": ("Tanzanian Shillings", "Senti"),
    "USD": ("United States Dollars", "Cents"),
    "EUR": ("Euros", "Cents"),
    "GBP": ("Pounds Sterling", "Pence"),
    "KES": ("Kenyan Shillings", "Cents"),
    "UGX": ("Ugandan Shillings", "Cents"),
    "ZAR": ("South African Rand", "Cents"),
    "AED": ("UAE Dirhams", "Fils"),
    "INR": ("Indian Rupees", "Paise"),
}


def _three_words(number):
    """Words for an integer 0..999."""
    words = []
    hundreds = number // 100
    remainder = number % 100
    if hundreds:
        words.append(_ONES[hundreds])
        words.append("Hundred")
    if remainder:
        if hundreds:
            words.append("And")
        if remainder < 20:
            words.append(_ONES[remainder])
        else:
            words.append(_TENS[remainder // 10])
            if remainder % 10:
                words.append(_ONES[remainder % 10])
    return words


def integer_in_words(value):
    """Words for a non-negative integer (US short scale), or "Zero"."""
    value = abs(int(value))
    if value == 0:
        return "Zero"
    groups = []
    while value:
        groups.append(value % 1000)
        value //= 1000
    parts = []
    for index, group in enumerate(groups):
        if not group:
            continue
        group_words = _three_words(group)
        if index:
            group_words = group_words + [_SCALES[index]]
        parts.append(" ".join(group_words))
    return " ".join(reversed(parts))


def amount_in_words(amount, currency="TZS"):
    """Written form of a receipt amount in the receipt currency.

    Rounds to two decimal places. Whole amounts read
    "<integer words> <currency unit> Only"; fractional amounts append
    "And <subunit words> <currency subunit>".
    """
    value = Decimal(str(amount or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    major = int(value)
    minor = int((value - Decimal(major)) * 100)

    unit, subunit = CURRENCY_UNITS.get((currency or "").strip().upper(), ((currency or "").strip().upper() or "Units", "Cents"))

    words = [integer_in_words(abs(major)), unit]
    if minor:
        words += ["And", integer_in_words(minor), subunit]
    words.append("Only")
    return " ".join(words)
