# MLOps Pipeline

이미지 데이터셋 업로드부터 자동 레이블링, 모델 학습, 실험 추적까지 한 번에 관리하는 end-to-end MLOps 파이프라인입니다.

## 주요 기능

- **이미지 업로드 & 데이터셋 관리** — 이미지를 업로드하면 Label Studio 프로젝트가 자동 생성됩니다.
- **YOLO 자동 레이블링** — ML Backend가 YOLO 모델로 사전 어노테이션을 생성합니다.
- **수동 어노테이션** — Label Studio UI로 레이블을 검토·수정합니다.
- **모델 학습** — 어노테이션이 완료된 데이터로 YOLO 모델을 학습합니다 (XPU / DirectML / CPU 자동 감지).
- **실험 추적** — MLflow로 학습 지표와 모델 아티팩트를 기록합니다.
- **모델 레지스트리** — 학습된 모델의 스테이지(None → Staging → Production)를 관리합니다.

## 기술 스택

| 역할 | 기술 |
|------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python) |
| 어노테이션 툴 | Label Studio |
| 자동 레이블링 | YOLOv11 (Ultralytics) |
| 실험 추적 | MLflow |
| 데이터베이스 | PostgreSQL (Label Studio), SQLite (job state) |
| 컨테이너화 | Docker Compose |

## 서비스 포트

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Next.js UI | 3000 | 프론트엔드 대시보드 |
| FastAPI | 8000 | 오케스트레이션 백엔드 |
| Label Studio | 8080 | 어노테이션 툴 |
| YOLO ML Backend | 9090 | 자동 레이블링 서비스 |
| MLflow | 5000 | 실험 추적 |
| PostgreSQL | 5432 | Label Studio 데이터베이스 |

## 시작하기

### 사전 요구사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Docker Compose 포함)
- [Node.js 18+](https://nodejs.org/)
- [Git](https://git-scm.com/)

### 1. 저장소 클론

```bash
git clone https://github.com/hunsibi/MLOps.git
cd MLOps
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

### 3. 서비스 시작

메모리 부족을 방지하기 위해 순서대로 시작합니다:

```bash
docker compose up postgres mlflow -d
docker compose up label-studio -d
docker compose up api ml-backend -d
```

### 4. Label Studio API Key 발급

첫 실행 후 Label Studio API Key를 `.env`에 등록해야 합니다:

```bash
# 로그인 및 쿠키 획득
curl -s http://localhost:8080/user/login -c /tmp/ls_cookies.txt -o /dev/null
CSRF=$(grep csrftoken /tmp/ls_cookies.txt | awk '{print $NF}')
curl -s -b /tmp/ls_cookies.txt -c /tmp/ls_cookies.txt \
  -X POST http://localhost:8080/user/login \
  -H "X-CSRFToken: ${CSRF}" -H "Referer: http://localhost:8080/" \
  -d "csrfmiddlewaretoken=${CSRF}&email=admin%40mlops.local&password=adminpassword" -L -o /dev/null

# API Key 출력
curl -s -b /tmp/ls_cookies.txt http://localhost:8080/api/current-user/token

# Legacy token 인증 활성화 (Label Studio 1.23+ 필수)
CSRF=$(grep csrftoken /tmp/ls_cookies.txt | awk '{print $NF}')
curl -s -b /tmp/ls_cookies.txt -X POST http://localhost:8080/api/jwt/settings \
  -H "Content-Type: application/json" -H "X-CSRFToken: ${CSRF}" -H "Referer: http://localhost:8080/" \
  -d '{"legacy_api_tokens_enabled": true}'
```

출력된 토큰을 `.env`의 `LABEL_STUDIO_API_KEY`에 붙여넣고 서비스를 재시작합니다:

```bash
docker compose restart api ml-backend
```

### 5. 프론트엔드 시작

```bash
cd ui
npm install
npm run dev
```

브라우저에서 http://localhost:3000 을 엽니다.

## 아키텍처

```
[ Next.js UI ]
      │  REST
      ▼
[ FastAPI :8000 ] ──── Label Studio API ──── [ Label Studio :8080 ]
      │                                              │
      │  subprocess                           predict webhook
      ▼                                              ▼
[ train.py ] ──── MLflow ────────────    [ ML Backend :9090 ]
                  [ :5000 ]                  (YOLO inference)
```

### 데이터 흐름

**업로드 → 자동 레이블링:**
1. 사용자가 `/api/v1/datasets/upload`로 이미지 업로드
2. FastAPI가 이미지 저장 후 Label Studio 프로젝트 & 태스크 자동 생성
3. Label Studio가 ML Backend의 `POST /predict`를 호출해 자동 어노테이션 생성

**레이블링 → 학습:**
1. 사용자가 `/api/v1/training/jobs`로 학습 시작
2. FastAPI가 Label Studio에서 어노테이션을 export하여 train/val/test 분할
3. `train.py` 서브프로세스 실행 → MLflow에 지표 기록 및 모델 등록

**모델 레지스트리:**
- MLflow Model Registry에서 None → Staging → Production 스테이지 관리
- Production 모델이 다음 자동 레이블링에 사용됨

## 디렉터리 구조

```
MLOps/
├── docker-compose.yml
├── .env.example
├── services/
│   ├── api/             # FastAPI 오케스트레이터
│   ├── ml_backend/      # YOLO ML Backend (Flask/Gunicorn)
│   └── trainer/         # 학습 스크립트 (train.py, dataset_builder.py)
├── ui/                  # Next.js 프론트엔드
│   └── app/
│       ├── datasets/    # 데이터셋 관리
│       ├── labeling/    # Label Studio iframe
│       ├── training/    # 학습 작업 관리
│       ├── models/      # 모델 레지스트리
│       └── experiments/ # MLflow 실험
├── data/                # 공유 데이터 볼륨 (gitignore)
├── models/              # YOLO 모델 가중치 (gitignore)
└── mlflow/              # MLflow DB & 아티팩트 (gitignore)
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LABEL_STUDIO_API_KEY` | Label Studio API 토큰 **(필수)** | — |
| `LABEL_STUDIO_USERNAME` | Label Studio 관리자 이메일 | `admin@mlops.local` |
| `LABEL_STUDIO_PASSWORD` | Label Studio 관리자 비밀번호 | `adminpassword` |
| `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 | `labelstudio_password` |
| `YOLO_PRETRAINED_MODEL` | 자동 레이블링에 사용할 YOLO 가중치 | `yolo11n.pt` |
| `NEXT_PUBLIC_API_URL` | 프론트엔드에서 FastAPI 주소 | `http://localhost:8000` |

## 유용한 명령어

```bash
# 서비스 로그 확인
docker logs mlops-api --tail=50 -f
docker logs mlops-ml-backend --tail=50 -f
docker logs mlops-mlflow --tail=50 -f

# 특정 서비스 재빌드
docker compose build api
docker compose up api --force-recreate -d

# 전체 스택 중지
docker compose down
```

## 라이선스

MIT
