import pytest
from unittest.mock import patch, MagicMock
from models.huggingface import HuggingFaceProvider
import urllib.error

def test_huggingface_provider_formatting():
    """Verify HuggingFaceProvider correctly formats requests to the HF serverless API."""
    provider = HuggingFaceProvider(model="Qwen/Qwen3-Coder-Next", api_key="hf_test_key")
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"choices": [{"message": {"content": "Test response"}}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        resp = provider.complete("Hello world!", system="System msg", temperature=0.5, max_tokens=100)
        
        # Verify response parsed correctly
        assert resp.text == "Test response"
        assert resp.model == "Qwen/Qwen3-Coder-Next"
        
        # Verify HTTP request was formulated correctly
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        
        assert req.full_url == "https://api-inference.huggingface.co/models/Qwen/Qwen3-Coder-Next/v1/chat/completions"
        assert req.get_header("Authorization") == "Bearer hf_test_key"
        assert req.get_header("Content-type") == "application/json"
        
        # Verify JSON payload
        import json
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "Qwen/Qwen3-Coder-Next"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100
        assert len(payload["messages"]) == 2
        assert payload["messages"][0] == {"role": "system", "content": "System msg"}
        assert payload["messages"][1] == {"role": "user", "content": "Hello world!"}

def test_huggingface_provider_http_error():
    provider = HuggingFaceProvider(model="Qwen/Qwen3-Coder-Next", api_key="hf_test_key")
    with patch("urllib.request.urlopen") as mock_urlopen:
        fp_mock = MagicMock()
        fp_mock.read.return_value = b'{"error": "Invalid API key"}'
        error = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=fp_mock)
        mock_urlopen.side_effect = error
        
        with pytest.raises(RuntimeError, match="Hugging Face API error 401: .*Invalid API key.*"):
            provider.complete("Test")

def test_huggingface_provider_availability():
    assert not HuggingFaceProvider(api_key="").available()
    assert HuggingFaceProvider(api_key="hf_test").available()
