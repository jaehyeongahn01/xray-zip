# 데이터 출처 및 사진 복원

사진은 전부 제외했습니다. X-PLAY 교육용 원본 100장과 Grad-CAM 이미지도 포함하지 않았습니다.
pneumonia_labels.csv는 원본 전체 5,856장 목록입니다.
final_train_split.csv / final_val_split.csv / final_test_split.csv는 최종 환자 단위 분할을
노트북 알고리즘(seed42)으로 재생성한 목록입니다. 4,439 / 777 / 624장, train-val 환자키 겹침 0.
CSV split은 원본 폴더, training_split은 재학습용 분할입니다. 원본 val 16장은 최종 학습에서 제외됩니다.
local_path는 제거했고 relative_path와 s3_uri로 이미지를 찾습니다.

과제 제공 원본 이미지: s3://aws-say3-dataset1/pneumonia-xray/chest_xray/
게임 데이터: s3://aws-say3-student-dataset/students/aws-say3-11/P1/education_gradcam/
검토자에게 해당 S3 읽기 권한이 필요합니다. 패키지는 권한·자격증명을 포함하지 않습니다.

권한 있는 AWS 계정에서 필요할 때 직접 실행 (자동 실행하지 않음):
```bash
aws s3 sync s3://aws-say3-dataset1/pneumonia-xray/chest_xray/ 04_dataset/chest_xray/
aws s3 sync s3://aws-say3-student-dataset/students/aws-say3-11/P1/education_gradcam/ 04_dataset/education_game_review/
```
게임에는 education_game_review/images/*.png, overlay/*.png 및 questions.csv가 필요합니다.
사진 복원 없이 웹 게임·과거 이미지 검증은 할 수 없습니다. 학습도 이미지 복원이 필요합니다.
