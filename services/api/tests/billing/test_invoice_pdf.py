"""Invoice PDF regressions. Written for steps 5.1/5.3; execution deferred by the owner."""
import io
import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from sqlalchemy import func, select

from app.billing.models import Invoice, Payment
from app.billing.pdf import render_invoice
from app.billing.schemas import InvoiceOut
from app.customers.models import Customer
from app.identity.models import Login
from app.identity.service import hash_password
from tests.billing.test_billing import admin_payment
from tests.directory_helpers import set_setting
from tests.test_api import auth


def issued(m):
    p = admin_payment(m)
    assert m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin).status_code == 200
    response = m.client.post(f"/v1/admin/payments/{p['id']}/invoice", headers=m.admin)
    assert response.status_code == 200, response.text
    return p, response.json()


def text_of(response):
    assert response.status_code == 200, response.text if response.status_code != 200 else ""
    assert response.content.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) >= 1
    return "\n".join(page.extract_text() for page in reader.pages)


def test_owner_opens_pdf_without_creating_a_second_invoice(money):
    m = money
    p, invoice = issued(m)
    endpoint = f"/v1/customer/payments/{p['id']}/invoice.pdf"
    for _ in range(2):
        response = m.client.get(endpoint, headers=m.customer)
        content = text_of(response)
        assert invoice["number"] in content and "Meera Rao" in content
        assert "11-Oct-2026" in content and "1,299.00" in content
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"] == f'inline; filename="{invoice["number"]}.pdf"'
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
    assert m.db.scalar(select(func.count()).select_from(Invoice)) == 1
    assert m.client.get(f"/v1/admin/payments/{p['id']}/invoice.pdf", headers=m.admin).status_code == 200


def test_pdf_does_not_issue_an_invoice_for_due_or_uninvoiced_received_payment(money):
    m = money
    p = admin_payment(m)
    url = f"/v1/customer/payments/{p['id']}/invoice.pdf"
    assert m.client.get(url, headers=m.customer).status_code == 404
    m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    response = m.client.get(url, headers=m.customer)
    assert response.status_code == 404 and response.json()["code"] == "no_invoice"
    assert m.db.scalar(select(func.count()).select_from(Invoice)) == 0


def test_invoice_pdf_checks_authentication_roles_and_customer_ownership(money):
    m = money
    p, _ = issued(m)
    original = m.db.get(Customer, m.customer_id)
    login = Login(role="customer", login_id="other-invoice@example.com", display_name="Other",
                  password_hash=hash_password("pw-other-invoice1"), active=True)
    m.db.add(login)
    m.db.flush()
    m.db.add(Customer(login_id=login.id, first_name="Other", last_name="Customer",
                      email=login.login_id, mobile="9876543219", society_id=original.society_id))
    m.db.commit()
    token = m.client.post("/v1/auth/login", json={
        "login_id": login.login_id, "password": "pw-other-invoice1",
    }).json()["access_token"]
    url = f"/v1/customer/payments/{p['id']}/invoice.pdf"
    assert m.client.get(url).status_code == 401
    assert m.client.get(url, headers=m.admin).status_code == 403
    assert m.client.get(url, headers=auth(token)).status_code == 404
    assert m.client.get(f"/v1/admin/payments/{p['id']}/invoice.pdf", headers=m.customer).status_code == 403
    assert m.client.get(f"/v1/customer/payments/{uuid.uuid4()}/invoice.pdf", headers=m.customer).status_code == 404


def test_pdf_preserves_issued_amount_names_and_supplier_details(money):
    m = money
    from app.billing.config import MoneySettings, get_money_settings
    m.client.app.dependency_overrides[get_money_settings] = lambda: MoneySettings(gst_configuration_mock=False)
    set_setting(m.db.get_bind(), "invoice.seller_name", "Original Supplier")
    set_setting(m.db.get_bind(), "invoice.seller_address", "Original address")
    set_setting(m.db.get_bind(), "invoice.seller_gstin", "29ABCDE1234F1Z5")
    p, _ = issued(m)
    set_setting(m.db.get_bind(), "invoice.seller_name", "Changed Supplier")
    customer = m.db.get(Customer, m.customer_id)
    customer.first_name = "Changed"
    payment = m.db.get(Payment, uuid.UUID(p["id"]))
    payment.amount_rupees = 2000
    m.db.commit()
    response = m.client.get(f"/v1/customer/payments/{p['id']}/invoice.pdf", headers=m.customer)
    text = text_of(response)
    assert "Original Supplier" in text and "Original address" in text
    assert "Changed Supplier" not in text and "Changed Rao" not in text
    assert "1,299.00" in text and "2,000.00" not in text
    assert "PREVIEW" not in text


def test_incomplete_supplier_settings_are_preview_only_and_blocked_outside_dev(money, monkeypatch):
    m = money
    p, _ = issued(m)
    endpoint = f"/v1/customer/payments/{p['id']}/invoice.pdf"
    assert "PREVIEW" in text_of(m.client.get(endpoint, headers=m.customer))
    monkeypatch.setattr("app.billing.service.get_settings", lambda: SimpleNamespace(environment="prod"))
    blocked = m.client.get(endpoint, headers=m.customer)
    assert blocked.status_code == 409 and blocked.json()["code"] == "invoice_settings_incomplete"


def test_legacy_invoice_supplier_details_are_not_silently_backfilled(money):
    m = money
    p, _ = issued(m)
    row = m.db.scalar(select(Invoice).where(Invoice.payment_id == uuid.UUID(p["id"])))
    row.seller_details = None
    m.db.commit()
    text = text_of(m.client.get(f"/v1/customer/payments/{p['id']}/invoice.pdf", headers=m.customer))
    assert "Legacy invoice" in text
    m.db.refresh(row)
    assert row.seller_details is None


@pytest.mark.parametrize("description", ["Exterior & Interior <premium>", "Long service " * 60])
def test_pdf_escapes_text_and_wraps_long_content(description):
    invoice = InvoiceOut(number="PRV102600000001", issued_on=date(2026, 10, 11),
        amount_rupees=1299, description=description, customer_name="José & Rao",
        vehicle="HR01ZZ1234", gst_included=True, seller_name="Priveo",
        seller_address="A long address " * 20, seller_gstin="29ABCDE1234F1Z5")
    content = render_invoice(invoice, preview=False)
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert invoice.number in text and "José & Rao" in text
    assert description.split()[0] in text
