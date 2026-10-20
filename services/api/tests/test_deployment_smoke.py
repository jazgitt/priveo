"""Keep the deployment smoke journey aligned with real application routes."""
from scripts import smoke_test
from tests.conftest import PASSWORDS


def test_deployment_smoke_against_api(client, monkeypatch, capsys):
    monkeypatch.setattr(smoke_test.sys, "argv", ["smoke_test.py", "https://test.invalid"])
    for role, _, env in smoke_test.LOGINS:
        monkeypatch.setenv(env, PASSWORDS[role])

    paths = []

    def call(base, path, body=None, token=None):
        paths.append(path)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = (client.post(path, json=body, headers=headers) if body is not None
                    else client.get(path, headers=headers))
        return response.status_code, response.json()

    monkeypatch.setattr(smoke_test, "call", call)
    smoke_test.main()

    assert "/v1/crew/visits" in paths
    assert "/v1/crew/home" not in paths
    assert "ok   crew visits response" in capsys.readouterr().out
