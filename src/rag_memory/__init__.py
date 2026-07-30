"""
rag_memory package: RAG & Historical Memory Engine for Odoo Agentic Swarm.
"""

from rag_memory.ingester import (
    Document,
    DocumentChunk,
    DocumentCategory,
    ProposalOutcome,
    DocumentIngester,
    JSONIngester,
    CSVIngester,
    MarkdownIngester,
    TextIngester,
    create_sliding_window_chunks,
)
from rag_memory.business_lines import (
    GuidedArchitectureEngine,
    BusinessLineClassifier,
    BusinessLineType,
    STANDARD_BOM_TEMPLATES,
)
from rag_memory.campaign_onepager_engine import (
    CampaignOnePagerEngine,
    OnePagerProposal,
    TargetedCampaign,
)
from rag_memory.indexer import (
    VectorStore,
    SearchResult,
    tokenize,
    strip_diacritics,
)
from rag_memory.few_shot import (
    FewShotEngine,
    HistoricalMemory,
)
from rag_memory.knowledge_matrix import (
    KnowledgeMatrix,
    TechnicalKnowledgeMatrix,
    OfferRecord,
    PricingItem,
    TechnicalSpec,
    CommercialTerms,
    OfferStatus,
)
from rag_memory.advanced_intelligence import (
    OperationalIntelligenceEngine,
    RegulatoryComplianceAuditor,
    WinRateEstimator,
    CrossSellEngine,
    ComplianceWarning,
    RegulatoryAuditReport,
    WinRatePrediction,
    CrossSellOpportunity,
)

__all__ = [
    "Document",
    "DocumentChunk",
    "DocumentCategory",
    "ProposalOutcome",
    "DocumentIngester",
    "JSONIngester",
    "CSVIngester",
    "MarkdownIngester",
    "TextIngester",
    "create_sliding_window_chunks",
    "VectorStore",
    "SearchResult",
    "tokenize",
    "strip_diacritics",
    "FewShotEngine",
    "HistoricalMemory",
    "KnowledgeMatrix",
    "TechnicalKnowledgeMatrix",
    "OfferRecord",
    "PricingItem",
    "TechnicalSpec",
    "CommercialTerms",
    "OfferStatus",
    "OperationalIntelligenceEngine",
    "RegulatoryComplianceAuditor",
    "WinRateEstimator",
    "CrossSellEngine",
    "ComplianceWarning",
    "RegulatoryAuditReport",
    "WinRatePrediction",
    "CrossSellOpportunity",
    "BusinessLineClassifier",
    "BusinessLineType",
    "STANDARD_BOM_TEMPLATES",
    "GuidedArchitectureEngine",
]


