# app/detection/flaky.py
import re
from app.models.failure import FailureContext

# (keyword_regex, category, weight)
FLAKY_KEYWORDS: list[tuple[str, str, float]] = [
    # Network
    (r"connection reset by peer", "network", 0.85),
    (r"EHOSTUNREACH", "network", 0.80),
    (r"connection refused", "network", 0.70),
    (r"could not resolve host", "network", 0.80),
    (r"network is unreachable", "network", 0.80),
    (r"TLS handshake timeout", "network", 0.75),
    # Rate limits
    (r"rate limit exceeded", "rate_limit", 0.95),
    (r"429 Too Many Requests", "rate_limit", 0.90),
    (r"API rate limit", "rate_limit", 0.90),
    (r"secondary rate limit", "rate_limit", 0.92),
    # Gateway / proxy
    (r"502 Bad Gateway", "gateway", 0.85),
    (r"503 Service Unavailable", "gateway", 0.80),
    (r"504 Gateway Timeout", "gateway", 0.85),
    (r"upstream connect error", "gateway", 0.80),
    # Infrastructure
    (r"no space left on device", "infrastructure", 0.90),
    (r"ENOSPC", "infrastructure", 0.90),
    (r"disk full", "infrastructure", 0.85),
    (r"runner lost communication", "infrastructure", 0.88),
    # Registry / CDN
    (r"dial tcp.*i/o timeout", "registry", 0.80),
    (r"manifest unknown", "registry", 0.75),
    (r"toomanyrequests.*docker", "registry", 0.85),
    # Generic transient
    (r"temporary failure", "transient", 0.60),
    (r"try again later", "transient", 0.55),
    (r"transient error", "transient", 0.65),
    (r"intermittent", "transient", 0.50),
    (r"timeout", "transient", 0.40),
]


class FlakyClassifier:
    def classify(self, ctx: FailureContext) -> dict:
        full_log = "\n".join(line.message for line in ctx.logs)
        matched_signals: list[dict] = []
        category_weights: dict[str, float] = {}
        score = 0.0

        for pattern, category, weight in FLAKY_KEYWORDS:
            for m in re.finditer(pattern, full_log, re.IGNORECASE):
                # Capture up to 3 matched signals
                if len(matched_signals) < 3:
                    start = max(0, m.start() - 20)
                    end = min(len(full_log), m.end() + 80)
                    snippet = full_log[start:end][:200]
                    matched_signals.append({
                        "keyword": pattern,
                        "category": category,
                        "log_line": snippet,
                    })
                # Accumulate weight per category
                category_weights[category] = category_weights.get(category, 0.0) + weight
                score = min(1.0, score + weight)
                break  # one match per pattern is enough

        # Multi-category boost: 2+ distinct categories → +0.15
        if len(category_weights) >= 2:
            score = min(1.0, score + 0.15)

        # Dominant category
        flaky_category = None
        if category_weights:
            flaky_category = max(category_weights, key=category_weights.get)

        is_flaky = score >= 0.6

        recommended_action = (
            "Retry the build — likely transient."
            if is_flaky
            else "Investigate as real bug."
        )

        return {
            "is_flaky": is_flaky,
            "flaky_score": round(score, 3),
            "flaky_category": flaky_category,
            "matched_signals": matched_signals,
            "recommended_action": recommended_action,
        }
