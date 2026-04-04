"""Traditional financial-sector AML heuristics (IDs 1-90)."""
from __future__ import annotations

from typing import Any, Optional

from app.ml.heuristics.base import (
    BaseHeuristic,
    HeuristicResult,
    Applicability,
    Environment,
)
from app.ml.heuristics.common_red_flags import (
    check_sub_threshold_fragmentation,
    check_rapid_movement_low_balance,
    check_many_to_one,
    check_one_to_many,
    check_mule_patterns,
    check_new_entity_high_value,
    check_circular_flows,
)

ENV = Environment.TRADITIONAL


# ---------------------------------------------------------------------------
# Factory for stub heuristics that require off-chain data
# ---------------------------------------------------------------------------

def _create_stub(_hid: int, _name: str, _tags: list[str], _desc: str, _reqs: list[str]):
    """Return an *instance* of a stub heuristic whose evaluate() checks data
    requirements and returns inapplicable when the data is missing."""

    class _Stub(BaseHeuristic):
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

    _Stub.__name__ = _Stub.__qualname__ = f"H{_hid}_{_name.replace(' ', '')}"
    return _Stub()


# ===================================================================
# Heuristics with real (on-chain-analog) detection logic
# ===================================================================

class CashStructuring(BaseHeuristic):
    id = 1
    name = "CashStructuring"
    environment = ENV
    lens_tags = ["behavioral", "temporal"]
    description = "Repeated sub-threshold transfers designed to evade reporting limits."
    data_requirements = ["amount", "timestamp"]

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        amounts = (context or {}).get("amount", [])
        if not isinstance(amounts, list):
            amounts = [amounts]
        triggered, ratio = check_sub_threshold_fragmentation(amounts, threshold=10000.0)
        conf = min(ratio, 1.0) if triggered else 0.0
        return HeuristicResult(
            triggered=triggered,
            confidence=conf,
            explanation=f"Sub-threshold ratio {ratio:.2f}" if triggered else "",
            evidence={"ratio": ratio, "count": len(amounts)},
        )


class MuleDeposits(BaseHeuristic):
    id = 4
    name = "MuleDeposits"
    environment = ENV
    lens_tags = ["behavioral", "entity"]
    description = "Multiple unrelated depositors funnelling into a single account."
    data_requirements = ["deposit_patterns"]

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is not None and wallet and wallet.get("address"):
            triggered, in_deg = check_many_to_one(graph, wallet["address"], threshold=10)
            if triggered:
                return HeuristicResult(
                    triggered=True,
                    confidence=min(in_deg / 20.0, 1.0),
                    explanation=f"Fan-in of {in_deg} unique depositors.",
                    evidence={"in_degree": in_deg},
                )
        appl = self.check_data_requirements(context)
        if appl != Applicability.APPLICABLE:
            return HeuristicResult(applicability=appl)
        return HeuristicResult()


class RoundDollarDeposits(BaseHeuristic):
    id = 5
    name = "RoundDollarDeposits"
    environment = ENV
    lens_tags = ["behavioral"]
    description = "Repeated deposits of round-number amounts suggesting cash structuring."
    data_requirements = ["amount"]

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        amounts = (context or {}).get("amount", [])
        if not isinstance(amounts, list):
            amounts = [amounts]
        if not amounts:
            return HeuristicResult(applicability=Applicability.INAPPLICABLE_MISSING_DATA)
        round_count = sum(1 for a in amounts if a and float(a) % 100 == 0)
        ratio = round_count / len(amounts)
        triggered = ratio > 0.6 and round_count >= 3
        return HeuristicResult(
            triggered=triggered,
            confidence=min(ratio, 1.0) if triggered else 0.0,
            explanation=f"{round_count}/{len(amounts)} round-dollar deposits" if triggered else "",
            evidence={"round_count": round_count, "ratio": ratio},
        )


