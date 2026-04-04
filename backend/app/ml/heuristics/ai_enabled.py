"""AI-enabled AML heuristics (IDs 156-175)."""
from __future__ import annotations

from typing import Any, Optional

import numpy as np

from app.ml.heuristics.base import (
    BaseHeuristic,
    HeuristicResult,
    Applicability,
    Environment,
)
from app.ml.heuristics.common_red_flags import (
    check_circular_flows,
    check_many_to_one,
    check_one_to_many,
    check_no_economic_rationale,
    check_sub_threshold_fragmentation,
)

ENV = Environment.AI_ENABLED


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
# Real implementations (temporal/graph/behavioral)
# ===================================================================

class AutomatedTransactionScheduling(BaseHeuristic):
    id = 161
    name = "AutomatedTransactionScheduling"
    environment = ENV
    lens_tags = ["temporal", "behavioral"]
    description = "Clockwork-precise transaction timing suggesting bot-driven scheduling."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        intervals = features.get("outflow_intervals_seconds", [])
        if len(intervals) < 5:
            return HeuristicResult()
        mean_iv = np.mean(intervals)
        if mean_iv == 0:
            return HeuristicResult()
        cv = np.std(intervals) / mean_iv
        triggered = cv < 0.05 and len(intervals) >= 5
        return HeuristicResult(
            triggered=triggered,
            confidence=max(1.0 - cv * 10, 0.0) if triggered else 0.0,
            explanation=f"Clockwork scheduling: CV={cv:.4f} over {len(intervals)} intervals." if triggered else "",
            evidence={"cv": cv, "mean_interval_s": mean_iv, "interval_count": len(intervals)},
        )


class ReinforcementLearnedThresholdAvoidance(BaseHeuristic):
    id = 162
    name = "ReinforcementLearnedThresholdAvoidance"
    environment = ENV
    lens_tags = ["temporal", "behavioral"]
    description = "Dynamically adjusted amounts that cluster near but adapt around thresholds."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        amounts = []
        if features:
            amounts = features.get("recent_amounts", [])
        if not amounts:
            return HeuristicResult()

        thresholds = [1000, 3000, 10000, 15000, 50000]
        best_cluster = 0.0
        for t in thresholds:
            band = [a for a in amounts if 0.8 * t <= a < t]
            ratio = len(band) / max(len(amounts), 1)
            if ratio > best_cluster:
                best_cluster = ratio

        var = np.var(amounts) if len(amounts) > 1 else 0
        mean_a = np.mean(amounts) if amounts else 1
        norm_var = var / (mean_a ** 2) if mean_a else 0
        adaptive = best_cluster > 0.4 and norm_var > 0.01

        triggered = adaptive and best_cluster > 0.4
        conf = min(best_cluster * 1.5, 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Dynamic threshold avoidance: cluster ratio {best_cluster:.2f}, variance {norm_var:.4f}." if triggered else "",
            evidence={"cluster_ratio": best_cluster, "normalized_variance": norm_var},
        )


class GraphAwareRouteOptimization(BaseHeuristic):
    id = 163
    name = "GraphAwareRouteOptimization"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Routing that avoids monitored/screened clusters, suggesting graph-aware adversary."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        addr = wallet["address"]
        if not graph.has_node(addr):
            return HeuristicResult()
        screened = (context or {}).get("screened_nodes", set())
        if not screened:
            return HeuristicResult()

        neighbors = set(graph.successors(addr)) | set(graph.predecessors(addr))
        overlap = neighbors & screened
        avoidance_ratio = 1.0 - (len(overlap) / max(len(neighbors), 1))
        path_length = features.get("avg_path_length_to_exchange", 0) if features else 0
        triggered = avoidance_ratio > 0.95 and len(neighbors) >= 5 and path_length > 4
        conf = min(avoidance_ratio, 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Graph-aware routing: {avoidance_ratio:.2%} avoidance of screened nodes, path length {path_length}." if triggered else "",
            evidence={"avoidance_ratio": avoidance_ratio, "neighbor_count": len(neighbors), "path_length": path_length},
        )


class BotnetWalletOrchestration(BaseHeuristic):
    id = 164
    name = "BotnetWalletOrchestration"
    environment = ENV
    lens_tags = ["entity", "temporal", "graph"]
    description = "Synchronized wallet activity across many addresses suggesting botnet control."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        sync_score = features.get("temporal_sync_score", 0)
        cluster_size = features.get("synchronized_cluster_size", 0)
        triggered = sync_score > 0.7 and cluster_size >= 5
        conf = min(sync_score * (cluster_size / 10.0), 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Botnet orchestration: sync={sync_score:.2f}, cluster={cluster_size}." if triggered else "",
            evidence={"sync_score": sync_score, "cluster_size": cluster_size},
        )


class AutonomousCrossChainExecution(BaseHeuristic):
    id = 165
    name = "AutonomousCrossChainExecution"
    environment = ENV
    lens_tags = ["graph", "temporal"]
    description = "Multi-step cross-chain execution with inhuman latency between hops."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        hop_latencies = features.get("cross_chain_hop_latencies_s", [])
        if len(hop_latencies) < 2:
            return HeuristicResult()
        min_latency = min(hop_latencies)
        mean_latency = np.mean(hop_latencies)
        inhuman = min_latency < 5 and mean_latency < 30
        chain_count = features.get("chains_touched", 1)
        triggered = inhuman and chain_count >= 2
        conf = min((1.0 / max(mean_latency, 0.1)) * 5 * (chain_count / 3.0), 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Autonomous cross-chain: min latency {min_latency:.1f}s, {chain_count} chains." if triggered else "",
            evidence={"min_latency_s": min_latency, "mean_latency_s": mean_latency, "chains_touched": chain_count},
        )


