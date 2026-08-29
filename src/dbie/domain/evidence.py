"""Evidence lineage and trust semantics."""

from collections.abc import Iterable

from dbie.domain.enums import EvidenceTier, EvidenceType
from dbie.domain.models import EvidenceItem


def independent_lineage_count(items: Iterable[EvidenceItem]) -> int:
    return len({item.lineage_group_id for item in items})


def can_validate_fatal_assumption(
    items: Iterable[EvidenceItem], minimum_independent_sources: int = 2
) -> bool:
    eligible = [
        item
        for item in items
        if item.evidence_type is not EvidenceType.MODEL_JUDGMENT
        and item.tier is not EvidenceTier.MODEL_ONLY
    ]
    if any(item.tier is EvidenceTier.OBSERVED_BEHAVIOR for item in eligible):
        return True
    return independent_lineage_count(eligible) >= minimum_independent_sources