class RapidCashInWireOut(BaseHeuristic):
    id = 6
    name = "RapidCashInWireOut"
    environment = ENV
    lens_tags = ["behavioral", "temporal"]
    description = "Cash deposited and wired out quickly with near-zero residual balance."
    data_requirements = ["amount", "timestamp"]

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        ctx = context or {}
        volumes = ctx.get("amount", [])
        balances = ctx.get("balances", [])
        if not isinstance(volumes, list):
            volumes = [volumes]
        if not isinstance(balances, list):
            balances = [balances]
        if not volumes or not balances:
            return HeuristicResult(applicability=Applicability.INAPPLICABLE_MISSING_DATA)
        triggered, score = check_rapid_movement_low_balance(volumes, balances)
        return HeuristicResult(
            triggered=triggered,
            confidence=min(score, 1.0) if triggered else 0.0,
            explanation="High throughput with near-zero retained balance" if triggered else "",
            evidence={"flow_score": score},
        )


class LoanBackScheme(BaseHeuristic):
    id = 17
    name = "LoanBackScheme"
    environment = ENV
    lens_tags = ["graph", "entity"]
    description = "Illicit funds lent to self via shell entity to create appearance of legitimate loan."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is not None and wallet and wallet.get("address"):
            triggered, n_cycles = check_circular_flows(graph, wallet["address"], max_length=4)
            if triggered:
                return HeuristicResult(
                    triggered=True,
                    confidence=min(n_cycles / 5.0, 1.0),
                    explanation=f"Detected {n_cycles} circular flow(s) consistent with loan-back scheme.",
                    evidence={"cycle_count": n_cycles},
                )
        return HeuristicResult()


class NestedPersonalAccounts(BaseHeuristic):
    id = 21
    name = "NestedPersonalAccounts"
    environment = ENV
    lens_tags = ["entity", "graph"]
    description = "Personal accounts used to nest sub-accounts for layering."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is not None and wallet and wallet.get("address"):
            addr = wallet["address"]
            triggered_in, in_deg = check_many_to_one(graph, addr, threshold=8)
            triggered_out, out_deg = check_one_to_many(graph, addr, threshold=8)
            if triggered_in and triggered_out:
                score = min((in_deg + out_deg) / 40.0, 1.0)
                return HeuristicResult(
                    triggered=True,
                    confidence=score,
                    explanation=f"High fan-in ({in_deg}) and fan-out ({out_deg}) suggesting nested accounts.",
                    evidence={"in_degree": in_deg, "out_degree": out_deg},
                )
        return HeuristicResult()


class FunnelAccounts(BaseHeuristic):
    id = 22
    name = "FunnelAccounts"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Multiple accounts funnel funds into one collection point."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is not None and wallet and wallet.get("address"):
            triggered, in_deg = check_many_to_one(graph, wallet["address"], threshold=10)
            mule_flag, pt_ratio = check_mule_patterns(wallet, features)
            if triggered:
                conf = min(in_deg / 20.0, 1.0)
                if mule_flag:
                    conf = min(conf + 0.2, 1.0)
                return HeuristicResult(
                    triggered=True,
                    confidence=conf,
                    explanation=f"Funnel pattern: {in_deg} inbound, pass-through ratio {pt_ratio:.2f}.",
                    evidence={"in_degree": in_deg, "pass_through_ratio": pt_ratio},
                )
        return HeuristicResult()


class PassThroughAccounts(BaseHeuristic):
    id = 23
    name = "PassThroughAccounts"
    environment = ENV
    lens_tags = ["graph", "behavioral"]
    description = "Funds transit through an account with minimal retention."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        triggered, pt_ratio = check_mule_patterns(wallet, features)
        if triggered:
            return HeuristicResult(
                triggered=True,
                confidence=min(pt_ratio, 1.0),
                explanation=f"Pass-through ratio {pt_ratio:.2f} — near-total relay.",
                evidence={"pass_through_ratio": pt_ratio},
            )
        return HeuristicResult()


