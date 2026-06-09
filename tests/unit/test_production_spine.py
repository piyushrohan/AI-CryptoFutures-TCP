from datetime import UTC, datetime
import unittest

import httpx
from fastapi.testclient import TestClient

from apps.api.fastapi_app import create_app
from libs.binance_connector import (
    BinanceClientError,
    BinanceRateLimitState,
    BinanceRestConfig,
    BinanceRestResult,
    BinanceUsdmEnvironment,
    BinanceUsdmRestClient,
    ConnectorBoundaryError,
    signed_query_string,
    validate_usdm_order_payload,
)
from libs.config import CredentialScope, OperatorMode, RuntimeConfig, TradingGate, VenueTarget
from libs.schemas import PaperOrderIntent, default_account_state
from libs.security import (
    CredentialBundle,
    CredentialPurpose,
    EnvSecretProvider,
    SingleOwnerAuthConfig,
)
from services.audit import CommandLedgerError, InMemoryCommandLedger
from services.execution import (
    MonotonicOrderReconciler,
    VenueOrderStatus,
    VenueOrderUpdate,
)
from services.storage import PRODUCTION_TABLES, PostgresSettings
from services.portfolio import live_readonly_account_payload


AUTH = {"Authorization": "Bearer owner-token"}
AUTH_CSRF = {
    "Authorization": "Bearer owner-token",
    "X-TCP-CSRF-Token": "csrf-token",
}


def app_client() -> TestClient:
    auth = SingleOwnerAuthConfig.from_env(
        {
            "TCP_ADMIN_TOKEN": "owner-token",
            "TCP_CSRF_TOKEN": "csrf-token",
            "TCP_ACTOR_ID": "owner",
        }
    )
    return TestClient(create_app(auth_config=auth, command_ledger=InMemoryCommandLedger()))


class ProductionFastApiSpineTests(unittest.TestCase):
    def test_health_is_public_but_status_requires_auth(self):
        client = app_client()

        self.assertEqual(client.get("/api/v1/health").status_code, 200)
        self.assertEqual(client.get("/api/v1/status").status_code, 401)
        opened = client.get("/api/v1/status", headers=AUTH)

        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()["runtime"]["operator_mode"], "paper")

    def test_post_requires_csrf_and_records_command_ledger(self):
        client = app_client()
        body = {
            "command_type": "create_manual_order_intent",
            "payload": {"symbol": "BTCUSDC"},
            "idempotency_key": "idem-001",
        }

        blocked = client.post("/api/v1/commands/validate", headers=AUTH, json=body)
        opened = client.post(
            "/api/v1/commands/validate",
            headers=AUTH_CSRF,
            json=body,
        )

        self.assertEqual(blocked.status_code, 401)
        self.assertEqual(opened.status_code, 200)
        payload = opened.json()
        self.assertFalse(payload["command"]["accepted"])
        self.assertEqual(payload["command_ledger"]["status"], "rejected")
        self.assertEqual(payload["command_ledger"]["actor_id"], "owner")

    def test_idempotency_key_conflict_returns_409(self):
        client = app_client()
        first = {
            "command_type": "get_system_status",
            "payload": {},
            "idempotency_key": "idem-conflict",
        }
        second = {
            "command_type": "get_risk_status",
            "payload": {},
            "idempotency_key": "idem-conflict",
        }

        self.assertEqual(
            client.post(
                "/api/v1/commands/validate",
                headers=AUTH_CSRF,
                json=first,
            ).status_code,
            200,
        )
        conflict = client.post(
            "/api/v1/commands/validate",
            headers=AUTH_CSRF,
            json=second,
        )

        self.assertEqual(conflict.status_code, 409)

    def test_ops_status_redacts_storage_and_secret_values(self):
        client = app_client()

        payload = client.get("/api/v1/ops/status", headers=AUTH).json()

        self.assertTrue(payload["storage"]["database_url_redacted"])
        self.assertTrue(payload["secrets"]["testnet_trading"]["secrets_redacted"])
        self.assertEqual(payload["binance"]["network_calls"], "not_performed")


