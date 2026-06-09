# 엣지 AI 연합학습 클라이언트 이탈 관리 시스템

군산대 캡스톤디자인 — 팀 **데굴데굴** (최현식 / 이승규 / 남궁재민) · 제이디
컴퍼니 협업.

이기종 엣지 디바이스(라즈베리파이 · Jetson · Android 폰)에서 연합학습을 운영
할 때 발생하는 **클라이언트 이탈**을 예측·모니터링·제어하는 통합 플랫폼이다.
모든 핵심 구성요소(알고리즘 · 모델 · 데이터셋 · 클라이언트 선택 정책 · 이탈
예측기)는 런타임에 교체 가능한 **plug-in 레지스트리**로 구현되어 있다.

```
capstone/
├── backend/    FastAPI 기반 중앙 코디네이터
├── frontend/   React + Tailwind v4 + shadcn 라이트 톤 대시보드 (이탈 관리 패널 부각)
├── client/     Python edge 클라이언트. `pip install -e .` 후 `fl-client` 명령
├── android/    Kotlin FL 클라이언트 앱 v0.3.0 (참여자 중심 UI + WorkManager)
├── cli/        flctl — (deprecated) read-only 모니터링 CLI. 참여는 fl-client 사용
└── docs/       아키텍처 · 모듈 교체 · 시연 시나리오 · 인수인계 · 자체 호스팅
```

### 검증된 상태 (2026-06-09)
- 글로벌 MNIST acc: r5 92.39% → r20 98.75% → r275 98.98% → 이전 세션 r115 99.05%
- 글로벌 Fashion-MNIST acc: r5 57.94% (런타임에 dataset swap → 같은 모델 재사용 검증)
- 동시 라운드: 폰 1 + Edge 2 + CLI 1 (실기)
- 폰 앱: 토글 ON → 자동 학습 / 글로벌 acc / fleet / sparkline / 라이브 진행 단계 동작
- 외부 노출: localtunnel `kunsan-fl.loca.lt`

## 아키텍처 한 눈에

```
┌────────────────────────────────────────────────────────┐
│  Web 대시보드 (React)                                  │
│   · 모듈 swap UI    · 파라미터 편집  · 실시간 차트     │
│   · 클라이언트 표   · kick / ban / unban               │
└───────────────┬────────────────────────────────────────┘
                │  HTTPS / WS
┌───────────────▼────────────────────────────────────────┐
│  FL Coordinator (FastAPI, Python)                      │
│  ┌─ algorithms/   ┌─ models/    ┌─ datasets/           │
│  ┌─ selection/    ┌─ dropout/   ┌─ auth                │
│  └─ orchestrator (round loop, metric aggregation)      │
│                                                        │
│   REST  /api/...      WS  /ws/events                   │
└─┬──────────────────────────────────────────┬───────────┘
  │                                          │
  │   provisioning(id,secret)                │  admin Bearer
  │   register / heartbeat / update          │
  │                                          │
┌─▼───────────────┐  ┌────────────────┐  ┌───▼─────────────┐
│ Android FL app  │  │ Python edge    │  │ flctl (CLI)     │
│ Kotlin + okhttp │  │ client (Pi/Jet)│  │ REPL + slash    │
│ encrypted creds │  │ ~/.flclient    │  │ commands        │
└─────────────────┘  └────────────────┘  └─────────────────┘
```

## 빠른 시작

### 1) 서버

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m server.main   # http://localhost:8000
```

기본 어드민 계정은 `admin` / `admin` — 운영 시 `FL_ADMIN_USER` /
`FL_ADMIN_PASS` 환경변수로 덮어쓴다.

### 2) 웹 대시보드

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

서버 URL은 우측 상단 「change」 버튼으로 언제든 바꿀 수 있다. 빌드 시
`VITE_SERVER_URL` 환경변수로 기본값을 박을 수도 있다.

### 3) Python edge 클라이언트 (`fl-client`)

```bash
cd client
pip install -e .                              # `fl-client` 명령이 PATH에 노출됨
fl-client --server https://kunsan-fl.loca.lt  # 참여 시작
fl-client --help                              # 옵션 (--algo / --model / --dataset / --epochs / --reprovision)
```

라즈베리파이 / Jetson 에서는 PyTorch 휠을 먼저 깔고 `pip install -e .`:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -e .
```