class MirrorTransfers(BaseHeuristic):
    id = 26
    name = "MirrorTransfers"
    environment = ENV
    lens_tags = ["graph", "temporal"]
    description = "Matching debit and credit across jurisdictions to move value without cross-border transfer."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        if graph is not None and wallet and wallet.get("address"):
            triggered, n_cycles = check_circular_flows(graph, wallet["address"], max_length=3)
            if triggered:
                return HeuristicResult(
                    triggered=True,
                    confidence=min(n_cycles / 3.0, 1.0),
                    explanation=f"Mirror-like circular transfers detected ({n_cycles} loops).",
                    evidence={"cycle_count": n_cycles},
                )
        return HeuristicResult()


class DormantAccountActivation(BaseHeuristic):
    id = 31
    name = "DormantAccountActivation"
    environment = ENV
    lens_tags = ["temporal", "behavioral"]
    description = "Long-dormant account suddenly activated with high-value activity."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        triggered, info = check_new_entity_high_value(wallet, threshold_days=365, threshold_amount=0)
        if wallet:
            dormancy_days = wallet.get("dormancy_days", 0)
            recent_vol = wallet.get("total_in", 0) + wallet.get("total_out", 0)
            if dormancy_days > 180 and recent_vol > 10000:
                conf = min(dormancy_days / 730.0, 1.0)
                return HeuristicResult(
                    triggered=True,
                    confidence=conf,
                    explanation=f"Account dormant {dormancy_days}d then moved {recent_vol:.0f}.",
                    evidence={"dormancy_days": dormancy_days, "recent_volume": recent_vol},
                )
        return HeuristicResult()


class ACHMicroSplitting(BaseHeuristic):
    id = 35
    name = "ACHMicroSplitting"
    environment = ENV
    lens_tags = ["behavioral", "temporal"]
    description = "Electronic transfers micro-split across many transactions to avoid detection."
    data_requirements = []

    def evaluate(self, tx=None, wallet=None, graph=None, features=None, context=None):
        amounts = []
        if context and "amount" in context:
            amounts = context["amount"] if isinstance(context["amount"], list) else [context["amount"]]
        if not amounts and features:
            amounts = features.get("recent_amounts", [])
        if not amounts:
            return HeuristicResult(applicability=Applicability.INAPPLICABLE_MISSING_DATA)
        triggered, ratio = check_sub_threshold_fragmentation(amounts, threshold=3000.0)
        return HeuristicResult(
            triggered=triggered,
            confidence=min(ratio, 1.0) if triggered else 0.0,
            explanation=f"Micro-split ratio {ratio:.2f}" if triggered else "",
            evidence={"ratio": ratio},
        )


# ===================================================================
# Stub definitions for remaining traditional heuristics (off-chain)
# ===================================================================

