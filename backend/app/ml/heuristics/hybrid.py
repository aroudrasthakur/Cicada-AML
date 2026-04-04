"""Hybrid (on-chain + off-chain) AML heuristics (IDs 143-155, 176-185)."""
from __future__ import annotations

from typing import Any, Optional

from app.ml.heuristics.base import (
    BaseHeuristic,
    HeuristicResult,
    Applicability,
    Environment,
)
from app.ml.heuristics.common_red_flags import (
    check_high_risk_counterparty,
    check_tainted_to_cashout,
    check_many_to_one,
    check_circular_flows,
    check_mule_patterns,
    check_no_economic_rationale,
)

ENV = Environment.HYBRID


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _stub(_hid: int, _name: str, _tags: list[str], _desc: str, _reqs: list[str]):
    class _S(BaseHeuristic):
        id = _hid
        name = _name
        environment = ENV
        lens_tags = _tags
        description = _desc
        data_requirements = _reqs

        def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
            appl = self.check_data_requirements(context)
            if appl != Applicability.APPLICABLE:
                return HeuristicResult(applicability=appl)
            return HeuristicResult()

    _S.__name__ = _S.__qualname__ = f"H{_hid}_{_name.replace(' ', '')}"
    return _S()


# ===================================================================
# Heuristics with address-tag-based detection (no off-chain data req)
# ===================================================================

class P2PExchangeLaundering(BaseHeuristic):
    id = 144
    name = "P2PExchangeLaundering"
    environment = ENV
    lens_tags = ["graph", "offramp"]
    description = "Layering through peer-to-peer exchange platforms."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        tainted, score = check_tainted_to_cashout(features, context)
        if tainted:
            return HeuristicResult(
                triggered=True,
                confidence=score,
                explanation=f"P2P exchange path: taint-to-cashout score {score:.2f}, tags {tags}.",
                evidence={"cashout_score": score, "risk_tags": tags},
            )
        return HeuristicResult()


class CrossBorderExchangeArbitrage(BaseHeuristic):
    id = 149
    name = "CrossBorderExchangeArbitrage"
    environment = ENV
    lens_tags = ["offramp", "behavioral"]
    description = "Exploiting price differences between exchanges across jurisdictions."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        arb_score = features.get("cross_exchange_arb_score", 0)
        triggered = arb_score > 0.5
        return HeuristicResult(
            triggered=triggered,
            confidence=min(arb_score, 1.0) if triggered else 0.0,
            explanation=f"Cross-border arbitrage score {arb_score:.2f}." if triggered else "",
            evidence={"arb_score": arb_score},
        )


class SanctionsEvasionStablecoinCorridor(BaseHeuristic):
    id = 176
    name = "SanctionsEvasionStablecoinCorridor"
    environment = ENV
    lens_tags = ["offramp", "graph", "entity"]
    description = "Stablecoin corridors used to evade geographic sanctions."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        sanctioned = [t for t in tags if t.lower() == "sanctioned"]
        if sanctioned:
            return HeuristicResult(
                triggered=True,
                confidence=0.9,
                explanation=f"Stablecoin corridor touching sanctioned entities: {sanctioned}.",
                evidence={"sanctioned_tags": sanctioned},
            )
        return HeuristicResult()


class RansomwareProceedsLayering(BaseHeuristic):
    id = 179
    name = "RansomwareProceedsLayering"
    environment = ENV
    lens_tags = ["graph", "offramp"]
    description = "Layering proceeds from ransomware payments."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        ransomware = [t for t in tags if t.lower() == "ransomware"]
        if ransomware:
            tainted, score = check_tainted_to_cashout(features, context)
            return HeuristicResult(
                triggered=True,
                confidence=max(0.8, score),
                explanation=f"Ransomware-linked funds being layered; tags {ransomware}.",
                evidence={"ransomware_tags": ransomware, "cashout_score": score},
            )
        return HeuristicResult()