systemd 로 상시 가동하려면 `client/systemd/fl-client.service` 샘플 참고.

### 4) Android 앱

`android/` 를 Android Studio 로 빌드하거나 미리 만든 `app-debug.apk` 설치.
첫 실행 후 「참여」 토글만 켜면 자동으로 client_id/secret 발급, 백그라운드 학습
스케줄링(Gboard 식 — 충전 + Wi-Fi + 유휴 + 배터리 50%+) 시작. 설정 변경은 헤더
우측 「설정」 다이얼로그.

```kotlin
// android/app/build.gradle.kts — 빌드 기본값 (런타임에 설정 다이얼로그로 덮어쓰기 가능)
buildConfigField("String", "DEFAULT_SERVER_URL", "\"https://kunsan-fl.loca.lt\"")
```

### 5) flctl (Node, deprecated 모니터링)

리눅스 참여는 `fl-client` (Python) 가 표준. `flctl` 은 read-only 점검 용도로만
남겨둠. 자세한 내용은 `cli/README.md`.

### 6) 시뮬레이터 (실제 디바이스 없이 데모)

```bash
cd backend && source .venv/bin/activate
python ../tools/simulate.py --clients 6 --noniid
```

라즈베리파이·Jetson·Pixel·Galaxy 등의 프로필을 흉내내는 가상 클라이언트
6개가 동시에 접속한다. 대시보드의 「FL session → Start」 누르면 실제로
PyTorch CNN 학습이 라운드별로 돌아가고 loss/accuracy 차트가 채워진다.

### 7) Docker compose (1줄 기동)

```bash
docker compose up --build
# backend  → http://localhost:8000
# dashboard→ http://localhost:5173
```

`FL_ADMIN_PASS`, `VITE_SERVER_URL` 등 환경변수로 운영 설정 덮어쓰기.

## 모듈 교체 — 모든 구성요소가 plug-in

각 카테고리는 동일한 패턴이다: `base.py` (추상 클래스) + `registry.py`
(데코레이터 기반 등록) + 기본 구현. 새 클래스를 만들어 `@register` 만 붙이면
서버에 등록되고, 대시보드의 swap 메뉴 / flctl 의 `/registry` 자동완성 / Android
스피너에 즉시 나타난다.

| 종류 | 위치 | 인터페이스 | 기본 구현 |
|---|---|---|---|
| FL 알고리즘 (집계) | `backend/server/algorithms/` | `FLAlgorithm.aggregate()` | `fedavg` |
| 모델 (글로벌 가중치) | `backend/server/models/` | `ModelSpec.initial_weights()` | `cnn_mnist` |
| 데이터셋 (파티셔닝) | `backend/server/datasets/` | `DatasetSpec.partition()` | `mnist` |
| 클라이언트 선택 | `backend/server/selection/` | `SelectionPolicy.select()` | `all`, `random`, `dropout_aware` |
| 이탈 예측기 | `backend/server/dropout/` | `DropoutPredictor.predict()` | `rule_based` |
| 클라이언트측 알고리즘 | `client/algorithms/`, `android/.../fl/` | `local_train()` | `fedavg` |
| 클라이언트측 모델 | `client/models/`, `android/.../model/` | `ModelRunner` | `cnn_mnist` |
| 클라이언트측 데이터셋 | `client/datasets/`, `android/.../data/` | `DatasetLoader` | `mnist` |

새 FL 알고리즘 예시 (`backend/server/algorithms/fedprox.py`):

```python
from .base import FLAlgorithm
from .registry import register

@register
class FedProx(FLAlgorithm):
    name = "fedprox"
    def aggregate(self, client_updates, global_weights):
        ...
```

`backend/server/algorithms/__init__.py` 에 `from . import fedprox` 한 줄 추가
하면 끝. 서버 재기동 후 대시보드의 「Pluggable modules → algorithm」 드롭다운
에 자동으로 노출된다.

## 인증 모델

| 주체 | 자격증명 | 발급 | 접근 권한 |
|---|---|---|---|
| **참여 디바이스** | `(client_id, client_secret)` | `POST /api/provision` (자동 발급) | `register`, `heartbeat`, `update` 만 |
| **어드민** | username/password → Bearer 토큰 | `POST /api/admin/login` | 파라미터 변경, 모듈 swap, kick/ban |
| **익명** | — | — | `status`, `registry`, `clients`, `metrics`, `params` 읽기 |

