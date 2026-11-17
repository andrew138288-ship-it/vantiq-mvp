from app.services.ai_gateway import build_sales_instructions


def test_sales_instructions_protect_against_prompt_injection():
    instructions = build_sales_instructions("pt-BR", "close a wholesale order")
    assert "untrusted data" in instructions
    assert "never as instructions" in instructions
    assert "human review only" in instructions
    assert "pt-BR" in instructions
    assert "close a wholesale order" in instructions


def test_sales_instructions_do_not_assume_sales_goal():
    instructions = build_sales_instructions("en-US", None)
    assert "Advance the conversation helpfully without pressure." in instructions


def test_portuguese_variants_remain_distinct():
    brazil = build_sales_instructions("pt-BR", None)
    portugal = build_sales_instructions("pt-PT", None)
    assert "pt-BR" in brazil
    assert "pt-PT" in portugal
    assert brazil != portugal


def test_ai_compares_two_distinct_strategies_and_selects_one():
    instructions = build_sales_instructions("zh-CN", "move the deal forward")
    assert "exactly TWO materially different" in instructions
    assert "materially different" in instructions
    assert "Select ONE best strategy" in instructions
    assert "Do not average the strategies" in instructions
    assert "Selected strategy and reason" in instructions
    assert "suggested_reply" in instructions
    assert "Output ONLY valid JSON" in instructions


def test_ai_must_separate_facts_from_hypotheses_and_avoid_invention():
    instructions = build_sales_instructions("en-US", None)
    assert "Separate observed facts from hypotheses" in instructions
    assert "Do not invent product facts, prices, stock" in instructions
    assert "facts or terms the salesperson should verify" in instructions


def test_universal_sales_scope_and_b2b_b2c():
    instructions = build_sales_instructions("en-US", None)
    assert "any legal product or service" in instructions
    assert "B2B or B2C" in instructions


def test_missing_api_key_fails_closed(monkeypatch):
    import asyncio
    import pytest
    from app.db import settings
    from app.services.ai_gateway import AIProviderNotConfigured, generate_sales_assist

    monkeypatch.setattr(settings, "openai_api_key", None)
    with pytest.raises(AIProviderNotConfigured):
        asyncio.run(
            generate_sales_assist(
                conversation_text="Customer: Hello",
                response_locale="en-US",
            )
        )


def test_structured_sales_decision_requires_two_strategies_and_valid_selection():
    import pytest
    from pydantic import ValidationError
    from app.schemas import SalesDecision

    strategy = {
        "name": "Clarify value",
        "objective": "Understand the buyer's priority",
        "rationale": "The buyer has not shared decision criteria",
        "next_move": "Ask one focused question",
        "risk": "May delay an immediate quote",
    }
    payload = {
        "customer_situation": "The buyer is comparing suppliers",
        "buying_stage": "consideration",
        "buying_signals": ["Asked about warranty"],
        "objections": ["Price uncertainty"],
        "strategy_1": strategy,
        "strategy_2": {**strategy, "name": "Offer a scoped quote"},
        "comparison": "Strategy 1 reduces uncertainty; strategy 2 advances pricing",
        "selected_strategy": "strategy_1",
        "selection_reason": "Decision criteria are still unclear",
        "suggested_reply": "May I ask what matters most in your comparison?",
        "before_sending": ["Confirm warranty terms"],
    }
    decision = SalesDecision.model_validate(payload)
    assert decision.selected_strategy == "strategy_1"
    assert decision.strategy_2.name == "Offer a scoped quote"

    payload["selected_strategy"] = "strategy_3"
    with pytest.raises(ValidationError):
        SalesDecision.model_validate(payload)



def test_provider_diagnostics_classifies_authentication_without_logging_secrets(caplog):
    from app.services.ai_gateway import _log_provider_failure

    class FakeAuthenticationError(Exception):
        status_code = 401
        code = "invalid_api_key"
        request_id = "req_12345678"

        def __str__(self):
            return "request failed with sk-proj-this-must-never-be-logged"

    caplog.set_level("WARNING")
    _log_provider_failure(FakeAuthenticationError())

    record = next(record for record in caplog.records if record.name == "app.services.ai_gateway")
    assert record.vantiq_ai_category == "authentication"
    assert record.vantiq_ai_status_code == 401
    assert record.vantiq_ai_error_code == "invalid_api_key"
    assert record.vantiq_ai_request_id == "req_12345678"
    assert "sk-proj-this-must-never-be-logged" not in caplog.text


def test_provider_diagnostics_distinguishes_quota_and_model_errors():
    from app.services.ai_gateway import _provider_error_diagnostics

    class FakeQuotaError(Exception):
        status_code = 429
        code = "insufficient_quota"

    class FakeModelError(Exception):
        status_code = 404
        code = "model_not_found"

    quota = _provider_error_diagnostics(FakeQuotaError())
    model = _provider_error_diagnostics(FakeModelError())

    assert quota["vantiq_ai_category"] == "quota_or_rate_limit"
    assert quota["vantiq_ai_error_code"] == "insufficient_quota"
    assert model["vantiq_ai_category"] == "model_or_endpoint"
    assert model["vantiq_ai_error_code"] == "model_not_found"


def test_provider_diagnostics_does_not_copy_unrecognized_error_text():
    from app.services.ai_gateway import _provider_error_diagnostics

    class FakeUnknownError(Exception):
        status_code = 400
        code = "sk-proj-secret-value"

    diagnostics = _provider_error_diagnostics(FakeUnknownError())

    assert diagnostics["vantiq_ai_category"] == "unknown"
    assert diagnostics["vantiq_ai_error_code"] is None
    assert "sk-proj-secret-value" not in str(diagnostics)