class PigButcheringScamTreasury(BaseHeuristic):
    id = 180
    name = "PigButcheringScamTreasury"
    environment = ENV
    lens_tags = ["graph", "entity", "offramp"]
    description = "Treasury wallets collecting pig-butchering scam proceeds."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        scam = [t for t in tags if t.lower() == "scam"]
        if scam:
            in_triggered, in_deg = check_many_to_one(
                graph, (wallet or {}).get("address", ""), threshold=15
            )
            conf = 0.8
            if in_triggered:
                conf = min(conf + in_deg / 50.0, 1.0)
            return HeuristicResult(
                triggered=True,
                confidence=conf,
                explanation=f"Scam treasury: {in_deg} inbound, tags {scam}.",
                evidence={"scam_tags": scam, "in_degree": in_deg},
            )
        return HeuristicResult()


class DarknetMarketplaceSettlement(BaseHeuristic):
    id = 181
    name = "DarknetMarketplaceSettlement"
    environment = ENV
    lens_tags = ["graph", "offramp"]
    description = "Settlement flows from darknet marketplace escrows."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        darknet = [t for t in tags if t.lower() == "darknet"]
        if darknet:
            return HeuristicResult(
                triggered=True,
                confidence=0.85,
                explanation=f"Darknet marketplace exposure: {darknet}.",
                evidence={"darknet_tags": darknet},
            )
        return HeuristicResult()


class CSAMPaymentLaundering(BaseHeuristic):
    id = 182
    name = "CSAMPaymentLaundering"
    environment = ENV
    lens_tags = ["graph"]
    description = "Payment flows linked to child sexual abuse material distribution."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        ctx = context or {}
        csam_flag = ctx.get("csam_flagged", False)
        if csam_flag:
            return HeuristicResult(
                triggered=True,
                confidence=0.95,
                explanation="Address flagged for CSAM-related payment flows.",
                evidence={"csam_flagged": True},
            )
        return HeuristicResult()


class FraudRingSettlementTokenTransfers(BaseHeuristic):
    id = 183
    name = "FraudRingSettlementTokenTransfers"
    environment = ENV
    lens_tags = ["graph", "entity", "offramp"]
    description = "Token transfer patterns consistent with organised fraud ring settlement."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        triggered, n_cycles = check_circular_flows(graph, wallet["address"], max_length=5)
        mule_flag, pt_ratio = check_mule_patterns(wallet, features)
        if triggered and mule_flag:
            return HeuristicResult(
                triggered=True,
                confidence=min(0.7 + n_cycles * 0.1, 1.0),
                explanation=f"Fraud ring: {n_cycles} cycles, pass-through {pt_ratio:.2f}.",
                evidence={"cycle_count": n_cycles, "pass_through_ratio": pt_ratio},
            )
        return HeuristicResult()


class TerrorFinanceMicroTransferWebs(BaseHeuristic):
    id = 184
    name = "TerrorFinanceMicroTransferWebs"
    environment = ENV
    lens_tags = ["graph", "temporal", "entity"]
    description = "Web of micro-transfers funding terrorism-related activities."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        no_rationale, score = check_no_economic_rationale(features)
        if risk_flag and no_rationale:
            return HeuristicResult(
                triggered=True,
                confidence=min(score + 0.3, 1.0),
                explanation=f"Micro-transfer web with high-risk tags {tags}, no-rationale score {score:.2f}.",
                evidence={"risk_tags": tags, "no_rationale_score": score},
            )
        return HeuristicResult()


