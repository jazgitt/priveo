"""The customer loaders run the daily payments job after saving, so statuses exist at once."""
import pytest

from app.billing import service
from scripts import import_customers, load_monthly_customers


@pytest.mark.parametrize("script", [import_customers, load_monthly_customers])
def test_loader_runs_the_payments_job_after_loading(script, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(service, "generate_due_payments", lambda now: calls.append("generate") or 3)
    monkeypatch.setattr(service, "mark_overdue_and_inactive",
                        lambda now: calls.append("overdue") or service.OverdueReport())
    script.run_payments_job()
    assert calls == ["generate", "overdue"]
    assert "3 cycle payments made" in capsys.readouterr().out
