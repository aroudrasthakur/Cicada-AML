"""Base class and result types for the 185-typology heuristic engine."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Applicability(str, Enum):
    APPLICABLE = "applicable"
    INAPPLICABLE_MISSING_DATA = "inapplicable_missing_data"
    INAPPLICABLE_OUT_OF_SCOPE = "inapplicable_out_of_scope"


class Environment(str, Enum):
    TRADITIONAL = "traditional"
    BLOCKCHAIN = "blockchain"
    HYBRID = "hybrid"
    AI_ENABLED = "ai_enabled"


@dataclass
class HeuristicResult:
    triggered: bool = False
    confidence: float = 0.0
    explanation: str = ""
    applicability: Applicability = Applicability.APPLICABLE
    evidence: dict[str, Any] = field(default_factory=dict)


class BaseHeuristic(ABC):
    """Every heuristic must subclass this and implement evaluate()."""
    
    id: int
    name: str
    environment: Environment
    lens_tags: list[str]
    description: str
    data_requirements: list[str]
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
    
    @abstractmethod
    def evaluate(
        self,
        tx: Optional[dict] = None,
        wallet: Optional[dict] = None,
        graph: Any = None,
        features: Optional[dict] = None,
        context: Optional[dict] = None,
    ) -> HeuristicResult:
        """Run detection logic. Return HeuristicResult."""
        ...
    
    def check_data_requirements(self, context: Optional[dict] = None) -> Applicability:
        """Check if required data is available. Override for custom logic."""
        if not context:
            if self.data_requirements:
                return Applicability.INAPPLICABLE_MISSING_DATA
            return Applicability.APPLICABLE
        for req in self.data_requirements:
            if req not in context or context[req] is None:
                return Applicability.INAPPLICABLE_MISSING_DATA
        return Applicability.APPLICABLE
