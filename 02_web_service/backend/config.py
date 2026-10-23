"""백엔드 전역 설정 — 모든 외부 경로 상수를 여기 한 곳에 모은다(FR-1.4).

app.py 최상단에서 가장 먼저 import 되어야 한다. 여기서 webapp/ 디렉터리를
sys.path 맨 앞에 삽입하므로, 이 모듈이 로드된 뒤라야 inference / game_logic 를
무수정으로 import 할 수 있다(設計). 비밀/자격증명은 두지 않는다.
"""
import os
import sys

# 워크스페이스 루트 (절대경로 고정, 設計)
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(WORKSPACE_ROOT, "frontend", "dist")

WEBAPP_DIR = os.path.join(WORKSPACE_ROOT, "streamlit")
MODEL_PATH = os.path.normpath(os.path.join(WORKSPACE_ROOT, "..", "03_model_and_results", "best_model.pth"))

# 게임 데이터는 game_logic 이 자기 기준 상대경로로 찾으므로 참조/검증 용도로만 둔다.
GAME_DIR = os.path.normpath(os.path.join(WORKSPACE_ROOT, "..", "04_dataset", "education_game_review"))

# 쓰기가 허용되는 유일한 경로 (워크스페이스 루트 안)
DATA_DIR = os.environ.get("CXR_DATA_DIR", os.path.join(WORKSPACE_ROOT, "backend", "data"))
RECORDS_PATH = os.path.join(DATA_DIR, "records.json")

# CORS 허용 origin (와일드카드 금지, NFR-6)
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# 기본/실효 문턱값
DEFAULT_THRESH = 0.7
THRESH_MIN = 0.3
THRESH_MAX = 0.9

# ---- 관리자 시드 계정 ----
# 서버 기동 시 이 계정이 없으면 자동 생성한다(app.py lifespan).
# records.json 을 비우거나 지워도 항상 되살아나 로그인 확인용으로 쓸 수 있다.
# 비밀번호는 저장 시 salt+sha256 으로 해시되며 평문은 파일에 남지 않는다.
# 기본 비번은 운영 전환 시 환경변수 ADMIN_PASSWORD 로 덮어쓰는 것을 권장한다.
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "admin")
ADMIN_NAME = os.environ.get("ADMIN_NAME", "관리자")
ADMIN_OCCUPATION = "기타"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "0000")

# webapp 모듈(inference / game_logic) import 가능하게 경로 삽입 (設計)
if WEBAPP_DIR not in sys.path:
    sys.path.insert(0, WEBAPP_DIR)

# JSON remains the default until DynamoDB migration is verified.
REPOSITORY_BACKEND = os.environ.get("CXR_REPOSITORY", "sqlite")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

SQLITE_PATH = os.path.join(DATA_DIR, "xray-zip.sqlite3")
S3_BUCKET = os.environ.get("CXR_S3_BUCKET", "aws-say3-student-dataset")
S3_PREFIX = os.environ.get("CXR_S3_PREFIX", "students/aws-say3-11/P1/readings")
COOKIE_SECURE = os.environ.get("CXR_COOKIE_SECURE", "0") == "1"
