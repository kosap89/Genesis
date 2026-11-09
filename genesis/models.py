"""Reviewed model capabilities and public list prices; no account access implied."""
from copy import deepcopy
import re

DEFAULT_MODELS = {"openai": "gpt-6.1-sol", "anthropic": "claude-sonnet-4-5", "gemini": "gemini-2.5-flash"}
VERIFIED_AT = "2026-11-09"


def _entry(model, rates, efforts=(), default=None, modern=False, label=None):
    return {"id": model, "label": label or model, "reasoning_efforts": list(efforts),
            "default_reasoning_effort": default,
            "pricing": {"input_cost_per_million": rates[0], "cached_input_cost_per_million": rates[1],
                        "output_cost_per_million": rates[2], "long_context_threshold": 272000 if modern else None,
                        "long_input_multiplier": 2 if modern else 1, "long_output_multiplier": 1.5 if modern else 1},
            "source_url": "https://developers.openai.com/api/docs/models/" + model,
            "verified_at": VERIFIED_AT, "requires_ceo_authorization": model == "gpt-6-astra"}


_EFFORTS = ("low", "medium", "high", "xhigh", "max")
_CATALOG = {"openai": [
    _entry("gpt-6.1-sol", (2, .10, 10), _EFFORTS, "medium", True),
    _entry("gpt-6.1-terra", (1, .05, 5), ("none",) + _EFFORTS, "low", True),
    _entry("gpt-6-luna", (.10, .01, .50), ("none",) + _EFFORTS, "low", True),
    _entry("gpt-6-astra", (10, 1, 50), _EFFORTS, "low", True),
    _entry("gpt-4.1-mini", (.4, .1, 1.6), label="gpt-4.1-mini (legacy)"),
    _entry("gpt-4.1", (2, .5, 8), label="gpt-4.1 (legacy)"),
]}


def model_catalog(provider):
    return deepcopy(_CATALOG.get(provider, []))


def model_info(provider, model):
    return next((entry for entry in model_catalog(provider) if entry["id"] == model), None)


def default_route(role):
    routes = {"coo": ("gpt-6-luna", "low"), "strategy": ("gpt-6.1-sol", "medium"),
              "engineering": ("gpt-6.1-sol", "medium"), "finance": ("gpt-6.1-sol", "medium"),
              "qa": ("gpt-6.1-terra", "medium"), "growth": ("gpt-6.1-terra", "low"),
              "operations": ("gpt-6-luna", "low"), "ops": ("gpt-6-luna", "low")}
    model, effort = routes.get(role.lower(), routes["coo"])
    return {"provider": "openai", "model": model, "reasoning_effort": effort}


def validate_model_config(config):
    """Normalize routes before transport, including every explicit fallback.

    Custom models remain usable, but cannot inherit a guessed reasoning setting.
    Fallback reasoning is always selected independently of the primary route.
    """
    if not isinstance(config, dict):
        raise ValueError("Model configuration must be an object")
    result = dict(config)
    provider = result.get("provider", "openai")
    if not isinstance(provider, str) or provider not in DEFAULT_MODELS:
        raise ValueError("Unsupported provider")
    model = result.get("model")
    if model is None or model == "":
        model = DEFAULT_MODELS[provider]
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
        raise ValueError("Invalid model id")
    result.update(provider=provider, model=model)
    info = model_info(provider, model)
    effort = result.get("reasoning_effort")
    if info and info["reasoning_efforts"]:
        effort = info["default_reasoning_effort"] if effort in (None, "") else effort
        if effort not in info["reasoning_efforts"]:
            raise ValueError("Unsupported reasoning effort for " + model)
        result["reasoning_effort"] = effort
        if "temperature" in result:
            raise ValueError("Temperature is unsupported for " + model)
    elif effort not in (None, ""):
        raise ValueError("Reasoning effort is not supported for this model")
    else:
        result.pop("reasoning_effort", None)
    # Authorization follows the Astra family, including unverified snapshot ids.
    # Snapshot capability/pricing metadata is intentionally not guessed.
    if (model == "gpt-6-astra" or model.startswith("gpt-6-astra-")) and result.get("astra_authorized") is not True:
        raise ValueError("gpt-6-astra requires explicit CEO authorization")
    if model.startswith("gpt-6-astra-"):
        raise ValueError("Unverified Astra snapshot; select the reviewed gpt-6-astra model")
    if "fallbacks" in result:
        if not isinstance(result["fallbacks"], list):
            raise ValueError("Fallbacks must be a list")
        fallbacks = []
        for fallback in result["fallbacks"]:
            if not isinstance(fallback, dict) or fallback.get("fallbacks"):
                raise ValueError("Invalid fallback configuration")
            # CEO authorization is a per-task capability, shared with its routes.
            fallbacks.append(validate_model_config({**fallback, "astra_authorized": result.get("astra_authorized", False)}))
        result["fallbacks"] = fallbacks
    return result
