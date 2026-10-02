"""Frozen experiment settings, selected before held-out test evaluation."""

SEED = 20260930
SEVERITY_ORDER = {"Major": 3, "Moderate": 2, "Minor": 1}
SEVERITIES = ("Major", "Moderate", "Minor")
EMBEDDING_DIMS = 16
MIN_COVERED_ACCURACY = 0.95
MIN_COVERAGE = 0.40
MAJOR_PRECISION_TARGET = 0.90
GATE_MACRO_F1_MARGIN = 0.05
GATE_MAJOR_RECALL_MIN = 0.50
