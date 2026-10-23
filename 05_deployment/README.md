# 실행 환경 (평가자용)

여기는 에이전트 도구 폴더가 아닙니다. 의존성 목록과 로컬 서버 시작 스크립트만 포함했습니다.
스크립트는 AWS에 접속하거나 리소스를 만들지 않습니다.
SSH 접속, IAM 변경, EC2 시작/중지, 자동 업로드, 에이전트 작업 파일은 없습니다.

실제 운영 구성: 서울 리전 EC2 t3.small / Python 3.12 / CPU PyTorch /
Uvicorn worker 1 / 포트 8501 / systemd 자동실행 / EBS의 SQLite / S3 이미지 저장.
이 구성 설명만 포함하며 실제 EC2 접속키·운영 서비스 설치 스크립트는 제외했습니다.

가상환경 활성화 후 필요한 requirements를 설치하고 프로젝트 루트에서 실행:
- bash 05_deployment/run_backend.sh
- bash 05_deployment/run_streamlit.sh
React 개발 서버는 02_web_service/frontend에서 npm ci 후 npm run dev.
공개 운영에는 HTTPS와 별도 인증·백업 설정 검토가 필요합니다.
