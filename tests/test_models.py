"""Model registry tests are local and never contact providers."""
import unittest

from genesis.models import default_route, model_catalog, model_info, validate_model_config


class ModelRegistryTests(unittest.TestCase):
    def test_modern_prices_and_provenance(self):
        for model, rates in {"gpt-6.1-sol": (2, .1, 10), "gpt-6.1-terra": (1, .05, 5),
                             "gpt-6-luna": (.1, .01, .5), "gpt-6-astra": (10, 1, 50)}.items():
            with self.subTest(model=model):
                info = model_info("openai", model)
                price = info["pricing"]
                self.assertEqual(tuple(price[k] for k in ("input_cost_per_million", "cached_input_cost_per_million", "output_cost_per_million")), rates)
                self.assertEqual((price["long_context_threshold"], price["long_input_multiplier"], price["long_output_multiplier"]), (272000, 2, 1.5))
                self.assertEqual(info["verified_at"], "2026-11-09")
                self.assertTrue(info["source_url"].endswith("/" + model))
        catalog = model_catalog("openai")
        catalog[0]["pricing"]["input_cost_per_million"] = 999
        self.assertEqual(model_info("openai", "gpt-6.1-sol")["pricing"]["input_cost_per_million"], 2)

    def test_role_routes_and_efforts(self):
        for role, expected in {"coo": ("gpt-6-luna", "low"), "strategy": ("gpt-6.1-sol", "medium"),
                               "engineering": ("gpt-6.1-sol", "medium"), "finance": ("gpt-6.1-sol", "medium"),
                               "qa": ("gpt-6.1-terra", "medium"), "growth": ("gpt-6.1-terra", "low"),
                               "operations": ("gpt-6-luna", "low")}.items():
            route = default_route(role)
            self.assertEqual((route["model"], route["reasoning_effort"]), expected)
            self.assertEqual(validate_model_config(route), route)

    def test_validation_and_legacy_compatibility(self):
        self.assertEqual(validate_model_config({})["reasoning_effort"], "medium")
        self.assertNotIn("reasoning_effort", validate_model_config({"model": "custom:model-1"}))
        self.assertNotIn("reasoning_effort", validate_model_config({"model": "gpt-4.1"}))
        for config in ({"model": "bad model"}, {"model": []}, {"model": "custom", "reasoning_effort": "low"},
                       {"model": "gpt-4.1", "reasoning_effort": "low"}, {"model": "gpt-6.1-sol", "reasoning_effort": "none"},
                       {"model": "gpt-6.1-terra", "reasoning_effort": "bad"}, {"temperature": 1},
                       {"provider": "unknown"}, {"fallbacks": {}}, {"fallbacks": ["invalid"]}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                validate_model_config(config)

    def test_fallback_effort_is_independent_and_astra_is_gated(self):
        config = validate_model_config({"reasoning_effort": "high", "fallbacks": [{"model": "gpt-6-luna"}, {"provider": "anthropic"}]})
        self.assertEqual(config["fallbacks"][0]["reasoning_effort"], "low")
        self.assertNotIn("reasoning_effort", config["fallbacks"][1])
        for config in ({"model": "gpt-6-astra"}, {"fallbacks": [{"model": "gpt-6-astra"}]},
                       {"fallbacks": [{"model": "gpt-6-astra", "astra_authorized": True}]},
                       {"model": "gpt-6-astra", "astra_authorized": "true"}):
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, "CEO authorization"):
                validate_model_config(config)
        self.assertEqual(validate_model_config({"astra_authorized": True, "fallbacks": [{"model": "gpt-6-astra"}]})["fallbacks"][0]["reasoning_effort"], "low")

    def test_astra_snapshot_requires_root_authorization_without_guessed_metadata(self):
        model = "gpt-6-astra-2026-11-01"
        self.assertIsNone(model_info("openai", model))
        for config in ({"model": model}, {"fallbacks": [{"model": model}]},
                       {"fallbacks": [{"model": model, "astra_authorized": True}]}):
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, "CEO authorization"):
                validate_model_config(config)
        for config in ({"model": model, "astra_authorized": True},
                       {"astra_authorized": True, "fallbacks": [{"model": model}]}):
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, "Unverified Astra snapshot"):
                validate_model_config(config)