class HumanTraffickingRemittanceLaundering(BaseHeuristic):
    id = 185
    name = "HumanTraffickingRemittanceLaundering"
    environment = ENV
    lens_tags = ["graph", "offramp", "entity"]
    description = "Remittance patterns consistent with human trafficking proceeds laundering."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        mule_flag, pt_ratio = check_mule_patterns(wallet, features)
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        if mule_flag:
            conf = min(pt_ratio, 1.0)
            if risk_flag:
                conf = min(conf + 0.2, 1.0)
            return HeuristicResult(
                triggered=True,
                confidence=conf,
                explanation=f"Remittance mule pattern: pass-through {pt_ratio:.2f}, tags {tags}.",
                evidence={"pass_through_ratio": pt_ratio, "risk_tags": tags},
            )
        return HeuristicResult()


# ===================================================================
# Stubs requiring off-chain data
# ===================================================================

_STUB_DEFS: list[tuple[int, str, list[str], str, list[str]]] = [
    (143, "KYCBorrowedAccountCashout", ["entity", "offramp"],
     "Cashing out using a borrowed or purchased KYC-verified account.", ["kyc_data"]),
    (145, "CryptoATMCashout", ["offramp", "temporal"],
     "Converting crypto to cash via crypto ATMs.", ["atm_data"]),
    (146, "PrepaidDebitOfframp", ["offramp"],
     "Off-ramping crypto to prepaid debit cards.", ["card_data"]),
    (147, "MerchantProcessorOfframp", ["offramp", "document"],
     "Off-ramping through complicit merchant payment processors.", ["merchant_data"]),
    (148, "OTCSettlementTradeInvoices", ["offramp", "document"],
     "Settling OTC trades with fabricated trade invoices.", ["invoice_data"]),
    (150, "ForeignExchangeHouseCashout", ["offramp"],
     "Cashing out crypto through foreign exchange houses.", ["fex_data"]),
    (151, "PayrollGigCashoutCryptoTreasury", ["offramp", "entity"],
     "Disbursing crypto treasury via fake payroll or gig payments.", ["payroll_data"]),
    (152, "InvoiceFinancingOfframp", ["offramp", "document"],
     "Using invoice financing platforms to off-ramp crypto.", ["invoice_data"]),
    (153, "RealEstateDownPaymentExchange", ["offramp", "document"],
     "Converting crypto to real estate down payments.", ["property_data"]),
    (154, "LuxuryDealerCryptoAcceptance", ["offramp"],
     "Purchasing luxury goods from dealers accepting crypto.", ["dealer_data"]),
    (155, "CharityNGOCryptoDonation", ["offramp", "entity"],
     "Donating crypto to charities/NGOs as a laundering step.", ["ngo_data"]),
    (177, "MerchantTradeSettlementCrypto", ["offramp", "document"],
     "Using crypto for merchant trade settlement to obscure funds.", ["trade_data"]),
    (178, "StateProxyExchangeNetworks", ["entity", "graph"],
     "State-proxy exchange networks evading sanctions.", ["sanctions_data"]),
]

# ===================================================================
# IDs with dedicated class implementations
# ===================================================================
_IMPLEMENTED_IDS = {144, 149, 176, 179, 180, 181, 182, 183, 184, 185}

# ===================================================================
# Instantiate
# ===================================================================

_instances: list[BaseHeuristic] = [
    P2PExchangeLaundering(),
    CrossBorderExchangeArbitrage(),
    SanctionsEvasionStablecoinCorridor(),
    RansomwareProceedsLayering(),
    PigButcheringScamTreasury(),
    DarknetMarketplaceSettlement(),
    CSAMPaymentLaundering(),
    FraudRingSettlementTokenTransfers(),
    TerrorFinanceMicroTransferWebs(),
    HumanTraffickingRemittanceLaundering(),
]

for _hid, _name, _tags, _desc, _reqs in _STUB_DEFS:
    assert _hid not in _IMPLEMENTED_IDS, f"Stub {_hid} clashes with implemented class"
    _instances.append(_stub(_hid, _name, _tags, _desc, _reqs))

# ===================================================================
# Register all 23 hybrid heuristics
# ===================================================================
from app.ml.heuristics.registry import register as _register

for _h in _instances:
    _register(_h)
