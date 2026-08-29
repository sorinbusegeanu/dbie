"""Stable logical model roles, independent of concrete model families."""

from enum import StrEnum


class ModelRole(StrEnum):
    THINKER = "THINKER"
    DOER = "DOER"
    BUILDER = "BUILDER"
    JUDGE = "JUDGE"


class ModelSelection(StrEnum):
    PRIMARY = "PRIMARY"
    CHALLENGER = "CHALLENGER"
