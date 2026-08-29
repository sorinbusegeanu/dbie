from dbie.domain.models import PairwiseMatch
from dbie.persistence.db import Database
from dbie.persistence.repositories import PairwiseMatchRepository
from dbie.services.tournament import rank_matches, schedule_pairs, unstable_pairs


def test_scheduler_and_ranking_are_reproducible() -> None:
    first = schedule_pairs(["c", "a", "b"], run_id="run", judge_model="gpt-oss", seed=7)
    second = schedule_pairs(
        ["b", "c", "a"], run_id="run", judge_model="gpt-oss", seed=7
    )
    assert [(m.left_idea_id, m.right_idea_id) for m in first] == [
        (m.left_idea_id, m.right_idea_id) for m in second
    ]
    for match in first:
        match.winner_idea_id = (
            "a"
            if "a" in {match.left_idea_id, match.right_idea_id}
            else match.left_idea_id
        )
    assert rank_matches(first)[0].idea_id == "a"


def test_unstable_repeated_pair_escalates() -> None:
    matches = [
        PairwiseMatch(
            run_id="run",
            left_idea_id="a",
            right_idea_id="b",
            winner_idea_id=winner,
            judge_model="m",
        )
        for winner in ("a", "b")
    ]
    assert unstable_pairs(matches) == [("a", "b")]


def test_match_records_are_persisted_without_overwriting_models(tmp_path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'matches.sqlite3'}")
    database.initialize()
    repository = PairwiseMatchRepository(database)
    for model in ("gpt-oss:20b-64k", "ministral-3:14b-64k"):
        repository.create(
            PairwiseMatch(
                run_id="run",
                left_idea_id="a",
                right_idea_id="b",
                winner_idea_id="a",
                judge_model=model,
            )
        )
    assert {item.judge_model for item in repository.for_run("run")} == {
        "gpt-oss:20b-64k",
        "ministral-3:14b-64k",
    }
