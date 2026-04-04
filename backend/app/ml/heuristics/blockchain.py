"""Blockchain-native AML heuristics (IDs 91-142)."""
from __future__ import annotations

from typing import Any, Optional

from app.ml.heuristics.base import (
    BaseHeuristic,
    HeuristicResult,
    Applicability,
    Environment,
)
from app.ml.heuristics.common_red_flags import (
    check_many_to_one,
    check_one_to_many,
    check_new_entity_high_value,
    check_circular_flows,
    check_high_risk_counterparty,
    check_mule_patterns,
    check_sub_threshold_fragmentation,
    check_no_economic_rationale,
)

ENV = Environment.BLOCKCHAIN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_get(d: Optional[dict], *keys, default=None):
    """Nested dict get."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur


def _stub(_hid: int, _name: str, _tags: list[str], _desc: str, _reqs: list[str] | None = None):
    _reqs = _reqs or []

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
# Real implementations (IDs 91-100)
# ===================================================================

class PeelChain(BaseHeuristic):
    id = 91
    name = "PeelChain"
    environment = ENV
    lens_tags = ["graph", "temporal", "behavioral"]
    description = "Sequential transfers with decreasing residual balance — classic peel chain."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        addr = wallet["address"]
        if not graph.has_node(addr):
            return HeuristicResult()
        successors = list(graph.successors(addr))
        if len(successors) < 3:
            return HeuristicResult()
        edges = []
        for s in successors:
            data = graph.get_edge_data(addr, s)
            if data:
                amt = data.get("amount", data.get("value", 0))
                ts = data.get("timestamp", data.get("block_number", 0))
                edges.append((ts, amt))
        edges.sort(key=lambda x: x[0])
        if len(edges) < 3:
            return HeuristicResult()
        decreasing = sum(
            1 for i in range(1, len(edges)) if edges[i][1] < edges[i - 1][1]
        )
        ratio = decreasing / (len(edges) - 1)
        triggered = ratio > 0.7 and len(edges) >= 3
        return HeuristicResult(
            triggered=triggered,
            confidence=min(ratio, 1.0) if triggered else 0.0,
            explanation=f"Peel chain: {decreasing}/{len(edges)-1} sequential decreasing outputs." if triggered else "",
            evidence={"chain_length": len(edges), "decreasing_ratio": ratio},
        )


class FanOutDispersal(BaseHeuristic):
    id = 92
    name = "FanOutDispersal"
    environment = ENV
    lens_tags = ["graph", "temporal"]
    description = "High out-degree burst from a single node dispersing funds."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        triggered, out_deg = check_one_to_many(graph, wallet["address"], threshold=10)
        if not triggered and features:
            out_deg = features.get("out_degree", 0)
            triggered = out_deg >= 10
        if triggered:
            return HeuristicResult(
                triggered=True,
                confidence=min(out_deg / 30.0, 1.0),
                explanation=f"Fan-out burst: {out_deg} recipients.",
                evidence={"out_degree": out_deg},
            )
        return HeuristicResult()


class FanInAggregation(BaseHeuristic):
    id = 93
    name = "FanInAggregation"
    environment = ENV
    lens_tags = ["graph", "temporal"]
    description = "High in-degree to a single node aggregating funds."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        triggered, in_deg = check_many_to_one(graph, wallet["address"], threshold=10)
        if not triggered and features:
            in_deg = features.get("in_degree", 0)
            triggered = in_deg >= 10
        if triggered:
            return HeuristicResult(
                triggered=True,
                confidence=min(in_deg / 30.0, 1.0),
                explanation=f"Fan-in aggregation: {in_deg} senders.",
                evidence={"in_degree": in_deg},
            )
        return HeuristicResult()


class LayeredHopsFreshWallets(BaseHeuristic):
    id = 94
    name = "LayeredHopsFreshWallets"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Young/single-use addresses in multi-hop layering chains."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        triggered, info = check_new_entity_high_value(wallet, threshold_days=7, threshold_amount=1000.0)
        if triggered:
            pt_flag, pt_ratio = check_mule_patterns(wallet, features)
            conf = 0.6
            if pt_flag:
                conf = min(conf + 0.3, 1.0)
            return HeuristicResult(
                triggered=True,
                confidence=conf,
                explanation=f"Fresh wallet ({info.get('age_days', '?')}d old) with {info.get('total_volume', 0):.0f} volume.",
                evidence={**info, "pass_through": pt_ratio if pt_flag else None},
            )
        return HeuristicResult()


class DustingMixedInflows(BaseHeuristic):
    id = 95
    name = "DustingMixedInflows"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Many small (dust) inputs mixed with larger transfers to obscure provenance."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        inflows = features.get("inflow_amounts", [])
        if not inflows or len(inflows) < 5:
            return HeuristicResult()
        dust_threshold = features.get("dust_threshold", 0.001)
        dust_count = sum(1 for a in inflows if a <= dust_threshold)
        ratio = dust_count / len(inflows)
        triggered = ratio > 0.5 and dust_count >= 5
        return HeuristicResult(
            triggered=triggered,
            confidence=min(ratio, 1.0) if triggered else 0.0,
            explanation=f"Dusting: {dust_count}/{len(inflows)} dust-sized inputs." if triggered else "",
            evidence={"dust_count": dust_count, "total_inflows": len(inflows), "dust_ratio": ratio},
        )


class SelfTransferChain(BaseHeuristic):
    id = 96
    name = "SelfTransferChain"
    environment = ENV
    lens_tags = ["entity", "graph"]
    description = "Transfers between addresses controlled by the same entity."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        addr = wallet["address"]
        cluster = (context or {}).get("address_cluster", set())
        if not cluster:
            return HeuristicResult()
        if not graph.has_node(addr):
            return HeuristicResult()
        self_edges = 0
        for succ in graph.successors(addr):
            if succ in cluster:
                self_edges += 1
        for pred in graph.predecessors(addr):
            if pred in cluster:
                self_edges += 1
        triggered = self_edges >= 3
        return HeuristicResult(
            triggered=triggered,
            confidence=min(self_edges / 10.0, 1.0) if triggered else 0.0,
            explanation=f"Self-transfer chain: {self_edges} edges within same entity cluster." if triggered else "",
            evidence={"self_edges": self_edges, "cluster_size": len(cluster)},
        )


class AddressHoppingBlacklists(BaseHeuristic):
    id = 97
    name = "AddressHoppingBlacklists"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Rapidly rotating to novel addresses to avoid blacklisting."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        unique_addrs = features.get("unique_recipient_addresses_24h", 0)
        new_addr_ratio = features.get("new_address_ratio", 0)
        triggered = unique_addrs >= 10 and new_addr_ratio > 0.8
        conf = min(new_addr_ratio * (unique_addrs / 20.0), 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"{unique_addrs} unique recipients, {new_addr_ratio:.0%} new." if triggered else "",
            evidence={"unique_recipients_24h": unique_addrs, "new_address_ratio": new_addr_ratio},
        )


class TimeDelayLayering(BaseHeuristic):
    id = 98
    name = "TimeDelayLayering"
    environment = ENV
    lens_tags = ["temporal", "behavioral"]
    description = "Consistent time gaps between hops suggesting automated layering."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        intervals = features.get("outflow_intervals_seconds", [])
        if len(intervals) < 3:
            return HeuristicResult()
        import numpy as np
        mean_iv = np.mean(intervals)
        if mean_iv == 0:
            return HeuristicResult()
        cv = np.std(intervals) / mean_iv
        triggered = cv < 0.2 and len(intervals) >= 3
        return HeuristicResult(
            triggered=triggered,
            confidence=max(1.0 - cv, 0.0) if triggered else 0.0,
            explanation=f"Uniform interval layering: CV={cv:.3f} across {len(intervals)} hops." if triggered else "",
            evidence={"coefficient_of_variation": cv, "mean_interval_s": mean_iv, "hop_count": len(intervals)},
        )


class MicroSplittingThresholds(BaseHeuristic):
    id = 99
    name = "MicroSplittingThresholds"
    environment = ENV
    lens_tags = ["behavioral", "temporal"]
    description = "Amounts clustered just below reporting thresholds."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        amounts = []
        if features:
            amounts = features.get("recent_amounts", [])
        if not amounts and context:
            raw = (context or {}).get("amount", [])
            amounts = raw if isinstance(raw, list) else [raw]
        if not amounts:
            return HeuristicResult()
        triggered, ratio = check_sub_threshold_fragmentation(amounts, threshold=10000.0)
        return HeuristicResult(
            triggered=triggered,
            confidence=min(ratio, 1.0) if triggered else 0.0,
            explanation=f"Near-threshold clustering ratio {ratio:.2f}." if triggered else "",
            evidence={"ratio": ratio},
        )


class ConsolidationAfterObfuscation(BaseHeuristic):
    id = 100
    name = "ConsolidationAfterObfuscation"
    environment = ENV
    lens_tags = ["graph"]
    description = "Many relay hops converge to a single consolidation address."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        addr = wallet["address"]
        triggered, in_deg = check_many_to_one(graph, addr, threshold=8)
        if not triggered:
            return HeuristicResult()
        predecessors_ages = []
        for pred in graph.predecessors(addr):
            pred_data = graph.nodes.get(pred, {})
            age = pred_data.get("age_days", None)
            if age is not None:
                predecessors_ages.append(age)
        young = sum(1 for a in predecessors_ages if a < 7) if predecessors_ages else 0
        young_ratio = young / max(len(predecessors_ages), 1)
        conf = min((in_deg / 20.0) + young_ratio * 0.3, 1.0)
        triggered = in_deg >= 8 and (young_ratio > 0.5 or in_deg >= 15)
        return HeuristicResult(
            triggered=triggered,
            confidence=conf if triggered else 0.0,
            explanation=f"Consolidation: {in_deg} inbound, {young_ratio:.0%} from young wallets." if triggered else "",
            evidence={"in_degree": in_deg, "young_predecessor_ratio": young_ratio},
        )


# ===================================================================
# IDs 101-142: partial logic or stubs
# ===================================================================

class ChangeAddressAbuse(BaseHeuristic):
    id = 101
    name = "ChangeAddressAbuse"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Exploiting UTXO change addresses to obscure fund flow."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        change_ratio = features.get("change_address_reuse_ratio", 0)
        triggered = change_ratio > 0.7
        return HeuristicResult(
            triggered=triggered,
            confidence=min(change_ratio, 1.0) if triggered else 0.0,
            explanation=f"Change address reuse ratio {change_ratio:.2f}." if triggered else "",
            evidence={"change_address_reuse_ratio": change_ratio},
        )


class CoinJoinParticipation(BaseHeuristic):
    id = 102
    name = "CoinJoinParticipation"
    environment = ENV
    lens_tags = ["graph", "entity"]
    description = "Participation in CoinJoin transactions to mix funds."
    data_requirements = ["coinjoin_data"]

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        appl = self.check_data_requirements(context)
        if appl != Applicability.APPLICABLE:
            if features and features.get("coinjoin_tx_count", 0) > 0:
                count = features["coinjoin_tx_count"]
                return HeuristicResult(
                    triggered=count >= 2,
                    confidence=min(count / 5.0, 1.0),
                    explanation=f"Participated in {count} CoinJoin transactions.",
                    evidence={"coinjoin_tx_count": count},
                )
            return HeuristicResult(applicability=appl)
        return HeuristicResult()


class CrossWalletChainLoops(BaseHeuristic):
    id = 105
    name = "CrossWalletChainLoops"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Circular flows across multiple wallets and chains."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is None or not wallet or not wallet.get("address"):
            return HeuristicResult()
        triggered, n_cycles = check_circular_flows(graph, wallet["address"], max_length=6)
        if triggered:
            return HeuristicResult(
                triggered=True,
                confidence=min(n_cycles / 5.0, 1.0),
                explanation=f"Cross-wallet loops: {n_cycles} cycle(s) detected.",
                evidence={"cycle_count": n_cycles},
            )
        return HeuristicResult()


class NFTWashSaleLaundering(BaseHeuristic):
    id = 132
    name = "NFTWashSaleLaundering"
    environment = ENV
    lens_tags = ["behavioral", "entity", "offramp"]
    description = "Wash trading NFTs between controlled wallets to create false sale history."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        wash_score = features.get("nft_wash_trade_score", 0)
        self_trades = features.get("nft_self_trade_count", 0)
        triggered = wash_score > 0.6 or self_trades >= 3
        conf = max(wash_score, min(self_trades / 5.0, 1.0)) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"NFT wash sale: score={wash_score:.2f}, self-trades={self_trades}." if triggered else "",
            evidence={"wash_score": wash_score, "self_trade_count": self_trades},
        )


class NFTRoyaltyRecycling(BaseHeuristic):
    id = 133
    name = "NFTRoyaltyRecycling"
    environment = ENV
    lens_tags = ["behavioral", "entity"]
    description = "Artificially generating NFT royalty payments through self-dealing."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        royalty_self_ratio = features.get("nft_royalty_self_ratio", 0)
        triggered = royalty_self_ratio > 0.5
        return HeuristicResult(
            triggered=triggered,
            confidence=min(royalty_self_ratio, 1.0) if triggered else 0.0,
            explanation=f"Royalty self-dealing ratio {royalty_self_ratio:.2f}." if triggered else "",
            evidence={"royalty_self_ratio": royalty_self_ratio},
        )


class LowLiquidityTokenPumping(BaseHeuristic):
    id = 134
    name = "LowLiquidityTokenPumping"
    environment = ENV
    lens_tags = ["behavioral", "graph"]
    description = "Pumping price of low-liquidity token then dumping for laundering."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        pump_score = features.get("token_pump_score", 0)
        triggered = pump_score > 0.6
        return HeuristicResult(
            triggered=triggered,
            confidence=min(pump_score, 1.0) if triggered else 0.0,
            explanation=f"Low-liquidity token pump score {pump_score:.2f}." if triggered else "",
            evidence={"pump_score": pump_score},
        )


class AirdropFarmingDisguise(BaseHeuristic):
    id = 135
    name = "AirdropFarmingDisguise"
    environment = ENV
    lens_tags = ["entity", "graph"]
    description = "Sybil wallets farming airdrops to disguise fund origin."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        sybil_score = features.get("sybil_cluster_score", 0)
        triggered = sybil_score > 0.5
        return HeuristicResult(
            triggered=triggered,
            confidence=min(sybil_score, 1.0) if triggered else 0.0,
            explanation=f"Airdrop farming sybil score {sybil_score:.2f}." if triggered else "",
            evidence={"sybil_score": sybil_score},
        )


class StablecoinMintRedeemCycling(BaseHeuristic):
    id = 136
    name = "StablecoinMintRedeemCycling"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Cycling between minting and redeeming stablecoins to launder funds."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        mint_redeem_count = features.get("stablecoin_mint_redeem_cycles", 0)
        triggered = mint_redeem_count >= 3
        return HeuristicResult(
            triggered=triggered,
            confidence=min(mint_redeem_count / 6.0, 1.0) if triggered else 0.0,
            explanation=f"Stablecoin mint-redeem cycles: {mint_redeem_count}." if triggered else "",
            evidence={"mint_redeem_cycles": mint_redeem_count},
        )


class ExchangeAccountMuleRing(BaseHeuristic):
    id = 141
    name = "ExchangeAccountMuleRing"
    environment = ENV
    lens_tags = ["entity", "offramp"]
    description = "Ring of mule exchange accounts used to cash out."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        triggered, pt_ratio = check_mule_patterns(wallet, features)
        risk_flag, tags = check_high_risk_counterparty(wallet, context)
        if triggered and risk_flag:
            return HeuristicResult(
                triggered=True,
                confidence=min(pt_ratio * 1.2, 1.0),
                explanation=f"Mule ring: pass-through {pt_ratio:.2f}, risky tags {tags}.",
                evidence={"pass_through_ratio": pt_ratio, "risk_tags": tags},
            )
        return HeuristicResult()


class NestedVASPExposure(BaseHeuristic):
    id = 142
    name = "NestedVASPExposure"
    environment = ENV
    lens_tags = ["graph", "offramp"]
    description = "Exposure via nested virtual asset service providers."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if not features:
            return HeuristicResult()
        nested_score = features.get("nested_vasp_exposure_score", 0)
        triggered = nested_score > 0.4
        return HeuristicResult(
            triggered=triggered,
            confidence=min(nested_score, 1.0) if triggered else 0.0,
            explanation=f"Nested VASP exposure score {nested_score:.2f}." if triggered else "",
            evidence={"nested_vasp_score": nested_score},
        )


# ===================================================================
# Remaining stubs (103-131, 137-140 that need specific protocol data)
# ===================================================================

_STUB_DEFS: list[tuple[int, str, list[str], str, list[str]]] = [
    (103, "CentralizedMixerUse", ["graph", "offramp"],
     "Routing funds through centralized mixing services.", ["mixer_data"]),
    (104, "DecentralizedMixingPools", ["graph"],
     "Using decentralized mixing protocols (e.g., Tornado Cash).", ["mixing_pool_data"]),
    (106, "OTCBrokerLayering", ["graph", "offramp"],
     "Layering through OTC brokers to exit blockchain.", ["otc_data"]),
    (107, "BridgeHopObfuscation", ["graph", "offramp"],
     "Hopping across bridges to obscure origin chain.", ["bridge_data"]),
    (108, "CrossChainSwapHops", ["graph"],
     "Multiple cross-chain swaps to layer funds.", ["swap_data"]),
    (109, "StablecoinWrapping", ["graph", "behavioral"],
     "Wrapping and unwrapping stablecoins to break tracing.", []),
    (110, "GasSponsorshipDistancing", ["entity", "graph"],
     "Using gas sponsorship (meta-transactions) to decouple sender.", []),
    (111, "PrivacyCoinConversion", ["graph", "offramp"],
     "Converting to privacy coins (Monero, Zcash) for obfuscation.", ["privacy_coin_data"]),
    (112, "ShieldedPoolEntryExit", ["graph"],
     "Entering and exiting shielded transaction pools.", ["shielded_pool_data"]),
    (113, "AnonymityWalletRouting", ["graph"],
     "Routing through wallets designed for anonymity.", ["wallet_type_data"]),
    (114, "StealthAddressCycling", ["graph", "entity"],
     "Generating new stealth addresses per transaction.", ["stealth_data"]),
    (115, "RingSignatureLaundering", ["graph"],
     "Exploiting ring signatures to hide true sender.", ["ring_sig_data"]),
    (116, "SwapInOutPrivacyAssets", ["graph", "offramp"],
     "Swapping in and out of privacy-focused assets.", ["swap_data"]),
    (117, "AtomicSwapPrivacyHop", ["graph"],
     "Atomic swaps to privacy chains.", ["atomic_swap_data"]),
    (118, "MixToBridgeSequence", ["graph", "offramp"],
     "Mixer followed by immediate bridge hop.", ["mixer_data", "bridge_data"]),
    (119, "WalletClusterFragmentation", ["entity", "graph"],
     "Deliberately fragmenting wallet cluster to evade clustering.", []),
    (120, "TokenizedGiftCardCashout", ["offramp", "behavioral"],
     "Cashing out via tokenized gift cards.", ["gift_card_data"]),
    (121, "DEXWashPathing", ["graph", "behavioral"],
     "Wash trading on DEXes to create artificial volume.", ["dex_data"]),
    (122, "DEXAggregatorChurn", ["graph"],
     "Churning through DEX aggregators to split and reassemble.", ["dex_data"]),
    (123, "LiquidityPoolParking", ["graph", "behavioral"],
     "Parking funds in liquidity pools temporarily.", ["defi_data"]),
    (124, "FlashLoanCamouflage", ["graph", "behavioral"],
     "Using flash loans to temporarily inflate balances or volumes.", ["defi_data"]),
    (125, "MEVBundleShielding", ["graph"],
     "Using MEV bundles to hide transaction ordering.", ["mev_data"]),
    (126, "YieldFarmLaundering", ["graph", "behavioral"],
     "Cycling funds through yield farms to obscure origin.", ["defi_data"]),
    (127, "LendingProtocolBorrowLoop", ["graph", "behavioral"],
     "Deposit-borrow-repay loops across lending protocols.", ["defi_data"]),
    (128, "LiquidationEventMasking", ["graph"],
     "Engineering liquidation events to move funds.", ["defi_data"]),
    (129, "BridgeAndDEXDaisyChain", ["graph", "offramp"],
     "Alternating bridge and DEX hops in sequence.", ["bridge_data", "dex_data"]),
    (130, "CrossChainRouterAbuse", ["graph"],
     "Exploiting cross-chain routers for multi-hop obfuscation.", ["router_data"]),
    (131, "GovernanceTokenFlipping", ["graph", "behavioral"],
     "Using governance token transactions to disguise transfers.", []),
    (137, "Layer2InOutHopping", ["graph"],
     "Hopping between L1 and L2 to fragment trail.", ["l2_data"]),
    (138, "CrossProtocolCollateralRelay", ["graph", "behavioral"],
     "Moving collateral across DeFi protocols to obfuscate.", ["defi_data"]),
    (139, "DAOTreasuryAbuse", ["graph", "entity"],
     "Misusing DAO treasury proposals to extract funds.", ["dao_data"]),
    (140, "OnChainGameAssetLaundering", ["behavioral", "graph"],
     "Laundering through on-chain gaming asset trades.", ["gaming_data"]),
]

# ===================================================================
# IDs with dedicated class implementations
# ===================================================================
_IMPLEMENTED_IDS = {91, 92, 93, 94, 95, 96, 97, 98, 99, 100,
                    101, 102, 105, 132, 133, 134, 135, 136, 141, 142}

# ===================================================================
# Instantiate
# ===================================================================

_instances: list[BaseHeuristic] = [
    PeelChain(),
    FanOutDispersal(),
    FanInAggregation(),
    LayeredHopsFreshWallets(),
    DustingMixedInflows(),
    SelfTransferChain(),
    AddressHoppingBlacklists(),
    TimeDelayLayering(),
    MicroSplittingThresholds(),
    ConsolidationAfterObfuscation(),
    ChangeAddressAbuse(),
    CoinJoinParticipation(),
    CrossWalletChainLoops(),
    NFTWashSaleLaundering(),
    NFTRoyaltyRecycling(),
    LowLiquidityTokenPumping(),
    AirdropFarmingDisguise(),
    StablecoinMintRedeemCycling(),
    ExchangeAccountMuleRing(),
    NestedVASPExposure(),
]

for _hid, _name, _tags, _desc, _reqs in _STUB_DEFS:
    assert _hid not in _IMPLEMENTED_IDS, f"Stub {_hid} clashes with implemented class"
    _instances.append(_stub(_hid, _name, _tags, _desc, _reqs))

# ===================================================================
# Register all 52 blockchain heuristics
# ===================================================================
from app.ml.heuristics.registry import register as _register

for _h in _instances:
    _register(_h)