어드민은 대시보드 우측 「Admin login」 또는 `flctl /login` 으로 인증한다.
세션 TTL 8시간(`token_ttl_sec`).

### 클라이언트 탈락 / 차단

- `POST /api/admin/kick/{client_id}` — 즉시 deactivate + 자격증명 폐기 (재발급
  하면 다시 들어올 수 있음)
- `POST /api/admin/ban/{client_id}` — 영구 차단 (해당 ID는 재발급 불가)
- `POST /api/admin/unban/{client_id}` — 차단 해제

대시보드의 「Connected clients」 표에서 행마다 `kick` / `ban` 버튼이 어드민
에게만 노출된다.

## 실시간 메트릭

오케스트레이터는 라운드가 끝날 때마다 `(loss, accuracy)` 를 sample-weighted
평균으로 집계하고, EventBus 로 모든 WS 구독자에게 push 한다. 대시보드는
`MetricsChart.jsx` 에서 이를 누적해 라인 차트로 보여준다 (`recharts`).

REST 폴백: `GET /api/metrics` 가 동일한 누적 배열을 반환한다.

## 중앙 서버 주소가 바뀌어도 동작하도록

운영 중 서버 호스트가 바뀔 가능성을 가정해, 모든 클라이언트는 서버 URL을
**환경변수 또는 런타임 입력**으로 받는다:

| 컴포넌트 | 변경 방법 |
|---|---|
| Web 대시보드 | 헤더의 「change」 버튼 (localStorage에 저장) 또는 빌드 시 `VITE_SERVER_URL` |
| Python edge | `FL_SERVER_URL` env 또는 `--server` 플래그 |
| Android 앱 | 첫 화면의 Server URL 입력란 (EncryptedSharedPreferences) |
| flctl CLI | `FL_SERVER_URL` env, `--server` 플래그, REPL의 `/server <url>` |

## 동기 / 비동기 FL 모드

| 모드 | 라운드 경계 | 집계 시점 | 적합 |
|---|---|---|---|
| `sync` | 있음 (round_num 증가) | round_timeout 전에 도착한 클라이언트 평균 | 모델 정확도 비교 / 벤치마크 |
| `async` | 없음 (연속) | 클라이언트가 update 보낼 때마다 `g ← (1-α)·g + α·u` 블렌드 (FedAsync 스타일) | 모바일·셀룰러 등 연결 단속 환경, MQTT 와 자연스럽게 결합 |

웹 대시보드의 「FL session」 패널에서 모드를 고른 뒤 Start. 모드는 세션을
일단 Stop 한 뒤에만 바꿀 수 있다. 클라이언트(Android / Python edge)는 매
heartbeat 응답으로 현재 세션 상태와 본인 선발 여부를 받아 UI에 표시한다.

## 통신 프로토콜

지금 코드는 모두 **HTTP+WS** 위에서 동작한다. 가중치 전송 효율과 모바일
연결 안정성을 위해 미래에 **gRPC / MQTT** 로 데이터 플레인을 옮길 수 있도록
`backend/server/transport/` 에 plug-in slot이 있다. 자세한 트레이드오프는
`docs/PROTOCOL.md` 참고.

## 일정

| 단계 | 기간 | 산출물 | 상태 |
|---|---|---|---|
| 1단계 | 3월 | 이탈 예측 모듈 + heartbeat 파이프라인 | ✅ |
| 2단계 | 4월 | 실시간 모니터링 대시보드 (5초 갱신) | ✅ |
| 3단계 | 5월 | 알고리즘/모델/데이터셋/선택 정책 통합 + 어드민 제어 | ✅ |
| 4단계 | 6월 | 다기기 실증 + `fl-client` 패키징 + 폰 v0.3.0 + 이탈 관리 UI | ✅ |
| 5단계 | 6~7월 | 학과 내부망 호스팅 마이그 + 최종 보고서 / 발표 | 진행 |

## 추가 문서

- `docs/demo-scenario.md` — 발표/영상 촬영용 7컷 시연 시나리오
- `docs/handoff.md` — 컴포넌트 책임·실행 순서·인수인계 체크리스트
- `docs/self-hosting.md` — localtunnel → 학과 내부망 마이그 가이드
