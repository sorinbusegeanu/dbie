"""Phase 11 reproducible pairwise scheduling and Elo aggregation."""

from __future__ import annotations

import random
from collections import Counter
from itertools import combinations

from pydantic import BaseModel, Field

from dbie.domain.models import PairwiseMatch


class RankedCandidate(BaseModel):
    idea_id: str
    rating: float
    rank: int
    match_count: int
    stability: float = Field(ge=0, le=1)


def schedule_pairs(
    idea_ids: list[str], *, run_id: str, judge_model: str, seed: int
) -> list[PairwiseMatch]:
    randomizer = random.Random(seed)
    matches: list[PairwiseMatch] = []
    for first, second in combinations(sorted(set(idea_ids)), 2):
        pair = [first, second]
        randomizer.shuffle(pair)
        matches.append(
            PairwiseMatch(
                run_id=run_id,
                left_idea_id=pair[0],
                right_idea_id=pair[1],
                judge_model=judge_model,
                presentation_order_randomized=True,
            )
        )
    return matches


def rank_matches(
    matches: list[PairwiseMatch], *, k_factor: float = 24
) -> list[RankedCandidate]:
    identifiers = sorted(
        {item.left_idea_id for item in matches}
        | {item.right_idea_id for item in matches}
    )
    ratings = {identifier: 1500.0 for identifier in identifiers}
    counts: Counter[str] = Counter()
    pair_votes: dict[tuple[str, str], list[str | None]] = {}
    for match in matches:
        left, right = match.left_idea_id, match.right_idea_id
        expected_left = 1 / (1 + 10 ** ((ratings[right] - ratings[left]) / 400))
        actual_left = (
            0.5 if match.winner_idea_id is None else float(match.winner_idea_id == left)
        )
        delta = k_factor * (actual_left - expected_left)
        ratings[left] += delta
        ratings[right] -= delta
        counts.update((left, right))
        key = tuple(sorted((left, right)))
        pair_votes.setdefault(key, []).append(match.winner_idea_id)
    stability_by_id = {identifier: [] for identifier in identifiers}
    for (left, right), votes in pair_votes.items():
        frequencies = Counter(votes)
        stability = max(frequencies.values()) / len(votes)
        stability_by_id[left].append(stability)
        stability_by_id[right].append(stability)
    ordered = sorted(
        identifiers, key=lambda identifier: (-ratings[identifier], identifier)
    )
    return [
        RankedCandidate(
            idea_id=identifier,
            rating=round(ratings[identifier], 3),
            rank=index + 1,
            match_count=counts[identifier],
            stability=(
                sum(stability_by_id[identifier]) / len(stability_by_id[identifier])
                if stability_by_id[identifier]
                else 0
            ),
        )
        for index, identifier in enumerate(ordered)
    ]


def unstable_pairs(
    matches: list[PairwiseMatch], threshold: float = 0.67
) -> list[tuple[str, str]]:
    votes: dict[tuple[str, str], list[str | None]] = {}
    for match in matches:
        key = tuple(sorted((match.left_idea_id, match.right_idea_id)))
        votes.setdefault(key, []).append(match.winner_idea_id)
    return [
        pair
        for pair, outcomes in votes.items()
        if len(outcomes) > 1
        and max(Counter(outcomes).values()) / len(outcomes) < threshold
    ]