class ProductionFoundationContractTests(unittest.TestCase):
    def test_env_secret_provider_metadata_never_returns_secret_values(self):
        provider = EnvSecretProvider(
            {
                "BINANCE_TESTNET_API_KEY": "testnet-key",
                "BINANCE_TESTNET_API_SECRET": "testnet-secret",
            }
        )

        metadata = provider.public_metadata(CredentialPurpose.BINANCE_TESTNET_TRADING)

        self.assertTrue(metadata["api_key_present"])
        self.assertTrue(metadata["api_secret_present"])
        self.assertNotIn("testnet-key", str(metadata))
        self.assertNotIn("testnet-secret", str(metadata))

    def test_command_ledger_rejects_conflicting_idempotency_reuse(self):
        ledger = InMemoryCommandLedger()
        ledger.record_received(
            command_type="get_system_status",
            actor_id="owner",
            payload={},
            runtime={},
            idempotency_key="idem-1",
        )

        with self.assertRaises(CommandLedgerError):
            ledger.record_received(
                command_type="get_risk_status",
                actor_id="owner",
                payload={},
                runtime={},
                idempotency_key="idem-1",
            )

    def test_postgres_settings_are_redacted_and_list_required_tables(self):
        settings = PostgresSettings.from_env({"DATABASE_URL": "postgresql://secret"})

        payload = settings.to_public_dict()

        self.assertTrue(payload["configured"])
        self.assertTrue(payload["database_url_redacted"])
        self.assertIn("audit_records", PRODUCTION_TABLES)
        self.assertIn("command_ledger", payload["required_tables"])

    def test_credential_purposes_are_not_interchangeable(self):
        live_config_with_testnet_keys = RuntimeConfig(
            operator_mode=OperatorMode.LIVE,
            venue_target=VenueTarget.BINANCE_LIVE,
            credential_scope=CredentialScope.READ_ONLY,
            trading_gate=TradingGate.LOCKED,
            binance_testnet_api_key_present=True,
            binance_testnet_api_secret_present=True,
        )
        live_payload = live_readonly_account_payload(live_config_with_testnet_keys)

        metadata = next(
            item
            for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )
        testnet_payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            metadata,
            config=RuntimeConfig(
                venue_target=VenueTarget.BINANCE_TESTNET,
                credential_scope=CredentialScope.TRADING,
                binance_live_readonly_api_key_present=True,
                binance_live_readonly_api_secret_present=True,
            ),
        )

        self.assertFalse(live_payload["accepted"])
        self.assertIn("read-only Binance credentials", "; ".join(live_payload["reasons"]))
        self.assertIsNone(testnet_payload)
        self.assertIn("Binance credentials", "; ".join(reasons))

    def test_live_binance_order_payload_validation_is_out_of_scope(self):
        metadata = next(
            item
            for item in default_account_state().symbol_metadata
            if item.symbol == "BTCUSDC"
        )

        payload, reasons = validate_usdm_order_payload(
            PaperOrderIntent.from_mapping(
                {
                    "symbol": "BTCUSDC",
                    "side": "BUY",
                    "book_side": "LONG",
                    "quantity": "0.001",
                    "limit_price": "65000.4",
                }
            ),
            metadata,
            config=RuntimeConfig(
                operator_mode=OperatorMode.LIVE,
                venue_target=VenueTarget.BINANCE_LIVE,
                credential_scope=CredentialScope.READ_ONLY,
                trading_gate=TradingGate.LOCKED,
                binance_live_readonly_api_key_present=True,
                binance_live_readonly_api_secret_present=True,
            ),
        )

        self.assertIsNone(payload)
        joined = "; ".join(reasons)
        self.assertIn("live Binance order payload validation is out of scope", joined)
        self.assertIn("requires trading credentials", joined)

    def test_signed_query_uses_hmac_without_exposing_secret(self):
        query = signed_query_string(
            {"recvWindow": 5000, "timestamp": 1},
            api_secret="secret",
        )

        self.assertIn("signature=", query)
        self.assertNotIn("secret", query)

    def test_binance_client_rejects_missing_credentials_and_frontend_callers(self):
        config = BinanceRestConfig(BinanceUsdmEnvironment.TESTNET)
        self.assertIn("testnet", config.base_url)

        with self.assertRaises(BinanceClientError):
            BinanceUsdmRestClient(
                credentials=CredentialBundle(
                    CredentialPurpose.BINANCE_TESTNET_TRADING,
                    "",
                    "",
                ),
                config=config,
            )
        with self.assertRaises(ConnectorBoundaryError):
            BinanceUsdmRestClient(
                credentials=CredentialBundle(
                    CredentialPurpose.BINANCE_TESTNET_TRADING,
                    "key",
                    "secret",
                ),
                config=config,
                caller="frontend",
            )

    def test_binance_client_parses_rate_limits_with_mock_transport(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertIn("signature=", str(request.url))
            self.assertEqual(request.headers["X-MBX-APIKEY"], "key")
            return httpx.Response(
                200,
                json={"ok": True},
                headers={
                    "x-mbx-used-weight-1m": "12",
                    "x-mbx-order-count-10s": "2",
                },
            )

        client = BinanceUsdmRestClient(
            credentials=CredentialBundle(
                CredentialPurpose.BINANCE_TESTNET_TRADING,
                "key",
                "secret",
            ),
            config=BinanceRestConfig(BinanceUsdmEnvironment.TESTNET),
            http_client=httpx.Client(
                transport=httpx.MockTransport(handler),
                base_url="https://testnet.binancefuture.com",
            ),
        )

        result = client.signed_request("GET", "/fapi/v3/account")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.rate_limits.used_weight_1m, 12)
        self.assertEqual(result.rate_limits.order_count_10s, 2)
        self.assertIsInstance(result.rate_limits, BinanceRateLimitState)
        self.assertEqual(result.to_public_dict()["rate_limits"]["used_weight_1m"], 12)

    def test_binance_client_public_request_and_error_classes(self):
        statuses = [401, 429, 500, 400]
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            status = statuses[len(seen)]
            seen.append(status)
            return httpx.Response(
                status,
                text="not-json",
                headers={"x-mbx-used-weight-1m": "bad-int"},
            )

        client = BinanceUsdmRestClient(
            credentials=CredentialBundle(
                CredentialPurpose.BINANCE_TESTNET_TRADING,
                "key",
                "secret",
            ),
            config=BinanceRestConfig(BinanceUsdmEnvironment.TESTNET),
            http_client=httpx.Client(
                transport=httpx.MockTransport(handler),
                base_url="https://testnet.binancefuture.com",
            ),
        )

        self.assertEqual(client.public_request("GET", "/auth").error_class, "auth_error")
        self.assertEqual(client.public_request("GET", "/limit").error_class, "rate_limited")
        self.assertEqual(
            client.public_request("GET", "/server").error_class,
            "venue_server_error",
        )
        rejection = client.public_request("GET", "/bad")
        self.assertEqual(rejection.error_class, "venue_rejection")
        self.assertEqual(rejection.payload, {"text": "not-json"})
        self.assertIsNone(rejection.rate_limits.used_weight_1m)

    def test_binance_client_wraps_http_errors(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=request)

        client = BinanceUsdmRestClient(
            credentials=CredentialBundle(
                CredentialPurpose.BINANCE_TESTNET_TRADING,
                "key",
                "secret",
            ),
            config=BinanceRestConfig(BinanceUsdmEnvironment.TESTNET),
            http_client=httpx.Client(
                transport=httpx.MockTransport(handler),
                base_url="https://testnet.binancefuture.com",
            ),
        )

        with self.assertRaises(BinanceClientError):
            client.public_request("GET", "/fapi/v1/exchangeInfo")
        with self.assertRaises(BinanceClientError):
            client.signed_request("GET", "/fapi/v3/account")

    def test_binance_rest_result_public_dict(self):
        result = BinanceRestResult(
            status_code=200,
            payload={"ok": True},
            request_id="request-1",
            rate_limits=BinanceRateLimitState(order_count_1m=3),
        )

        self.assertEqual(result.to_public_dict()["request_id"], "request-1")
        self.assertEqual(
            result.to_public_dict()["rate_limits"]["order_count_1m"],
            3,
        )


    def test_reconciler_rejects_duplicate_and_regressive_updates(self):
        reconciler = MonotonicOrderReconciler()
        first = VenueOrderUpdate(
            venue_target="binance_testnet",
            order_id="1",
            client_order_id="client-1",
            status=VenueOrderStatus.NEW,
            execution_type="NEW",
            payload={},
            event_time=datetime.now(UTC),
        )
        filled = VenueOrderUpdate(
            **{
                **first.__dict__,
                "status": VenueOrderStatus.FILLED,
                "execution_type": "TRADE",
            }
        )

        self.assertTrue(reconciler.apply(first).accepted)
        self.assertFalse(reconciler.apply(first).accepted)
        self.assertTrue(reconciler.apply(filled).accepted)
        self.assertFalse(reconciler.apply(first).accepted)


if __name__ == "__main__":
    unittest.main()
