"""Classification metrics for contradiction, update, and compatibility labels."""

from __future__ import annotations


def confusion_matrix(predicted: list[str], expected: list[str]) -> dict[str, dict[str, int]]:
    if len(predicted) != len(expected):
        raise ValueError("predicted and expected must have equal length")
    labels = sorted(set(predicted) | set(expected))
    matrix = {actual: {guess: 0 for guess in labels} for actual in labels}
    for guess, actual in zip(predicted, expected):
        matrix[actual][guess] += 1
    return matrix


def classification_report(predicted: list[str], expected: list[str]) -> dict:
    matrix = confusion_matrix(predicted, expected)
    scores = {}
    for label in matrix:
        true_positive = matrix[label][label]
        false_positive = sum(matrix[other][label] for other in matrix if other != label)
        false_negative = sum(value for guess, value in matrix[label].items() if guess != label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        scores[label] = {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    macro_f1 = sum(score["f1"] for score in scores.values()) / len(scores) if scores else 0.0
    return {"labels": scores, "macro_f1": macro_f1, "confusion_matrix": matrix}
