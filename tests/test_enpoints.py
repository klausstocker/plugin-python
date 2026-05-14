from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
BASE_PATH = "/pluginpython"


def test_get_ping_returns_plain_text():
    response = client.get(f"{BASE_PATH}/ping")

    assert response.status_code == 200
    assert response.text == "pong"


def test_get_info_returns_service_info_dto():
    response = client.get(f"{BASE_PATH}/open/info")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "pluginpython"
    assert body["servicename"] == "pluginpython"


def test_post_configurationinfo_returns_configuration_dto_shape():
    payload = {
        "typ": "PIG",
        "name": "PluginVomTester",
        "config": "",
        "configurationID": "cfg-1",
        "timeout": 300,
    }

    response = client.post(f"{BASE_PATH}/open/configurationinfo", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["configurationID"] == "cfg-1"
    assert body["configurationMode"] == 2
    assert body["useQuestion"] is True


def test_post_generalinfo_returns_matching_typ():
    response = client.post(f"{BASE_PATH}/open/generalinfo", json="PIG")

    assert response.status_code == 200
    body = response.json()
    assert body["typ"] == "PIG"
