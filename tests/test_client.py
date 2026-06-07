import pytest
from pyzello.client import ZelloClient

def test_client_initialization():
    config = {
        "auth_mode": "development",
        "auth_token": "dummy_token",
        "zello_username": "tester",
        "zello_channels": ["TestChannel"]
    }
    client = ZelloClient(api_config=config)
    assert client.api_config["auth_mode"] == "development"
    assert client.target_channels == ["TestChannel"]
    assert client.is_connected is False

def test_generate_auth_token_development():
    config = {
        "auth_mode": "development",
        "auth_token": "dev_token_123"
    }
    client = ZelloClient(api_config=config)
    token = client.generate_auth_token()
    assert token == "dev_token_123"

def test_event_registration():
    config = {"zello_channels": ["Chan1"]}
    client = ZelloClient(api_config=config)
    
    @client.on("connect")
    def on_connect_handler():
        pass
        
    assert "connect" in client._event_handlers
    assert len(client._event_handlers["connect"]) == 1
    assert client._event_handlers["connect"][0] == on_connect_handler
