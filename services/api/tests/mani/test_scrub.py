"""The scrubber: the 13 cases from the 30-Oct source audit, plus idempotence, speed and a
final sweep. Plain pytest, no database."""
import copy
import time

from app.mani.scrub import PatternScrubber

S = PatternScrubber()


def scrub(text: str) -> str:
    return S.scrub(text).text


def test_admin_login_literal_replaced_everywhere():
    assert scrub("log in as priveopapa today") == "log in as [redacted:admin-login] today"
    assert scrub('{"login_id": "priveopapa"}') == '{"login_id": "[redacted:admin-login]"}'
    assert "PriveoPapa" not in scrub("PriveoPapa")
    assert "priveopapa" not in scrub("user priveopapa/pw")
    assert scrub("priveopapaX stays") == "priveopapaX stays"


def test_extra_literals():
    s = PatternScrubber(extra_literals=["owner42"])
    assert s.scrub("owner42 and priveopapa").text == "[redacted:admin-login] and [redacted:admin-login]"
    twice = PatternScrubber(extra_literals=["login"])
    once = twice.scrub("login x").text
    assert once == "[redacted:admin-login] x"
    assert twice.scrub(once).text == once


def test_password_keys_json_and_kwargs_keep_key_names():
    assert scrub('{"password": "hunter2", "name": "Asha"}') == '{"password": "[redacted:secret]", "name": "Asha"}'
    assert scrub("login(user, password='hunter2')") == "login(user, password='[redacted:secret]')"
    assert scrub("ADMIN_PASSWORD=hunter2") == "ADMIN_PASSWORD=[redacted:secret]"
    assert scrub("secret: abc123XYZ") == "secret: [redacted:secret]"
    assert scrub("MOCK_EMAIL_CODE=123456") == "MOCK_EMAIL_CODE=[redacted:secret]"
    assert scrub("{'api_key': 'abc', 'pw': 'zzz'}") == "{'api_key': '[redacted:secret]', 'pw': '[redacted:secret]'}"
    # A key name with no value stays.
    for kept in ("the password_hash column", "set password,\nnext", "password:\nnext line", "max_tokens: 4096"):
        assert scrub(kept) == kept


def test_crew_password_shapes():
    assert scrub("Password: Raj1111$") == "Password: [redacted:secret]"
    assert scrub("crew Raj password=Raj1111$ ok") == "crew Raj password=[redacted:secret] ok"
    assert "Raj1111$" not in scrub("handed over: Raj1111$")


def test_provider_token_prefixes():
    samples = [
        "vercel_blob_rw_AbCd1234EfGh_5678IjKlMnOp",
        "re_A1b2C3d4_E5f6G7h8I9j0K1l2M3n4",
        "sk-or-v1-0123456789abcdef0123456789",
        "AKIAABCDEFGHIJKLMNOP",
        "ghp_0123456789abcdefghij0123456789ABCD",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fw",
    ]
    for tok in samples:
        out = scrub(f"value is {tok} here")
        assert tok not in out and "[redacted:token]" in out, tok
    out = scrub("Authorization: Bearer abcdef0123456789abcdef")
    assert out == "Authorization: Bearer [redacted:token]"
    pem = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg\nabc\n-----END PRIVATE KEY-----"
    assert scrub(f"key:\n{pem}\nafter") == "key:\n[redacted:private-key]\nafter"
    assert scrub("-----BEGIN RSA PRIVATE KEY-----\nunterminated") == "[redacted:private-key]"
    # Plain words that only look similar stay.
    assert scrub("re_search and sk-learn") == "re_search and sk-learn"


def test_database_url_credentials():
    assert scrub("postgres://app_user:p4ss@db.example.com:5432/priveo") == (
        "postgres://[redacted:db-credentials]@db.example.com:5432/priveo")
    assert scrub("DATABASE_URL=postgresql+psycopg://u:p@host/db").endswith("://[redacted:db-credentials]@host/db")
    assert scrub("use postgresql://... for the URL") == "use postgresql://... for the URL"
    assert scrub("https://example.com/path") == "https://example.com/path"


def test_emails():
    out = scrub("Mail Asha@Example.COM or asha.k+x@example.com, ops@priveo.test.")
    assert out == "Mail [redacted:email] or [redacted:email], [redacted:email]."
    assert scrub("not an email: @handle and a@b") == "not an email: @handle and a@b"


