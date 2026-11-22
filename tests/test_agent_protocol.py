#!/usr/bin/env python3
"""
tests/test_agent_protocol.py
Unit test suite for Open Agentic Web Protocol (OAW-1.0.0) reference implementation.
Tests:
1. Agent Identity and HMAC signature verification
2. Capability manifest creation and serialization
3. Bilateral contract creation and multi-agent signing
4. Escrow locking and settlement with deterministic hash verification
5. Fraud detection / hash mismatch reputation slashing
6. End-to-end network discovery and execution
"""

import hashlib
import json
import os
import sys
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from open_agentic_protocol import (
    AgentIdentity,
    CapabilityManifest,
    AgentContract,
    SettlementEngine,
    AgentNetworkHub
)

class TestOpenAgenticProtocol(unittest.TestCase):

    def setUp(self):
        self.client = AgentIdentity("agent:client-corp", "seed_secret_client_12345")
        self.provider = AgentIdentity("agent:auditor-pro", "seed_secret_provider_67890")
        self.provider.reputation_score = 0.90
        self.hub = AgentNetworkHub(network_id="oaw:testnet")

    def test_identity_and_signature(self):
        msg = b"execute_seo_audit_task_01"
        sig = self.client.sign(msg)
        self.assertTrue(self.client.verify_signature(msg, sig))
        self.assertFalse(self.client.verify_signature(b"tampered_message", sig))

    def test_capability_manifest(self):
        skill = CapabilityManifest(
            skill_id="skill:technical-audit",
            version="1.0.0",
            base_price_micro=1500000,
            currency="INR",
            sla_latency_ms=2000
        )
        data = skill.to_dict()
        self.assertEqual(data["skill_id"], "skill:technical-audit")
        self.assertEqual(data["pricing_model"]["base_price_micro_units"], 1500000)

    def test_contract_signing_flow(self):
        contract = AgentContract(
            contract_id="CTR-001",
            client_id=self.client.agent_id,
            provider_id=self.provider.agent_id,
            skill_id="skill:technical-audit",
            agreed_price_micro=1500000,
            task_spec={"target_url": "https://example.com"}
        )
        self.assertFalse(contract.is_fully_signed())

        # Sign client
        self.assertTrue(contract.sign_contract(self.client))
        self.assertFalse(contract.is_fully_signed())

        # Sign provider
        self.assertTrue(contract.sign_contract(self.provider))
        self.assertTrue(contract.is_fully_signed())
        self.assertEqual(contract.state, "ACTIVE")

    def test_settlement_and_escrow_release(self):
        deliverable = {"status": "SUCCESS", "pages_crawled": 42, "critical_issues": 3}
        output_bytes = json.dumps(deliverable, sort_keys=True).encode("utf-8")
        expected_hash = hashlib.sha256(output_bytes).hexdigest()

        contract = AgentContract(
            contract_id="CTR-002",
            client_id=self.client.agent_id,
            provider_id=self.provider.agent_id,
            skill_id="skill:technical-audit",
            agreed_price_micro=1500000,
            task_spec={"expected_sha256": expected_hash}
        )
        contract.sign_contract(self.client)
        contract.sign_contract(self.provider)

        engine = SettlementEngine()
        self.assertTrue(engine.deposit_escrow(contract))
        self.assertEqual(contract.state, "ESCROW_LOCKED")

        success, msg = engine.verify_and_settle(contract, deliverable, self.client, self.provider)
        self.assertTrue(success)
        self.assertEqual(contract.state, "SETTLED")
        self.assertEqual(contract.settlement_hash, expected_hash)
        self.assertGreater(self.provider.reputation_score, 0.90)

    def test_settlement_fraud_detection(self):
        contract = AgentContract(
            contract_id="CTR-003",
            client_id=self.client.agent_id,
            provider_id=self.provider.agent_id,
            skill_id="skill:technical-audit",
            agreed_price_micro=1500000,
            task_spec={"expected_sha256": "expected_valid_sha256_hash_here"}
        )
        contract.sign_contract(self.client)
        contract.sign_contract(self.provider)

        engine = SettlementEngine()
        engine.deposit_escrow(contract)

        initial_rep = self.provider.reputation_score
        fake_deliverable = {"malicious": True}
        success, msg = engine.verify_and_settle(contract, fake_deliverable, self.client, self.provider)

        self.assertFalse(success)
        self.assertEqual(contract.state, "DISPUTED_HASH_MISMATCH")
        self.assertLess(self.provider.reputation_score, initial_rep)

    def test_hub_discovery_and_atomic_execution(self):
        skill = CapabilityManifest("skill:market-intel", "1.0", 1200000)
        self.hub.register_agent(self.provider, [skill])

        deliverable = {"records_extracted": 150}
        d_bytes = json.dumps(deliverable, sort_keys=True).encode("utf-8")
        expected_hash = hashlib.sha256(d_bytes).hexdigest()

        task_spec = {"query": "fintech agencies", "expected_sha256": expected_hash}
        success, res = self.hub.negotiate_and_execute(
            client=self.client,
            skill_id="skill:market-intel",
            task_spec=task_spec,
            max_price=2000000,
            deliverable_payload=deliverable
        )
        self.assertTrue(success)
        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["price_settled"], 1200000)

if __name__ == "__main__":
    unittest.main()
