"""추론 + Grad-CAM 모듈.
gradcam.ipynb에서 검증된 로직을 옮겨 웹앱에서 재사용한다.
- 모델 로드 (체크포인트 dict의 model_state 키 대응)
- 학습과 동일한 eval 전처리
- Grad-CAM 직접 구현 (layer4[-1] feature map x gradient)
- heatmap / overlay 생성
"""
import io
import os

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as T

# ---- 상수 (학습 config와 동일) ----
CLASS_NAMES = ["NORMAL", "BACTERIAL_PNEUMONIA", "VIRAL_PNEUMONIA"]
CLASS_NAMES_KR = ["정상", "세균성 폐렴", "바이러스성 폐렴"]
NUM_CLASSES = 3
IMG_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_eval_tf = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(MEAN, STD),
])


def build_model():
    """학습 때와 동일한 구조: ResNet18 + fc(512->3)."""
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
    return model


def load_model(model_path):
    """로컬 .pth에서 모델 로드. 체크포인트 dict(model_state 키) 대응.
    가중치가 제대로 안 들어오면 RuntimeError (조용한 실패 방지).
    """
    ckpt = torch.load(model_path, map_location=DEVICE, weights_only=False)
    state = ckpt
    if isinstance(ckpt, dict):
        for k in ("model_state", "model", "state_dict"):
            if k in ckpt and isinstance(ckpt[k], dict):
                state = ckpt[k]
                break
        if "class_names" in ckpt and list(ckpt["class_names"]) != CLASS_NAMES:
            raise RuntimeError(
                f"클래스 순서 불일치: ckpt={ckpt['class_names']} vs {CLASS_NAMES}"
            )
    model = build_model()
    missing, _ = model.load_state_dict(state, strict=False)
    if missing:
        raise RuntimeError(f"가중치 로드 실패: {len(missing)}개 키 미채움 (예: {missing[:3]})")
    model.to(DEVICE).eval()
    return model


class GradCAM:
    """ResNet18 Grad-CAM. target_layer의 activation/gradient로 히트맵 생성."""

    def __init__(self, model, target_layer):
        self.model = model
        self.activations = None
        self.gradients = None
        self._fwd = target_layer.register_forward_hook(self._save_act)
        self._bwd = target_layer.register_full_backward_hook(self._save_grad)

    def _save_act(self, m, i, o):
        self.activations = o.detach()

    def _save_grad(self, m, gi, go):
        self.gradients = go[0].detach()

    def __call__(self, x, class_idx=None):
        self.model.zero_grad()
        logits = self.model(x)
        probs = F.softmax(logits, dim=1)[0].detach().cpu().numpy()
        if class_idx is None:
            class_idx = int(logits.argmax(dim=1).item())
        logits[0, class_idx].backward()

        grads = self.gradients[0]
        acts = self.activations[0]
        weights = grads.mean(dim=(1, 2))
        cam = F.relu((weights[:, None, None] * acts).sum(dim=0))
        cam = F.interpolate(cam[None, None], size=(IMG_SIZE, IMG_SIZE),
                            mode="bilinear", align_corners=False)[0, 0]
        cam = cam.cpu().numpy()
        cam -= cam.min()
        if cam.max() > 0:
            cam /= cam.max()
        return cam, class_idx, probs


# ---- 시각화 (matplotlib 없이 PIL/numpy로 jet 컬러맵 근사) ----
def _jet(cam):
    """cam(H,W 0~1) → RGB uint8 heatmap. jet 컬러맵 근사 (의존성 최소화)."""
    x = np.clip(cam, 0, 1)
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def make_overlay(pil_img, cam, alpha=0.45):
    """원본(224) 위에 전체 heatmap 합성 → RGB uint8."""
    base = np.asarray(pil_img.resize((IMG_SIZE, IMG_SIZE)).convert("RGB")).astype(np.float32)
    heat = _jet(cam).astype(np.float32)
    over = (1 - alpha) * base + alpha * heat
    return np.clip(over, 0, 255).astype(np.uint8)


def make_overlay_thresh(pil_img, cam, thresh=0.7, alpha=0.6):
    """CAM이 thresh 이상인 핵심 영역만 색칠, 나머지는 원본."""
    base = np.asarray(pil_img.resize((IMG_SIZE, IMG_SIZE)).convert("RGB")).astype(np.float32)
    heat = _jet(cam).astype(np.float32)
    mask = (cam >= thresh).astype(np.float32)[..., None]
    over = base * (1 - alpha * mask) + heat * (alpha * mask)
    return np.clip(over, 0, 255).astype(np.uint8)


class Predictor:
    """모델 + Grad-CAM을 묶어 한 번에 예측/시각화."""

    def __init__(self, model_path):
        self.model = load_model(model_path)
        self.gradcam = GradCAM(self.model, self.model.layer4[-1])

    def predict(self, pil_img, thresh=0.7, display_max=640):
        """PIL 이미지 → dict. 표시용 이미지는 원본 가로세로 비율을 유지한다.

        추론/CAM은 224x224 정사각형에서 계산하지만, 화면에는 원본 비율로 보여주려고
        overlay(224 정사각)를 다시 '원본 비율'로 리사이즈해서 원본과 모양을 맞춘다.
        display_max: 표시용 긴 변 최대 픽셀 (비율 유지).
        """
        pil_img = pil_img.convert("RGB")
        W, H = pil_img.size
        # 추론은 224 정사각 기준
        x = _eval_tf(pil_img).unsqueeze(0).to(DEVICE)
        cam, pred_idx, probs = self.gradcam(x)

        # 표시용 원본: 비율 유지, 긴 변을 display_max로
        scale = display_max / max(W, H)
        disp_w, disp_h = max(1, int(W * scale)), max(1, int(H * scale))
        disp_img = pil_img.resize((disp_w, disp_h))

        # overlay(224 정사각)를 원본 비율(disp 크기)로 리사이즈해 원본과 모양 일치
        overlay_sq = Image.fromarray(make_overlay(pil_img, cam)).resize((disp_w, disp_h))
        overlay_th_sq = Image.fromarray(make_overlay_thresh(pil_img, cam, thresh=thresh)).resize((disp_w, disp_h))

        return {
            "probs": probs,
            "pred_idx": pred_idx,
            "pred_kr": CLASS_NAMES_KR[pred_idx],
            "cam": cam,
            "overlay": np.asarray(overlay_sq),
            "overlay_thresh": np.asarray(overlay_th_sq),
            "resized": np.asarray(disp_img),
        }
