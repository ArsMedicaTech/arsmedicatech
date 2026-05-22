"""
Tools for scoring benchmark results.
"""

# Case Score = Sflag ×(wacc * Accuracy + wexp * Explainability + wcomp * Component)


class Weights:
    """
    Class to hold weights for case scoring.

    :param wacc: float - Weight for accuracy.
    :param wcomp: float - Weight for component.
    :param wexp: float - Weight for explainability.
    """
    def __init__(self, wacc: float, wexp: float, wcomp: float):
        self.wacc = wacc
        self.wexp = wexp
        self.wcomp = wcomp

    def __repr__(self):
        return f"Weights(wacc={self.wacc}, wexp={self.wexp}, wcomp={self.wcomp})"


def case_score(safety_flag: bool, weights: Weights, accuracy: float, explainability: float, component: float) -> float:
    """
    Calculate the case score based on the provided weights and metrics.

    :param safety_flag: bool - Flag indicating if the case is selected.

    :param accuracy: float - Accuracy score.
    :param explainability: float - Explainability score.
    :param component: float - Component score.

    :return: float - The calculated case score.
    """
    Sflag = 1.0 if safety_flag else 0.0

    wacc = weights.wacc
    wexp = weights.wexp
    wcomp = weights.wcomp

    return Sflag * (wacc * accuracy + wexp * explainability + wcomp * component)


# w_textacc (Accuracy weight) = 0.6
# w_textexp (Explainability weight) = 0.2
# w_textcomp (Component Performance weight) = 0.2
