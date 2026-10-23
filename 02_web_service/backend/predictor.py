"""추론 래퍼 (設計§5).

- 모델 1회 로드 후 캐싱 (Streamlit @st.cache_resource 대응).
- GradCAM 이 forward/backward hook 로 인스턴스 상태를 공유하므로, 추론 호출을
  프로세스 내 단일 threading.Lock 으로 직렬화한다.
- inference.Predictor 의 알고리즘/상수/전처리는 수정하지 않고 import 해서 호출만 한다.
"""
import threading

import config  # noqa: F401  (sys.path 삽입 보장 — inference import 전에 먼저 로드)
import inference

_PREDICTOR = None
_LOCK = threading.Lock()


def get_predictor():
    """최초 호출 시 Predictor 를 생성·캐싱한다(이후 동일 인스턴스 반환)."""
    global _PREDICTOR
    if _PREDICTOR is None:
        _PREDICTOR = inference.Predictor(config.MODEL_PATH)
    return _PREDICTOR


def _clamp_thresh(thresh):
    """thresh 를 [THRESH_MIN, THRESH_MAX] 로 방어적 클램프."""
    return max(config.THRESH_MIN, min(config.THRESH_MAX, float(thresh)))


def run_predict(pil_img, thresh):
    """추론을 직렬화해 실행. (out_dict, thresh_effective) 반환.

    thresh 는 클램프한 실효값으로 predict 에 전달하고, 그 실효값을 함께 돌려준다.
    """
    thresh_effective = _clamp_thresh(thresh)
    with _LOCK:
        out = get_predictor().predict(pil_img, thresh=thresh_effective)
    return out, thresh_effective
