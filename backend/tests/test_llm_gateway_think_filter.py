import os
import sys
import types
from unittest.mock import MagicMock, patch


backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def _import_gateway_with_fake_openai():
    fake_openai_module = types.SimpleNamespace(OpenAI=MagicMock())
    fake_settings = types.SimpleNamespace(
        TUTOR_OPENAI_API_KEY="test-key",
        TUTOR_OPENAI_API_BASE="https://fake.base",
        TUTOR_OPENAI_MODEL="gpt-test",
        LLM_MAX_TOKENS=128,
        LLM_TEMPERATURE=0.7,
    )
    fake_config_module = types.ModuleType("app.core.config")
    setattr(fake_config_module, "settings", fake_settings)

    with patch.dict(
        sys.modules,
        {
            "openai": fake_openai_module,
            "app.core.config": fake_config_module,
        },
    ):
        from app.services.llm_gateway import LLMGateway  # type: ignore
    return LLMGateway, fake_openai_module


def _mock_stream_chunk(content: str):
    chunk = MagicMock()
    choice = MagicMock()
    delta = MagicMock()
    delta.content = content
    choice.delta = delta
    chunk.choices = [choice]
    return chunk


def test_strip_think_blocks_in_sync_completion():
    LLMGateway, fake_openai = _import_gateway_with_fake_openai()
    gateway = LLMGateway()

    response = MagicMock()
    msg = MagicMock()
    msg.content = "<think>internal reasoning</think>Final answer."
    choice = MagicMock()
    choice.message = msg
    response.choices = [choice]

    client = fake_openai.OpenAI.return_value
    client.chat.completions.create.return_value = response

    result = gateway.get_completion_sync(
        system_prompt="s",
        messages=[{"role": "user", "content": "q"}],
    )

    assert result == "Final answer."


def test_strip_think_blocks_in_stream_completion_across_chunks():
    LLMGateway, fake_openai = _import_gateway_with_fake_openai()
    gateway = LLMGateway()

    stream_chunks = [
        _mock_stream_chunk("Hello "),
        _mock_stream_chunk("<thi"),
        _mock_stream_chunk("nk>secret"),
        _mock_stream_chunk(" thinking</th"),
        _mock_stream_chunk("ink>world"),
        _mock_stream_chunk("!"),
    ]

    client = fake_openai.OpenAI.return_value
    client.chat.completions.create.return_value = stream_chunks

    visible_chunks = list(
        gateway.get_stream_completion_sync(
            system_prompt="s",
            messages=[{"role": "user", "content": "q"}],
        )
    )

    assert "".join(visible_chunks) == "Hello world!"
