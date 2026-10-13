"""GST-inclusive arithmetic in paise; rates/mode come from configuration."""
from decimal import Decimal, ROUND_HALF_UP


def included_gst(amount_rupees: int, rate_percent: int, mode: str) -> dict:
    if not 0 <= rate_percent <= 100 or mode not in ("CGST_SGST", "IGST"):
        raise ValueError("Invalid GST configuration")
    total = amount_rupees * 100
    taxable = int((Decimal(total) * 100 / (100 + rate_percent)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    gst = total - taxable
    central = (gst + 1) // 2 if mode == "CGST_SGST" else 0
    return {"rate_percent": rate_percent, "mode": mode, "total_paise": total,
            "taxable_paise": taxable, "gst_paise": gst, "cgst_paise": central,
            "sgst_paise": gst - central if mode == "CGST_SGST" else 0,
            "igst_paise": gst if mode == "IGST" else 0}