_STUB_DEFS: list[tuple[int, str, list[str], str, list[str]]] = [
    (2, "CashIntensiveFrontBusiness", ["behavioral", "document"],
     "Front business generating anomalous cash revenue.", ["revenue_data"]),
    (3, "ComminglingRetailTills", ["behavioral", "document"],
     "Illicit cash mixed with legitimate point-of-sale receipts.", ["pos_data"]),
    (7, "CashPurchaseMonetaryInstruments", ["behavioral", "offramp"],
     "Cash used to purchase money orders, cashier checks, etc.", ["instrument_data"]),
    (8, "SequentialMoneyOrders", ["behavioral"],
     "Sequentially numbered money orders purchased in bulk.", ["instrument_data"]),
    (9, "TravelerCheckCycling", ["behavioral"],
     "Repeated purchase and redemption of traveler's checks.", ["instrument_data"]),
    (10, "CasinoChipWalking", ["behavioral", "offramp"],
     "Converting cash to casino chips then cashing out with minimal play.", ["gaming_data"]),
    (11, "CasinoCageFunneling", ["behavioral", "offramp"],
     "Funneling cash through casino cage transactions.", ["gaming_data"]),
    (12, "CurrencyExchangeLayering", ["behavioral", "graph"],
     "Layering funds through multiple currency exchange transactions.", ["forex_data"]),
    (13, "BulkCashSmuggling", ["behavioral", "offramp"],
     "Physical transportation of bulk cash across borders.", ["customs_data"]),
    (14, "CashCourierNetworks", ["entity", "graph"],
     "Networks of cash couriers moving money physically.", ["courier_data"]),
    (15, "NightDepositoryAbuse", ["behavioral", "temporal"],
     "Abuse of night deposit facilities to avoid teller scrutiny.", ["deposit_data"]),
    (16, "ATMCashRecycling", ["behavioral", "temporal"],
     "Repeated ATM deposits and withdrawals to recycle cash.", ["atm_data"]),
    (18, "CashPayrollPadding", ["behavioral", "document"],
     "Inflating payroll with fictitious employees paid in cash.", ["payroll_data"]),
    (19, "CharityDonationLaundering", ["behavioral", "entity"],
     "Channeling illicit funds through charitable donations.", ["donation_data"]),
    (20, "FestivalCashInflation", ["behavioral", "temporal"],
     "Inflating cash intake during festivals or events.", ["event_data"]),
    (24, "ThirdPartyWireChain", ["graph", "entity"],
     "Chains of wire transfers through unrelated third parties.", ["wire_data"]),
    (25, "BackToBackLoans", ["graph", "entity"],
     "Loans secured by deposits of illicit origin.", ["loan_data"]),
    (27, "CorrespondentBankingAbuse", ["graph", "entity"],
     "Misuse of correspondent banking relationships for layering.", ["correspondent_data"]),
    (28, "ShellCompanyInvoice", ["entity", "document"],
     "Invoices from shell companies for fictitious goods or services.", ["invoice_data"]),
    (29, "PhantomConsultingFees", ["entity", "document"],
     "Payments for non-existent consulting services.", ["invoice_data"]),
    (30, "IntercompanyLoanChurn", ["graph", "entity"],
     "Circular loans between related entities to create paper trail.", ["loan_data"]),
    (32, "StudentElderlyMuleAccounts", ["entity", "behavioral"],
     "Accounts of students or elderly exploited as money mules.", ["demographic_data"]),
    (33, "PrepaidCardLoadingRings", ["behavioral", "offramp"],
     "Coordinated loading of prepaid cards from illicit funds.", ["card_data"]),
    (34, "GiftCardMonetization", ["behavioral", "offramp"],
     "Converting illicit funds to gift cards for resale or use.", ["card_data"]),
    (36, "CheckKiting", ["behavioral", "temporal"],
     "Exploiting float time between check deposit and clearing.", ["check_data"]),
    (37, "MobileDepositDuplication", ["behavioral"],
     "Depositing the same check via mobile and physical channels.", ["mobile_deposit_data"]),
    (38, "PayrollProcessorAbuse", ["entity", "document"],
     "Misusing payroll processing platforms to move funds.", ["payroll_data"]),
    (39, "FintechAccountHopping", ["behavioral", "temporal"],
     "Rapidly opening and closing fintech accounts to layer funds.", ["fintech_data"]),
    (40, "MicrobusinessMerchantAbuse", ["entity", "document"],
     "Fictitious micro-merchants processing fraudulent transactions.", ["merchant_data"]),
    (41, "OverInvoicingImports", ["document", "entity"],
     "Inflating import invoice values to move excess funds abroad.", ["trade_data"]),
    (42, "UnderInvoicingExports", ["document", "entity"],
     "Under-declaring export values to retain funds domestically.", ["trade_data"]),
    (43, "MultipleInvoicing", ["document"],
     "Submitting multiple invoices for the same shipment.", ["trade_data"]),
    (44, "ShortShipping", ["document"],
     "Shipping fewer goods than declared on invoices.", ["shipping_data"]),
    (45, "OverShipping", ["document"],
     "Shipping more goods than declared, hiding value transfer.", ["shipping_data"]),
    (46, "PhantomShipment", ["document"],
     "Invoicing for shipments that never occurred.", ["shipping_data"]),
    (47, "MisdescriptionOfGoods", ["document"],
     "Deliberately mis-describing goods to alter declared value.", ["customs_data"]),
    (48, "CarouselTradeFraud", ["graph", "document"],
     "Circular trading of goods across borders to reclaim VAT fraudulently.", ["trade_data"]),
    (49, "DualUseHighValueGoods", ["document", "entity"],
     "Trading dual-use or high-value goods to transfer value.", ["trade_data"]),
    (50, "CommoditySwaps", ["document"],
     "Swapping commodity grades to obscure value transfer.", ["commodity_data"]),
    (51, "FreightOverbilling", ["document"],
     "Inflating freight and logistics charges.", ["logistics_data"]),
    (52, "FalseReturnsRebates", ["document", "behavioral"],
     "Fabricating returns or rebates to extract funds.", ["returns_data"]),
    (53, "CustomsBrokerCollusion", ["entity", "document"],
     "Collusion with customs brokers to falsify documents.", ["customs_data"]),
    (54, "WarehouseReceiptFraud", ["document"],
     "Fraudulent warehouse receipts for non-existent goods.", ["warehouse_data"]),
    (55, "TradeFinanceLCAbuse", ["document", "entity"],
     "Abuse of letters of credit for trade-based laundering.", ["lc_data"]),
    (56, "SanctionedRouteTransshipment", ["entity", "graph"],
     "Transshipping goods via third countries to evade sanctions.", ["shipping_data"]),
    (57, "UsedCarExportLaundering", ["document", "offramp"],
     "Purchasing used cars with cash and exporting for resale.", ["vehicle_data"]),
    (58, "ScrapMetalValueMasking", ["document"],
     "Using scrap metal trade to disguise value transfers.", ["commodity_data"]),
    (59, "PreciousStonePortability", ["offramp"],
     "Moving value via easily transportable precious stones.", ["gemstone_data"]),
    (60, "ArtworkValuationInflation", ["document", "entity"],
     "Inflating artwork prices to facilitate value transfer.", ["auction_data"]),
    (61, "LayeredShellCompanies", ["entity", "graph"],
     "Multiple layers of shell companies to obscure ownership.", ["corporate_data"]),
    (62, "ShelfCompanyPurchase", ["entity"],
     "Purchasing aged shelf companies to appear legitimate.", ["corporate_data"]),
    (63, "NomineeShareholderMasking", ["entity"],
     "Using nominee shareholders to hide beneficial ownership.", ["corporate_data"]),
    (64, "TrustFoundationOpacity", ["entity", "document"],
     "Exploiting trust or foundation structures for opacity.", ["trust_data"]),
    (65, "ProfessionalEnablerRouting", ["entity", "graph"],
     "Funds routed through lawyers, accountants, or other professionals.", ["professional_data"]),
    (66, "FalseShareholderLoans", ["entity", "document"],
     "Fictitious shareholder loans to inject illicit funds.", ["loan_data"]),
    (67, "CapitalContributionRecycling", ["entity", "graph"],
     "Recycling funds through capital contributions.", ["corporate_data"]),
    (68, "DirectorForHireNetworks", ["entity"],
     "Networks of nominee directors used to obscure control.", ["director_data"]),
    (69, "VirtualOfficeShelling", ["entity"],
     "Shell companies registered at virtual office addresses.", ["address_data"]),
    (70, "InvoiceFactories", ["entity", "document"],
     "Networks generating fictitious invoices at scale.", ["invoice_data"]),
    (71, "BookkeepingWashEntries", ["document"],
     "False bookkeeping entries to balance illicit flows.", ["accounting_data"]),
    (72, "TaxRefundLaundering", ["document", "behavioral"],
     "Filing fraudulent tax claims to extract laundered funds.", ["tax_data"]),
    (73, "InsurancePremiumOverpayment", ["behavioral", "document"],
     "Overpaying insurance premiums and requesting refunds.", ["insurance_data"]),
    (74, "MortgageEarlyPayoff", ["behavioral", "offramp"],
     "Using illicit cash for early mortgage repayment.", ["mortgage_data"]),
    (75, "RealEstateFlippingRing", ["entity", "graph"],
     "Rapidly flipping real estate to layer proceeds.", ["property_data"]),
    (76, "RenovationInvoiceInflation", ["document"],
     "Inflating renovation invoices to justify cash expenditure.", ["construction_data"]),
    (77, "LuxuryAssetParking", ["offramp"],
     "Parking value in luxury goods (yachts, jets, jewelry).", ["asset_data"]),
    (78, "PawnAuctionLaundering", ["offramp", "behavioral"],
     "Using pawn shops or auctions to convert assets.", ["auction_data"]),
    (79, "FranchiseFeeLaundering", ["entity", "document"],
     "Laundering through franchise fee payments.", ["franchise_data"]),
    (80, "CrowdfundingAbuse", ["behavioral", "entity"],
     "Using crowdfunding platforms to layer illicit funds.", ["crowdfunding_data"]),
    (81, "HawalaIVTS", ["entity", "graph"],
     "Informal value transfer via hawala or similar systems.", ["ivts_data"]),
    (82, "UndergroundBankingMirrorBooks", ["entity", "graph"],
     "Underground banking using mirror ledger books.", ["banking_data"]),
    (83, "TourismReceiptInflation", ["document", "behavioral"],
     "Inflating tourism receipts to justify inbound cash.", ["tourism_data"]),
    (84, "RemittanceCorridorLayering", ["graph", "entity"],
     "Layering funds through high-volume remittance corridors.", ["remittance_data"]),
    (85, "RefugeeAidDiversion", ["entity"],
     "Diverting humanitarian aid funds for laundering.", ["aid_data"]),
    (86, "DiplomaticPouchAbuse", ["entity"],
     "Misuse of diplomatic channels to move value.", ["diplomatic_data"]),
    (87, "FreeTradeZoneConcealment", ["entity", "document"],
     "Concealing value movements within free trade zones.", ["ftz_data"]),
    (88, "CashForGoldExportLoop", ["offramp", "graph"],
     "Converting cash to gold then exporting for sale abroad.", ["commodity_data"]),
    (89, "CrossBorderSalarySimulation", ["entity", "document"],
     "Simulating salary payments across borders to move funds.", ["payroll_data"]),
    (90, "StudentTuitionLaundering", ["entity", "document"],
     "Using tuition payments to educational institutions for laundering.", ["tuition_data"]),
]

# ===================================================================
# IDs that have full class implementations above
# ===================================================================
_IMPLEMENTED_IDS = {1, 4, 5, 6, 17, 21, 22, 23, 26, 31, 35}

# ===================================================================
# Instantiate everything
# ===================================================================

_instances: list[BaseHeuristic] = [
    CashStructuring(),
    MuleDeposits(),
    RoundDollarDeposits(),
    RapidCashInWireOut(),
    LoanBackScheme(),
    NestedPersonalAccounts(),
    FunnelAccounts(),
    PassThroughAccounts(),
    MirrorTransfers(),
    DormantAccountActivation(),
    ACHMicroSplitting(),
]

for _hid, _name, _tags, _desc, _reqs in _STUB_DEFS:
    assert _hid not in _IMPLEMENTED_IDS, f"Stub {_hid} clashes with implemented class"
    _instances.append(_create_stub(_hid, _name, _tags, _desc, _reqs))

# ===================================================================
# Register all 90 heuristics
# ===================================================================
from app.ml.heuristics.registry import register as _register

for _h in _instances:
    _register(_h)