def test_mobiles_in_their_formats():
    for number in ("9000000102", "+919000000102", "+91 90000 00102", "09000000102", "90000 00102",
                   "90000-00102", "+91-9000000102", "900-000-0102"):
        assert scrub(f"call {number} now") == "call [redacted:mobile] now", number
    assert scrub("9000000102/9000000103") == "[redacted:mobile]/[redacted:mobile]"
    assert scrub("phone: 9000000102,") == "phone: [redacted:mobile],"


def test_crew_row_keeps_number_but_customer_row_loses_it():
    assert scrub("| Crew | 9000000002 | Crew home |") == "| Crew | 9000000002 | Crew home |"
    assert scrub("| Customer | 9000000002 | Customer home |") == "| Customer | [redacted:mobile] | Customer home |"
    both = scrub("| Crew | 9000000002 |\n| Customer | 9000000003 |")
    assert both == "| Crew | 9000000002 |\n| Customer | [redacted:mobile] |"


def test_address_fields_redacted_names_kept():
    text = ('{"name": "Asha Rao", "society": "Palm Meadows", "address_line1": "12 MG Road", '
            '"address_line2": "Block C", "flat": "B-204", "tower": "3", "parking_basement": "B2"}')
    out = scrub(text)
    for gone in ("12 MG Road", "Block C", "B-204", "B2"):
        assert gone not in out
    assert "Asha Rao" in out and "Palm Meadows" in out
    assert scrub("Address: 12 MG Road, Pune 411001\nNext") == "Address: [redacted:address]\nNext"
    assert scrub("address=null, name=x") == "address=null, name=x"


def test_name_mobile_email_line_keeps_name_only():
    out = scrub("Asha Rao 9000000102 asha@example.com order_id: 9876543210 ts=1761800000")
    assert out == "Asha Rao [redacted:mobile] [redacted:email] order_id: 9876543210 ts=1761800000"
    assert scrub('"invoice": "9123456780"') == '"invoice": "9123456780"'
    assert scrub("amount 12000 on 30-Oct-26 at 1761800000123") == "amount 12000 on 30-Oct-26 at 1761800000123"


def test_helplines_kept():
    line = "Helpline +910000000000 or +911234567890"
    assert scrub(line) == line


def test_password_hash_values():
    assert scrub("password_hash=$2b$12$abcdefghijklmnopqrstuv") == "password_hash=[redacted:secret]"
    assert scrub('"password_hash": "$2b$12$abc"') == '"password_hash": "[redacted:secret]"'
    assert scrub("password_hash = '$2b$12$abc'") == "password_hash = '[redacted:secret]'"


def test_scrub_data_nested_tool_result():
    data = {
        "customer": {"name": "Asha Rao", "mobile": "9000000102", "email": "asha@example.com",
                     "address_line1": "12 MG Road", "society": "Palm Meadows", "order_id": "9876543210"},
        "crew": [{"name": "Raj", "mobile": "9000000002", "password_hash": "$2b$x"}],
        "other": {"role": "crew", "name": "Sam", "phone": "9000000003", "note": "call 9000000003"},
        "admin": {"role": "admin", "login_id": "priveopapa", "phone": "9000000004", "email": "a@b.com"},
        "helpline": {"phone": "+911234567890"},
        "count": 3, "ok": True, "none": None, "pair": ("a@b.com", 5),
    }
    original = copy.deepcopy(data)
    out = S.scrub_data(data)
    assert data == original  # not mutated
    c = out["customer"]
    assert c["name"] == "Asha Rao" and c["society"] == "Palm Meadows" and c["order_id"] == "9876543210"
    assert c["mobile"] == "[redacted:mobile]" and c["email"] == "[redacted:email]"
    assert c["address_line1"] == "[redacted:address]"
    assert out["crew"][0] == {"name": "Raj", "mobile": "9000000002", "password_hash": "[redacted:secret]"}
    assert out["other"]["phone"] == "9000000003" and out["other"]["note"] == "call 9000000003"
    assert out["admin"] == {"role": "admin", "login_id": "[redacted:admin-login]",
                            "phone": "[redacted:mobile]", "email": "[redacted:email]"}
    assert out["helpline"]["phone"] == "+911234567890"
    assert out["count"] == 3 and out["ok"] is True and out["none"] is None
    assert out["pair"] == ("[redacted:email]", 5)
    assert set(out) == set(data)  # keys kept


def test_scrub_data_secret_keys_replace_any_type():
    out = S.scrub_data({"password": 12345, "tokens": [1, 2], "secret": {"a": 1}, "api_key": ["x"]})
    assert out == {"password": "[redacted:secret]", "tokens": [1, 2], "secret": "[redacted:secret]",
                   "api_key": "[redacted:secret]"}


