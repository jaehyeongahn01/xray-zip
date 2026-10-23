# 모델 학습·평가

train_final_batch16.ipynb: 최종 학습/평가 코드, ResNet18, 입력224, batch16, lr1e-4,
weight_decay1e-3, 13 epochs, seed42. 원본 v4의 batch32를 최종 실험 설정에 맞춘 제출 사본입니다.
experiments/: v1~v7 실험 노트북 소스. outputs 및 첨부 이미지는 제거했습니다.
gradcam.ipynb: Grad-CAM 및 교육 데이터 생성 코드.
download_data.ipynb: 학습 데이터 준비. 실행 전 S3 권한 확인 및 경로 설정이 필요합니다.
evaluate_final.py: 제공 모델을 로컬 test 이미지로 재평가하고 파일별 예측/분류표/혼동행렬 생성.
최종 실험의 원래 결과와 재평가 출력은 구분해서 저장합니다.

SageMaker 노트북에서 실행할 때 pneumonia_labels.csv를 실행 디렉터리에 복사하고
이미지를 data/chest_xray/에 복원하세요. OUT_BUCKET/S3_DEV_ROOT는 검토자 환경으로 변경하세요.
학습 중 S3 쓰기 셀은 검토자가 명시적으로 실행할 때만 작동합니다.

평가 예시(프로젝트 루트):
python 01_model_training/evaluate_final.py --data-root 04_dataset/chest_xray

GPU/라이브러리 버전 차이로 재학습 결과는 달라질 수 있습니다. 평가 CSV는 검증 완료된
최종 metrics.json에서 변환한 집계표이며, 이번 포장 작업에서 재학습하지 않았습니다.