class AdversarialBehaviorAgainstAMLModels(BaseHeuristic):
    id = 172
    name = "AdversarialBehaviorAgainstAMLModels"
    environment = ENV
    lens_tags = ["behavioral", "temporal"]
    description = "Behavior that shifts specifically after AML review, suggesting adversarial adaptation."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        pre_review_score = features.get("pre_review_risk_score", 0)
        post_review_score = features.get("post_review_risk_score", 0)
        behavior_shift = features.get("behavior_shift_after_review", 0)
        drift = abs(pre_review_score - post_review_score)
        triggered = drift > 0.3 and behavior_shift > 0.5
        conf = min(drift + behavior_shift * 0.5, 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Adversarial drift: risk delta {drift:.2f}, behavior shift {behavior_shift:.2f}." if triggered else "",
            evidence={"risk_score_drift": drift, "behavior_shift": behavior_shift},
        )


class MultiAgentLaunderingWorkflow(BaseHeuristic):
    id = 175
    name = "MultiAgentLaunderingWorkflow"
    environment = ENV
    lens_tags = ["graph", "entity", "temporal"]
    description = "Distributed coordination across multiple agents executing laundering steps."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        sync_score = features.get("temporal_sync_score", 0)
        unique_roles = features.get("unique_role_count", 0)
        no_rationale, nr_score = check_no_economic_rationale(features)

        triggered = sync_score > 0.5 and unique_roles >= 3 and no_rationale
        conf = min(sync_score * 0.4 + (unique_roles / 6.0) * 0.3 + nr_score * 0.3, 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Multi-agent workflow: sync={sync_score:.2f}, roles={unique_roles}, no-rationale={nr_score:.2f}." if triggered else "",
            evidence={"sync_score": sync_score, "unique_roles": unique_roles, "no_rationale_score": nr_score},
        )


# ===================================================================
# Stubs requiring off-chain data
# ===================================================================

_STUB_DEFS: list[tuple[int, str, list[str], str, list[str]]] = [
    (156, "SyntheticIdentityAccountOpening", ["entity", "document"],
     "Opening accounts with AI-generated synthetic identities.", ["kyc_data"]),
    (157, "DeepfakeKYCInterviews", ["entity", "document"],
     "Passing KYC video interviews using deepfake technology.", ["biometric_data"]),
    (158, "MassMuleRecruitmentGenAI", ["entity"],
     "AI-generated mass recruitment campaigns for money mules.", ["outreach_data"]),
    (159, "AIGeneratedShellWebsites", ["entity", "document"],
     "AI-generated websites for fictitious shell companies.", ["domain_data"]),
    (160, "AIWrittenInvoicesContracts", ["document"],
     "AI-authored invoices and contracts for fictitious transactions.", ["document_metadata"]),
    (166, "AICustomerServiceSocialEngineering", ["entity"],
     "AI chatbot social engineering to authorise fraudulent transfers.", ["support_data"]),
    (167, "VoiceCloningPaymentApproval", ["entity"],
     "Voice-cloned calls to approve payments or transfers.", ["voice_data"]),
    (168, "DocumentLaunderingImageModels", ["document"],
     "AI image models forging or altering financial documents.", ["document_metadata"]),
    (169, "AutomatedAccountRecoveryTakeover", ["entity", "temporal"],
     "Automated account recovery exploits to take over accounts.", ["auth_data"]),
    (170, "AIPersonalizedMuleCoaching", ["entity"],
     "AI-personalized coaching scripts for money mule recruits.", ["comm_data"]),
    (171, "SyntheticBeneficialOwnerNarratives", ["document", "entity"],
     "AI-generated beneficial ownership narratives for shell structures.", ["narrative_data"]),
    (173, "AIGeneratedScamFronts", ["entity", "graph"],
     "AI-created scam front-ends (fake investment platforms, etc.).", ["scam_data"]),
    (174, "AutonomousOTCNegotiationBots", ["offramp", "temporal"],
     "Autonomous bots negotiating OTC crypto trades.", ["otc_data"]),
]

# ===================================================================
# IDs with dedicated class implementations
# ===================================================================
_IMPLEMENTED_IDS = {161, 162, 163, 164, 165, 172, 175}

# ===================================================================
# Instantiate
# ===================================================================

_instances: list[BaseHeuristic] = [
    AutomatedTransactionScheduling(),
    ReinforcementLearnedThresholdAvoidance(),
    GraphAwareRouteOptimization(),
    BotnetWalletOrchestration(),
    AutonomousCrossChainExecution(),
    AdversarialBehaviorAgainstAMLModels(),
    MultiAgentLaunderingWorkflow(),
]

for _hid, _name, _tags, _desc, _reqs in _STUB_DEFS:
    assert _hid not in _IMPLEMENTED_IDS, f"Stub {_hid} clashes with implemented class"
    _instances.append(_stub(_hid, _name, _tags, _desc, _reqs))

# ===================================================================
# Register all 20 AI-enabled heuristics
# ===================================================================
from app.ml.heuristics.registry import register as _register

for _h in _instances:
    _register(_h)
