from collections.abc import Iterable

from dbie.domain.decisions import validate_finalist_promotion, validate_transition
from dbie.domain.eligibility import EligibilityResult, evaluate_eligibility
from dbie.domain.enums import CandidateState
from dbie.domain.models import Assumption, BusinessIdea
from dbie.persistence.repositories import CandidateRepository


class CandidateService:
    def __init__(self, repository: CandidateRepository) -> None:
        self.repository = repository

    def register(self, idea: BusinessIdea) -> BusinessIdea:
        return self.repository.create(idea)

    def apply_eligibility(self, idea_id: str) -> EligibilityResult:
        idea = self.repository.get(idea_id)
        result = evaluate_eligibility(idea)
        target = CandidateState.ELIGIBLE if result.eligible else CandidateState.KILL
        self.transition(idea_id, target)
        return result

    def transition(
        self,
        idea_id: str,
        target: CandidateState,
        assumptions: Iterable[Assumption] = (),
    ) -> BusinessIdea:
        idea = self.repository.get(idea_id)
        validate_transition(idea.lifecycle_state, target)
        if target is CandidateState.FINALIST:
            validate_finalist_promotion(assumptions)
        return self.repository.set_state(idea_id, target)
