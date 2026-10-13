from sqlalchemy import select
from app.billing.config import MoneySettings
from app.billing.models import Invoice
from app.billing.service import BillingService
from app.billing.tax import included_gst
from tests.billing.test_invoice_pdf import issued


def test_inclusive_18_percent_rounds_in_paise_and_balances():
    assert included_gst(118, 18, 'CGST_SGST') == {
        'rate_percent': 18, 'mode': 'CGST_SGST', 'total_paise': 11800, 'taxable_paise': 10000,
        'gst_paise': 1800, 'cgst_paise': 900, 'sgst_paise': 900, 'igst_paise': 0}
    tax = included_gst(999, 18, 'CGST_SGST')
    assert tax['taxable_paise'] + tax['cgst_paise'] + tax['sgst_paise'] == 99900
    assert included_gst(118, 18, 'IGST')['igst_paise'] == 1800


def test_issued_tax_remains_immutable_when_configuration_changes(money):
    m = money
    payment, invoice = issued(m)
    assert invoice['tax_details']['rate_percent'] == 18
    service = BillingService(m.db, m.clock, MoneySettings(gst_rate_percent=5, gst_mode='IGST'))
    saved = service.issue_invoice(payment['id'], m.db.scalar(select(Invoice)).issued_by)
    assert saved.tax_details == invoice['tax_details']
