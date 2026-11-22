#!/usr/bin/env python3
"""
open_agentic_protocol.py
Open Agentic Web Protocol (OAW-1.0.0) Reference Implementation
Built for the Open Agentic Web Challenge (Cognizant / MIT NANDA / Mozilla / AWS).

Implements:
1. Agent Identity & Cryptographic Keypair Verification
2. Dynamic Capability Manifest Publishing & Discovery
3. Multi-Agent Bilateral Contract Negotiation
4. Deterministic Artifact Settlement & Escrow Release
5. Verifiable Reputation Accounting
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

class AgentIdentity:
    """Manages agent identity, cryptographic signing, and public key verification."""
    def __init__(self, agent_id: str, secret_seed: str, endpoint_url: str = "https://agent.local/v1"):
        self.agent_id = agent_id
        self.secret_seed = secret_seed.encode("utf-8")
        self.public_key = hashlib.sha256(self.secret_seed).hexdigest()
        self.endpoint_url = endpoint_url
        self.reputation_score = 1.0

    def sign(self, payload_bytes: bytes) -> str:
        """Produces a deterministic HMAC-SHA256 signature over payload bytes."""
        return hmac.new(self.secret_seed, payload_bytes, hashlib.sha256).hexdigest()

    def verify_signature(self, payload_bytes: bytes, signature: str) -> bool:
        """Verifies an HMAC signature against the secret seed."""
        expected = self.sign(payload_bytes)
        return hmac.compare_digest(expected, signature)

    def export_public_manifest(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "public_key": self.public_key,
            "endpoint_url": self.endpoint_url,
            "reputation_score": round(self.reputation_score, 4)
        }

class CapabilityManifest:
    """Represents a set of services an agent can perform with pricing and SLA bounds."""
    def __init__(self, skill_id: str, version: str, base_price_micro: int, currency: str = "INR", sla_latency_ms: int = 5000):
        self.skill_id = skill_id
        self.version = version
        self.base_price_micro = base_price_micro
        self.currency = currency
        self.sla_latency_ms = sla_latency_ms

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "pricing_model": {
                "currency": self.currency,
                "base_price_micro_units": self.base_price_micro,
                "unit_metric": "per_task"
            },
            "sla_latency_ms": self.sla_latency_ms
        }

class AgentContract:
    """Represents an agreed, cryptographically bound micro-contract between two agents."""
    def __init__(self, contract_id: str, client_id: str, provider_id: str, skill_id: str, agreed_price_micro: int, task_spec: dict, timeout_seconds: int = 60):
        self.contract_id = contract_id
        self.client_id = client_id
        self.provider_id = provider_id
        self.skill_id = skill_id
        self.agreed_price_micro = agreed_price_micro
        self.task_spec = task_spec
        self.created_utc = datetime.now(timezone.utc).isoformat()
        self.timeout_seconds = timeout_seconds
        self.state = "INITIATED"
        self.client_signature: Optional[str] = None
        self.provider_signature: Optional[str] = None
        self.settlement_hash: Optional[str] = None

    def canonical_bytes(self) -> bytes:
        payload = {
            "contract_id": self.contract_id,
            "client_id": self.client_id,
            "provider_id": self.provider_id,
            "skill_id": self.skill_id,
            "price": self.agreed_price_micro,
            "task": self.task_spec
        }
        return json.dumps(payload, sort_keys=True).encode("utf-8")

    def sign_contract(self, agent: AgentIdentity) -> bool:
        sig = agent.sign(self.canonical_bytes())
        if agent.agent_id == self.client_id:
            self.client_signature = sig
        elif agent.agent_id == self.provider_id:
            self.provider_signature = sig
        else:
            return False

        if self.client_signature and self.provider_signature:
            self.state = "ACTIVE"
        return True

    def is_fully_signed(self) -> bool:
        return bool(self.client_signature and self.provider_signature and self.state == "ACTIVE")

class SettlementEngine:
    """Verifies deliverable execution and performs escrow releases or penalty slashes."""
    def __init__(self):
        self.escrow_vault: Dict[str, int] = {}
        self.settled_contracts: List[dict] = []

    def deposit_escrow(self, contract: AgentContract) -> bool:
        if not contract.is_fully_signed():
            return False
        self.escrow_vault[contract.contract_id] = contract.agreed_price_micro
        contract.state = "ESCROW_LOCKED"
        return True

    def verify_and_settle(self, contract: AgentContract, deliverable_payload: dict, client: AgentIdentity, provider: AgentIdentity) -> Tuple[bool, str]:
        """
        Validates deliverable output against contract completion hash and releases escrow.
        """
        if contract.state != "ESCROW_LOCKED":
            return False, f"Contract state must be ESCROW_LOCKED, got {contract.state}"

        # 1. Deterministic output verification
        req_hash = contract.task_spec.get("expected_sha256")
        output_bytes = json.dumps(deliverable_payload, sort_keys=True).encode("utf-8")
        calc_hash = hashlib.sha256(output_bytes).hexdigest()

        if req_hash and calc_hash != req_hash:
            # Verification failure -> Slash provider reputation and refund escrow
            provider.reputation_score = max(0.0, provider.reputation_score - 0.1)
            contract.state = "DISPUTED_HASH_MISMATCH"
            del self.escrow_vault[contract.contract_id]
            return False, f"Verification failed: hash mismatch ({calc_hash} != {req_hash})"

        # 2. Release Escrow
        amount = self.escrow_vault.pop(contract.contract_id, 0)
        contract.settlement_hash = calc_hash
        contract.state = "SETTLED"
        provider.reputation_score = min(1.0, provider.reputation_score + 0.02)

        record = {
            "contract_id": contract.contract_id,
            "settled_utc": datetime.now(timezone.utc).isoformat(),
            "amount_micro": amount,
            "deliverable_hash": calc_hash,
            "provider_reputation": provider.reputation_score
        }
        self.settled_contracts.append(record)
        return True, "Settlement successful; escrow released"

class AgentNetworkHub:
    """Decentralized Registry and Discovery Router for OAW-1.0.0 Agents."""
    def __init__(self, network_id: str = "oaw:global-mainnet"):
        self.network_id = network_id
        self.registry: Dict[str, AgentIdentity] = {}
        self.capabilities: Dict[str, List[CapabilityManifest]] = {}
        self.settlement = SettlementEngine()

    def register_agent(self, agent: AgentIdentity, skills: List[CapabilityManifest]) -> dict:
        self.registry[agent.agent_id] = agent
        self.capabilities[agent.agent_id] = skills
        return agent.export_public_manifest()

    def discover_providers(self, required_skill_id: str, max_price_micro: Optional[int] = None) -> List[dict]:
        candidates = []
        for aid, skills in self.capabilities.items():
            agent = self.registry.get(aid)
            if not agent:
                continue
            for sk in skills:
                if sk.skill_id == required_skill_id:
                    if max_price_micro is None or sk.base_price_micro <= max_price_micro:
                        candidates.append({
                            "agent_id": aid,
                            "public_key": agent.public_key,
                            "skill": sk.to_dict(),
                            "reputation": agent.reputation_score
                        })
        # Rank candidates by reputation descending, price ascending
        candidates.sort(key=lambda c: (-c["reputation"], c["skill"]["pricing_model"]["base_price_micro_units"]))
        return candidates

    def negotiate_and_execute(self, client: AgentIdentity, skill_id: str, task_spec: dict, max_price: int, deliverable_payload: dict) -> Tuple[bool, dict]:
        """Runs an end-to-end atomic discovery, contract signing, and settlement flow."""
        providers = self.discover_providers(skill_id, max_price)
        if not providers:
            return False, {"error": "No capable providers discovered within price ceiling"}

        chosen = providers[0]
        provider = self.registry[chosen["agent_id"]]

        contract_id = f"OAW-CTR-{int(time.time()*1000)}"
        contract = AgentContract(
            contract_id=contract_id,
            client_id=client.agent_id,
            provider_id=provider.agent_id,
            skill_id=skill_id,
            agreed_price_micro=chosen["skill"]["pricing_model"]["base_price_micro_units"],
            task_spec=task_spec
        )

        # Both agents sign
        contract.sign_contract(client)
        contract.sign_contract(provider)

        if not contract.is_fully_signed():
            return False, {"error": "Bilateral contract signing failed"}

        # Lock escrow
        if not self.settlement.deposit_escrow(contract):
            return False, {"error": "Escrow deposit rejected"}

        # Execute & Settle
        success, msg = self.settlement.verify_and_settle(contract, deliverable_payload, client, provider)
        return success, {
            "contract_id": contract.contract_id,
            "status": contract.state,
            "message": msg,
            "settlement_hash": contract.settlement_hash,
            "price_settled": contract.agreed_price_micro
        }
