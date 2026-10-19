from typing import Tuple


class BKTTracker:
    """
    Multimodal Bayesian Knowledge Tracing (BKT) Model
    Maintains probability of mastery P(Lt) and maps to proximal development boundaries.
    [R01: 多模態 BKT §動態追蹤]
    """

    def __init__(
        self,
        p_l0: float = 0.30,
        p_t: float = 0.15,
        p_g: float = 0.10,
        p_s: float = 0.10,
    ):
        self.p_l0 = p_l0
        self.p_t = p_t
        self.p_g = p_g
        self.p_s = p_s

    def update_mastery(self, p_prev: float, is_success: bool) -> float:
        """
        Compute Bayesian posterior update followed by forward learning prediction.
        """
        p_prev = max(0.01, min(0.99, p_prev))

        if is_success:
            numerator = p_prev * (1.0 - self.p_s)
            denominator = numerator + (1.0 - p_prev) * self.p_g
        else:
            numerator = p_prev * self.p_s
            denominator = numerator + (1.0 - p_prev) * (1.0 - self.p_g)

        p_posterior = numerator / denominator if denominator > 0 else p_prev
        p_next = p_posterior + (1.0 - p_posterior) * self.p_t
        return round(max(0.05, min(0.99, p_next)), 4)

    def calculate_zpd_boundaries(self, p_mastery: float) -> Tuple[float, float]:
        """
        Compute dynamic ZPD bounds [zpd_lower, zpd_upper].
        """
        lower = max(0.10, p_mastery - 0.20)
        upper = min(0.95, p_mastery + 0.25)
        return round(lower, 4), round(upper, 4)