def test_idempotent():
    doc = _planted_doc()
    once = S.scrub(doc).text
    twice = S.scrub(once)
    assert twice.text == once and twice.redactions == {}
    data = {"a": [{"email": "x@y.com", "note": "Address: 1 Road"}]}
    assert S.scrub_data(S.scrub_data(data)) == S.scrub_data(data)


def test_redaction_counts():
    res = S.scrub("a@b.com c@d.com 9000000102 password=hunter2 priveopapa")
    assert res.redactions == {"email": 2, "mobile": 1, "secret": 1, "admin-login": 1}
    assert S.scrub("nothing here").redactions == {}


def test_odd_input_never_raises():
    for odd in ("", "\x00\xff", "\n" * 5, "é" * 100, None, 12, b"bytes"):
        S.scrub(odd)  # type: ignore[arg-type]
    for odd in (None, 1, 2.5, object(), [], {}, {1: "a@b.com"}, [[[]]]):
        S.scrub_data(odd)
    deep: list = []
    node = deep
    for _ in range(500):
        nxt: list = []
        node.append(nxt)
        node = nxt
    S.scrub_data(deep)


def test_performance_on_large_and_hostile_input():
    big = "Asha Rao paid 1200 for order 9876543210; mail asha@example.com; call 9000000102.\n" * 12000
    assert len(big) > 900_000
    hostile = ["a" * 1_000_000, "password" * 125_000, "a." * 500_000, "9" * 1_000_000, "x@" * 500_000,
               "://" + "u" * 1_000_000, "-----BEGIN PRIVATE KEY-----" * 30_000, "address:" * 125_000,
               "\"" + "password: \"" * 100_000, "0" * 500_000 + " " + "1 " * 100_000]
    for text in [big, *hostile]:
        start = time.perf_counter()
        S.scrub(text)
        assert time.perf_counter() - start < 2.0, text[:30]


def _planted_doc() -> str:
    return "\n".join([
        "# Customer file for Asha Rao, Palm Meadows",
        "Contact: asha.rao@Example.com, mobile +91 98765 43210, alt 9000000102/9000000103",
        "Address: Flat B-204, Tower 3, Palm Meadows, 12 MG Road",
        '{"address_line1": "12 MG Road", "address_line2": "Near Park", "parking_basement": "B2"}',
        "| Crew | Raj | 9000000002 | Crew home |",
        "Admin login priveopapa with ADMIN_PASSWORD=Sup3rSecret!",
        "Crew password for Raj: Raj1111$",
        "DATABASE_URL=postgres://dbuser:dbpass99@db.example.com/priveo",
        "RESEND=re_Ab12Cd34_Ef56Gh78Ij90Kl12Mn34 BLOB=vercel_blob_rw_Zz99Yy88Xx77_Ww66Vv55",
        "OPENROUTER=sk-or-v1-abcdef0123456789abcdef AWS=AKIAIOSFODNN7EXAMPLE GH=ghp_abcdefghij0123456789ABCDEFGH",
        "Authorization: Bearer abcdefghijklmnop0123456789",
        "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r",
        "MOCK_EMAIL_CODE=424242",
        '"password_hash": "$2b$12$KIXQJ9v1dummyhashvalue", "token": "tok_live_abc123"',
        "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----",
    ])


def test_final_sweep_no_planted_value_survives():
    out = scrub(_planted_doc())
    planted = ["asha.rao@Example.com", "98765 43210", "9000000102", "9000000103", "B-204", "12 MG Road",
               "Near Park", "priveopapa", "Sup3rSecret!", "Raj1111$", "dbuser", "dbpass99",
               "re_Ab12Cd34", "vercel_blob_rw_Zz99", "sk-or-v1-abcdef", "AKIAIOSFODNN7EXAMPLE",
               "ghp_abcdefghij", "abcdefghijklmnop0123456789", "eyJhbGci", "424242", "KIXQJ9v1dummy",
               "tok_live_abc123", "MIIEvgIBAD"]
    for value in planted:
        assert value not in out, value
    # What is kept.
    for kept in ("Asha Rao", "Palm Meadows", "Raj", "9000000002", "ADMIN_PASSWORD", "DATABASE_URL",
                 "db.example.com", "password_hash"):
        assert kept in out, kept


def test_a_type_annotation_after_a_token_name_is_not_a_secret():
    text = "access_token_minutes: int = 15\n    refresh_token_days: float = 30"
    assert PatternScrubber().scrub(text).text == text
    assert "[redacted:secret]" in PatternScrubber().scrub("token: abcdef123456").text
