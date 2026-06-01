from datetime import datetime, timedelta


def sm2_review(ease_factor: float, interval: int, repetitions: int, rating: int) -> dict:
    if rating == 0:
        repetitions = 0
        interval = 0
        ease_factor = max(1.3, ease_factor - 0.2)
    elif rating == 1:
        repetitions = 0
        interval = 1
        ease_factor = max(1.3, ease_factor - 0.15)
    elif rating == 2:
        repetitions += 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = round(interval * ease_factor)
    elif rating == 3:
        repetitions += 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = round(interval * ease_factor * 1.3)
        ease_factor = min(3.0, ease_factor + 0.15)
    else:
        raise ValueError(f"Invalid rating: {rating}")

    next_review = datetime.now() + timedelta(days=interval)

    return {
        "ease_factor": round(ease_factor, 2),
        "interval": interval,
        "repetitions": repetitions,
        "next_review": next_review,
    }
