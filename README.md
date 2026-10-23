# XRAY ZIP — 소스코드 및 데이터 제출

안재형 / 2026-10-22

## 구조
- 01_model_training: 최종 ResNet18 학습 노트북, 실험 노트북, Grad-CAM, 평가 코드.
- 02_web_service: React 프론트엔드, FastAPI 백엔드, 판독·게임 공용 로직 및 기존 Streamlit.
- 03_model_and_results: best_model.pth, 최종 평가 CSV, 실험별 metrics/config.
- 04_dataset: 전체 라벨·최종 Train/Val/Test CSV, questions.csv, 사진 복원 안내.
- 05_deployment: 의존성·실행 스크립트·EC2 구성 설명. AWS 접속 자동화 파일은 없음.

사진은 사용자 요청에 따라 모두 제외했습니다. X-PLAY 100문제는 questions.csv만 포함합니다.
각 폴더를 같은 부모 폴더에 유지하세요. 모델·공용 코드·게임 데이터 참조 경로를 조정했습니다.

## 현재 웹 실행
Python 3.12 가상환경을 활성화하고:
```bash
pip install -r 05_deployment/requirements-backend.txt
export ADMIN_PASSWORD=1234
bash 05_deployment/run_backend.sh
```
별도 터미널에서 02_web_service/frontend로 이동 후 npm ci, npm run dev.
게임 이미지 복원은 04_dataset/README.md 참고. 관리자 ID admin, 최초 생성 시 지정한 비밀번호.
제출 사본의 기본 관리자 비밀번호는 운영값 대신 데모 0000입니다.
SQLite는 첫 실행에 생성되며 운영 회원·기록·세션 DB는 제외했습니다.
React 빌드(npm run build) 후 FastAPI가 화면까지 제공합니다.

판독 이력 저장은 S3 권한 및 CXR_S3_BUCKET/CXR_S3_PREFIX/AWS_REGION 설정이 필요합니다.
AWS 설정 없이도 추론은 가능하나 사진 저장 실패 메시지가 표시될 수 있습니다.
Streamlit은 requirements-streamlit.txt 설치 후 bash 05_deployment/run_streamlit.sh.

## 데이터·결과·AWS
과제 제공 데이터 출처와 복원 명령은 04_dataset에 있습니다.
최종 모델 test accuracy 0.8766 / macro-F1 0.8662. 기존 실험 저장값이며 새 재학습 결과가 아닙니다.
실험 당시 SageMaker 노트북으로 학습, S3로 데이터/모델 보관, EC2에서 CPU 추론·웹 운영.
현재 회원·게임·판독 정보는 SQLite, 판독 사진은 S3, 역할 권한은 IAM 사용.
DynamoDB는 채택하지 않아 관련 코드는 제외했습니다.

## 제외한 파일
Kiro/에이전트 지시·작업 로그(.agents/.codex/AGENTS.md 등), AWS/SSH 접속키,
자격증명/.env, EC2 시작·종료·권한 변경·자동 배포 도구, 운영 점검 스크립트,
실제 회원 DB·업로드 사진, node_modules/빌드/캐시, 내부 인수인계 문서.

S3를 사용하는 학습·판독 저장 코드는 서비스 자체 기능이므로 포함했습니다.
이 코드는 에이전트가 AWS를 제어하기 위한 파일과는 다릅니다.
원본 프로젝트를 변경하지 않고 제출용 사본만 구성했습니다.
