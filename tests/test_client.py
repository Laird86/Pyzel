import pytest
from pyzel.client import ZelloClient

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

@pytest.mark.asyncio
async def test_logon_payload():
    from unittest.mock import patch, MagicMock
    import asyncio
    
    config = {
        "auth_mode": "development",
        "auth_token": "dev_token_123",
        "zello_username": "tester",
        "zello_password": "supersecretpassword",
        "zello_channels": ["TestChannel1", "TestChannel2"]
    }
    client = ZelloClient(api_config=config)
    
    # Mock send_json to capture the payload
    with patch.object(client, "send_json") as mock_send_json:
        # Mock logger to ensure no secrets are logged
        with patch("pyzel.client.logger") as mock_logger:
            # Mock websocket connect to yield a dummy websocket
            class DummyWebsocket:
                async def recv(self):
                    return '{"success": true}'
                async def __aenter__(self):
                    return self
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
                    
            with patch("websockets.connect", return_value=DummyWebsocket()):
                # Run start as a task so we can cancel it after logon
                task = asyncio.create_task(client.start())
                
                # Yield control to the event loop so start() can run
                await asyncio.sleep(0.1)
                
                # Check that send_json was called with the logon payload
                logon_call = mock_send_json.call_args_list[0]
                payload = logon_call[0][0]
                
                assert payload["command"] == "logon"
                assert payload["username"] == "tester"
                # Ensure channels are actually the target channels, not an empty list
                assert payload["channels"] == ["TestChannel1", "TestChannel2"]
                assert "supersecretpassword" == payload["password"]
                
                # Verify that the supersecretpassword does not appear in any log call
                for call in mock_logger.debug.call_args_list + mock_logger.info.call_args_list + mock_logger.warning.call_args_list + mock_logger.error.call_args_list + mock_logger.critical.call_args_list:
                    # check all args and kwargs strings
                    for arg in call.args:
                        assert "supersecretpassword" not in str(arg)
                    for kwarg in call.kwargs.values():
                        assert "supersecretpassword" not in str(kwarg)
                
                task.cancel()

