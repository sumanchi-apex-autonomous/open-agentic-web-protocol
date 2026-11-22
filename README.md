# Open Agentic Protocol (OAW-1.0.0)

**Reference Implementation & Multi-Agent Micro-Settlement Engine**  
*Submitted to the Open Agentic Web Challenge (Cognizant &bull; MIT NANDA &bull; Mozilla &bull; AWS)*  
*Track T-B: Open-Source Autonomous Infrastructure*

[![Protocol Version](https://img.shields.io/badge/protocol-OAW--1.0.0-blue.svg)](agent_network_spec.json)
[![Tests](https://img.shields.io/badge/tests-6%2F6%20passing-brightgreen.svg)](tests/test_agent_protocol.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 1. Executive Summary

As autonomous AI agents proliferate across diverse cloud infrastructures, the absence of an open, decentralized standard for **agent discovery, capability negotiation, and verified micro-settlement** presents a critical bottleneck. Agents cannot reliably purchase sub-services from other agents without risking payment fraud, hallucinated completion claims, or proprietary platform lock-in.

The **Open Agentic Protocol (OAW-1.0.0)** establishes a zero-dependency, mathematically verifiable communication and economic layer for heterogeneous multi-agent systems. It enables any autonomous agent to:
1. **Declare Cryptographic Identity**: Public-key identity paired with HMAC-SHA256 signature verification.
2. **Publish Capability Manifests**: Standardized JSON-Schema descriptors of offered skills, unit pricing, and SLA latency ceilings.
3. **Execute Bilateral Micro-Contracts**: Non-repudiable contracts signed by both client and provider agents.
4. **Enforce Deterministic Escrow**: Cryptographic output hash verification before capital or compute units are released.
5. **Decentralized Reputation Accounting**: Automated scoring adjustments that reward verified deliverable completion and slash fraudulent claims.

---

## 2. Architecture & Transaction Flow

```
+---------------+                                           +------------------+
| Client Agent  |                                           |  Provider Agent  |
| (Needs Audit) |                                           | (Executes Audit) |
+---------------+                                           +------------------+
       |                                                             |
       | 1. Query Providers [skill:technical-audit]                  |
       +-----------------------------\                               |
                                      v                              |
                          +-----------------------+                  |
                          |  AgentNetworkHub      |                  |
                          |  (Discovery & Router) |                  |
                          +-----------------------+                  |
                                      |                              |
       | 2. Ranked Provider List      |                              |
       |<-----------------------------+                              |
       |                                                             |
       | 3. Propose AgentContract(CTR-XXXX)                          |
       |------------------------------------------------------------>|
       |                                                             |
       | 4. Bilateral Signatures: client_sig + provider_sig          |
       |<===========================================================>|
       |                                                             |
       | 5. Lock Escrow in SettlementEngine                          |
       +-----------------------------\                               |
                                      v                              |
                          +-----------------------+                  |
                          |  Escrow Vault (Locked)|                  |
                          +-----------------------+                  |
                                                                     |
                                      6. Execute Task & Emit Output  |
                                      ------------------------------>|
                                                                     |
                          +-----------------------+                  |
                          | SHA256 Output Verify  |                  |
                          +-----------------------+                  |
                                      |                              |
       | 7. Escrow Released + Reputation Bump                        |
       |<------------------------------------------------------------+
```

---

## 3. Repository Structure

```
V-DEVPOST-HACKATHON/repo/
├── agent_network_spec.json       # Formal JSON-Schema specification for OAW-1.0.0
├── open_agentic_protocol.py     # Core Python reference implementation
├── tests/
│   └── test_agent_protocol.py   # Comprehensive unit test suite (6/6 passing)
└── README.md                    # Technical documentation and integration guide
```

---

## 4. Quickstart & Installation

The reference implementation requires Python 3.9+ with zero external package dependencies.

### Running the Test Suite
From the repository root:

```bash
python -m unittest tests/test_agent_protocol.py
```

Expected output:
```text
......
----------------------------------------------------------------------
Ran 6 tests in 0.001s

OK
```

---

## 5. Integration Example

```python
import hashlib
import json
from open_agentic_protocol import AgentIdentity, CapabilityManifest, AgentNetworkHub

# 1. Initialize Network Hub
hub = AgentNetworkHub(network_id="oaw:global-mainnet")

# 2. Provider Agent registers capability
provider = AgentIdentity("agent:fast-audit-node", "secure_secret_seed_42")
skill = CapabilityManifest(
    skill_id="skill:core-web-vitals",
    version="1.0.0",
    base_price_micro=1500000, # 1.5 INR in micro-units
    currency="INR",
    sla_latency_ms=1500
)
hub.register_agent(provider, [skill])

# 3. Client Agent discovers and executes contract
client = AgentIdentity("agent:enterprise-crawler", "client_secret_seed_99")

deliverable = {"status": "SUCCESS", "lcp_score": 1.4, "cls_score": 0.02}
expected_sha = hashlib.sha256(json.dumps(deliverable, sort_keys=True).encode("utf-8")).hexdigest()

success, receipt = hub.negotiate_and_execute(
    client=client,
    skill_id="skill:core-web-vitals",
    task_spec={"target_url": "https://company.example.com", "expected_sha256": expected_sha},
    max_price=2000000,
    deliverable_payload=deliverable
)

print(f"Contract Status: {receipt['status']}")
print(f"Settlement Hash: {receipt['settlement_hash']}")
print(f"Price Paid: {receipt['price_settled']} micro-units")
```

---

## 6. Formal Specification Reference

The protocol schema is defined in [agent_network_spec.json](agent_network_spec.json). It mandates:
- Canonical JSON serialization (`sort_keys=True`) for all cryptographic inputs.
- HMAC-SHA256 non-repudiation on bilateral contract states.
- Explicit failure classification (`DISPUTED_HASH_MISMATCH`, `TIMEOUT`, `SLA_BREACH`).

---

## 7. License & Credits

Developed by **Apex Autonomous Technologies** for the **Open Agentic Web Challenge** (January 2027 deadline).  
Licensed under the Apache 2.0 Open Source License.
