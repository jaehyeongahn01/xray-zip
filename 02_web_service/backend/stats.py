"""통계·순위 서비스 계층 (設計).

저장소에서 받은 원시 게임 레코드 리스트로 §7.7/§7.8 형태를 계산하는 순수 함수.
클래스 정확도는 class_points(정상100/폐렴50 비대칭)가 아니라 class_correct(bool)와
true_label(0/1/2)로만 집계한다.
"""
from typing import List

# true_label → class_accuracy 키
_LABEL_KEY = {0: "normal", 1: "bacteria", 2: "virus"}

RECENT_TREND_N = 10


def _empty_class_accuracy():
    return {
        "normal": {"total": 0, "correct": 0, "accuracy": 0.0},
        "bacteria": {"total": 0, "correct": 0, "accuracy": 0.0},
        "virus": {"total": 0, "correct": 0, "accuracy": 0.0},
    }


def compute_user_stats(games: List[dict], recent_n: int = RECENT_TREND_N) -> dict:
    """사용자 게임 레코드 → 통계 dict (設計).

    기록이 없으면 0값(plays:0, avg/best:0, recent_trend:[], class_accuracy 모두 0).
    """
    if not games:
        return {
            "plays": 0,
            "avg_score": 0.0,
            "best_score": 0.0,
            "class_accuracy": _empty_class_accuracy(),
            "recent_trend": [],
        }

    plays = len(games)
    averages = [g.get("average", 0.0) for g in games]
    avg_score = sum(averages) / plays
    best_score = max(averages)

    # 클래스 정확도: class_correct + true_label 로만 집계
    class_acc = _empty_class_accuracy()
    for g in games:
        for pq in g.get("per_question_summary", []):
            key = _LABEL_KEY.get(int(pq["true_label"]))
            if key is None:
                continue
            class_acc[key]["total"] += 1
            if pq.get("class_correct"):
                class_acc[key]["correct"] += 1
    for key in class_acc:
        t = class_acc[key]["total"]
        class_acc[key]["accuracy"] = (
            class_acc[key]["correct"] / t if t > 0 else 0.0
        )

    # recent_trend: played_at 내림차순 상위 N → 오래된→최신으로 뒤집기.
    # 동일 played_at 은 저장(append) 순서로 안정 정렬 유지.
    indexed = list(enumerate(games))
    indexed.sort(key=lambda it: (it[1].get("played_at", ""), it[0]), reverse=True)
    top = indexed[:recent_n]
    top.reverse()
    recent_trend = [g.get("average", 0.0) for _, g in top]

    return {
        "plays": plays,
        "avg_score": avg_score,
        "best_score": best_score,
        "class_accuracy": class_acc,
        "recent_trend": recent_trend,
    }


def compute_leaderboard(all_games: List[dict], limit: int = 10) -> List[dict]:
    """모든 게임 → 사용자별 집계·정렬된 순위 엔트리 리스트 (設計).

    정렬: best_average desc → avg_average desc → plays desc → user_id asc.
    """
    by_user = {}
    for g in all_games:
        uid = g.get("user_id")
        if uid is None:
            continue
        by_user.setdefault(uid, []).append(g.get("average", 0.0))

    agg = []
    for uid, averages in by_user.items():
        plays = len(averages)
        agg.append({
            "user_id": uid,
            "best_average": max(averages) if averages else 0.0,
            "avg_average": sum(averages) / plays if plays else 0.0,
            "plays": plays,
        })

    agg.sort(
        key=lambda e: (-e["best_average"], -e["avg_average"], -e["plays"], e["user_id"])
    )

    entries = []
    for rank, e in enumerate(agg[:limit], start=1):
        entries.append({
            "rank": rank,
            "user_id": e["user_id"],
            "best_average": e["best_average"],
            "avg_average": e["avg_average"],
            "plays": e["plays"],
        })
    return entries
