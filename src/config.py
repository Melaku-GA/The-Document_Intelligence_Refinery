"""
Centralized configuration loader for Document Intelligence Refinery.

All thresholds, domain keywords, and strategy parameters are externalized here.
New domains can be onboarded by editing only this config file.
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import yaml


class TriageConfig(BaseModel):
    """Triage Agent configuration."""
    
    # Origin type detection thresholds
    min_character_density: float = Field(default=0.001, ge=0, le=1)
    max_image_area_ratio_for_digital: float = Field(default=0.5, ge=0, le=1)
    min_character_count_for_digital: int = Field(default=100, ge=0)
    
    # Layout complexity thresholds
    min_columns_for_multicolumn: int = Field(default=2, ge=1)
    min_table_area_ratio: float = Field(default=0.1, ge=0, le=1)
    min_figure_count: int = Field(default=3, ge=0)
    
    # Language detection
    supported_languages: List[str] = Field(default_factory=lambda: ["en", "am"])
    min_language_confidence: float = Field(default=0.7, ge=0, le=1)
    
    # Domain keywords
    domain_keywords: Dict[str, List[str]] = Field(default_factory=lambda: {
        "financial": [
            "revenue", "profit", "loss", "balance", "asset", "liability",
            "equity", "income", "expense", "fiscal", "budget", "audit",
            "financial", "quarterly", "annual", "earnings", "dividend"
        ],
        "legal": [
            "contract", "agreement", "party", "liability", "warranty",
            "compliance", "regulation", "statute", "jurisdiction", "clause"
        ],
        "technical": [
            "specification", "architecture", "implementation", "api",
            "system", "configuration", "deployment", "infrastructure"
        ],
        "medical": [
            "diagnosis", "treatment", "patient", "symptom", "prescription",
            "clinical", "healthcare", "medication", "therapy"
        ]
    })


class ExtractionConfig(BaseModel):
    """Extraction strategy configuration."""
    
    # Strategy A: Fast Text
    fast_text_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    min_characters_per_page: int = Field(default=100, ge=0)
    max_image_ratio_for_fast_text: float = Field(default=0.3, ge=0, le=1)
    
    # Strategy B: Layout-Aware
    layout_confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    enable_table_extraction: bool = Field(default=True)
    enable_figure_extraction: bool = Field(default=True)
    
    # Strategy C: Vision
    vision_confidence_threshold: float = Field(default=0.4, ge=0, le=1)
    max_pages_for_vision: int = Field(default=10, ge=1)
    max_cost_per_document: float = Field(default=5.0, ge=0)
    
    # Escalation chain
    escalation_chain: List[str] = Field(
        default_factory=lambda: ["fast_text", "minerulayout", "vision"]
    )


class ChunkingConfig(BaseModel):
    """Chunking engine configuration."""
    
    max_chars: int = Field(default=800, ge=100, le=5000)
    max_tokens: int = Field(default=512, ge=50, le=2000)
    
    # Rule enforcement
    preserve_table_headers: bool = Field(default=True)
    preserve_figure_captions: bool = Field(default=True)
    preserve_numbered_lists: bool = Field(default=True)
    preserve_section_headers: bool = Field(default=True)
    resolve_cross_references: bool = Field(default=True)
    
    # Validation
    validate_chunk_rules: bool = Field(default=True)
    min_chunk_length: int = Field(default=50, ge=0)
    max_chunk_length: int = Field(default=2000, ge=100)


class IndexingConfigModel(BaseModel):
    """PageIndex configuration."""
    
    output_dir: str = Field(default=".refinery/pageindex")
    min_section_pages: int = Field(default=1, ge=1)
    max_depth: int = Field(default=4, ge=1, le=10)
    extract_entities: bool = Field(default=True)
    
    # Entity patterns
    entity_patterns: Dict[str, str] = Field(default_factory=lambda: {
        'organization': r'\b[A-Z][a-zA-Z]*(?:Corporation|Company|Bank|Ministry|Agency|Institute|Authority)\b',
        'financial': r'\b(?:Birr|ETB|\$|USD|EUR)\s*[\d,]+(?:\.\d{2})?\b',
        'date': r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        'number': r'\b\d+(?:\.\d+)?(?:\s*%|\s*billion|\s*million|\s*thousand)?\b',
    })


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""
    
    backend: str = Field(default="in_memory")
    embedding_dim: int = Field(default=384, ge=128)
    top_k: int = Field(default=5, ge=1, le=20)


class RefineryConfig(BaseModel):
    """Main configuration for the Document Intelligence Refinery."""
    
    triage: TriageConfig = Field(default_factory=TriageConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    indexing: IndexingConfigModel = Field(default_factory=IndexingConfigModel)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    
    @classmethod
    def load_from_yaml(cls, path: str) -> "RefineryConfig":
        """Load configuration from YAML file."""
        config_path = Path(path)
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                return cls(**data)
        return cls()
    
    @classmethod
    def load_default(cls) -> "RefineryConfig":
        """Load default configuration."""
        return cls()


# Global config instance
_config: Optional[RefineryConfig] = None


def get_config() -> RefineryConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = RefineryConfig.load_default()
    return _config


def load_config(config_path: str) -> RefineryConfig:
    """Load configuration from a YAML file."""
    global _config
    _config = RefineryConfig.load_from_yaml(config_path)
    return _config


def reset_config():
    """Reset to default configuration."""
    global _config
    _config = None
