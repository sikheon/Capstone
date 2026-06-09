# 인수인계 (HANDOFF)

군산대 캡스톤 — 팀 **데굴데굴** × 제이디컴퍼니. 이 문서를 읽고 5분 안에
시스템을 띄우고 멈추고 들여다볼 수 있어야 합니다.

## 1. 한 줄 요약

> 이종 엣지 디바이스(Android / Pi / Jetson / Linux x86)에서 연합학습을 운영
> 하면서 **누가 떨어질 것 같은지** 를 예측·표시·제어하는 통합 플랫폼.

## 2. 컴포넌트 책임 매트릭스

| 폴더 | 무엇 | 누가 쓰나 | 핵심 진입점 |
| --- | --- | --- | --- |
| `backend/` | 중앙 코디네이터(라운드 루프, 집계, 인증, 이탈 예측) | 운영자 1대 | `python -m server.main` (uvicorn) |
| `frontend/` | 운영 대시보드 (어드민) | 운영자 브라우저 | `npm run dev` |
| `client/` | Python 엣지 참여 클라 (PyTorch) | Pi · Jetson · Linux x86 | `pip install -e . && fl-client` |
| `android/` | Kotlin 폰 참여 앱 | 일반 사용자 폰 | APK 설치 + 「참여」 토글 |
| `cli/` | (deprecated) Node 모니터링 CLI | 데모용 | `flctl` |
| `tools/simulate.py` | 가상 클라이언트 N대 시뮬레이터 | 실 디바이스 없는 데모 | `python tools/simulate.py --clients 6` |
| `docs/` | 시연 시나리오·인수인계·자체 호스팅 가이드 | 다음 운영자 | (이 문서들) |

## 3. 5분 안에 동작 확인

```powershell
# 1) 백엔드
cd backend; .\.venv\Scripts\activate
$env:PYTHONUNBUFFERED='1'; $env:PYTHONIOENCODING='utf-8'
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# 2) 외부 노출(폰 데모용)
npx localtunnel --port 8000 --subdomain kunsan-fl

# 3) 대시보드
cd ..\frontend; npm run dev    # http://localhost:5173 / admin/admin

# 4) Python 엣지 1대 (모두 같은 PC도 OK — 본인을 클라로 등록)
cd ..\client; pip install -e .
fl-client --server http://localhost:8000

# 5) 폰 (USB 연결 → APK 설치 → 토글 ON)
adb install -r app-debug.apk
adb shell am start -n com.capstone.fl/.MainActivity
```

이 시점에 대시보드:
- KPI strip: `state=running`, `mode=async`, `clients ≥ 2`
- **이탈 위험 관리** 패널: 활성 클라이언트 수 + 위험 분포 + 상위 3명 와치리스트
- MetricsChart: train acc 우상향
- GlobalModel: test acc (~5 업데이트마다 갱신)
- ClientsTable: kind 별로 행 추가 (edge / android)

## 4. 어드민 비밀번호

기본값 `admin` / `admin`. 실배포 시 백엔드 띄우기 전에:

```powershell
$env:FL_ADMIN_USER = 'kunsan-fl-admin'
$env:FL_ADMIN_PASS = '<강한 패스워드>'
```

토큰 TTL 8시간(`backend/server/auth.py: token_ttl_sec`).

## 5. 자주 만지게 될 파일

| 의도 | 위치 | 비고 |
| --- | --- | --- |
| 라운드 자동 회전 속도 조정 | `backend/server/core/orchestrator.py:54` | `_async_eval_every_updates` (글로벌 평가 빈도) |
| 어드민 토큰 TTL | `backend/server/auth.py` | `token_ttl_sec` |
| 이탈 위험 룰 | `backend/server/dropout/predictor.py` | risk 가중치 조정 |
| 폰 기본 서버 URL | `android/app/build.gradle.kts` | `DEFAULT_SERVER_URL` (런타임 변경 가능하므로 굳이 안 만져도 됨) |
| 폰 Worker 주기 | `android/app/.../worker/FLScheduler.kt` | `15, TimeUnit.MINUTES` (Gboard 식 제약 + WorkManager 최소값) |
| Web 디자인 토큰 | `frontend/src/styles.css` | 라이트 + 바이올렛 (HSL 263 70% 53%) |

## 6. 새 모듈 추가 (plug-in)

모든 plug-in 카테고리(알고리즘 / 모델 / 데이터셋 / selection / dropout) 패턴
동일:

```python
# backend/server/<category>/<your_name>.py
from .base import <BaseClass>
from .registry import register

@register
class YourImpl(<BaseClass>):
    name = "your_name"
    def predict(self, state):    # 또는 aggregate / partition / select / load
        ...
```

`backend/server/<category>/__init__.py` 에 `from . import your_name` 한 줄
추가. 서버 재기동 후 대시보드 Registry 패널 + flctl `/registry` + 폰 (해당
필드 사용 시) 에 자동 노출.

## 7. 데이터셋 추가 시 클라이언트 측 영향

서버에 데이터셋 plug-in 만 추가하면 어드민이 swap 할 수 있지만, **실제
학습은 클라이언트가 가지고 있어야** 합니다. 동일 이름의 클라이언트측
구현이 다음 두 곳에 추가되어야 합니다:

- `client/datasets/<name>.py` — Python edge
- `android/app/.../data/<Name>Loader.kt` — Android

이 둘은 서버 `DatasetSpec.partition()` 와 약속된 shape/label 을 따라야
합니다. 자세한 패턴은 `mnist` 구현 참고.

## 8. 검증된 성능 (인계 시점)

| 항목 | 값 |
| --- | --- |
| 글로벌 모델 acc (MNIST CNN, async, 단일 폰+엣지) | 라운드 5에서 92.39%, 라운드 20에서 98.75%, 이전 세션 r115에서 99.05% |
| 폰 라운드 1회 wall-clock (S22 Ultra) | 약 1–3초 (Wi-Fi + 충전 + idle 만족 시 백그라운드) |
| 어드민 액션 → 클라이언트 반영 | heartbeat 주기(5초) 이내 |
| WS 이벤트 → 대시보드 반영 | < 200ms |

## 9. 알려진 한계 / 다음 사람이 할 일

- **현재 데이터셋 2개** (MNIST / Fashion-MNIST). 둘 다 28×28 grayscale 10-class 라
  같은 모델(`cnn_mnist`) 재사용. 3채널·다른 해상도(CIFAR-10) 가려면 새 model
  plug-in(`cnn_cifar10`) + DatasetSpec 추가 + evaluator `_KNOWN_TESTS` 갱신 필요.
- **이탈 예측기는 규칙 기반 1개** (`rule_based`). 학습 기반 (LSTM/시퀀스) 으로 교체할 자리 있음(`backend/server/dropout/`).
- **HTTP+WS 단일 transport**. 모바일 셀룰러 환경에선 MQTT/gRPC 가 더 적합. `backend/server/transport/` plug-in slot 활용.
- **localtunnel 의존**. 외부 노출 본격화하려면 학과 내부망/도메인 + Caddy + Let's Encrypt 로 마이그. `docs/self-hosting.md` 참고.
- **단일 모델 서버**. 모델이 커지면 가중치를 매 라운드 통째로 보내는 게 부담. delta 압축 자리 있음.

## 10. 비상 연락 / 환경

- 현재 운영 PC: `DESKTOP-E8C4EI7` (Windows 11 Pro, Python 3.12 venv `backend/.venv`)
- 폰: 갤럭시 S22 Ultra (`R3CT808KNYD`)
- 폰 라파이 SSH: `ssh jongseo-pi` (BYOAI 프로젝트와 공용 — capstone 에는 직접 사용 X)
- 외부 도메인: `https://kunsan-fl.loca.lt` (localtunnel — 재시작하면 새로 떠야)
- 사용자: sikeon3329@kunsan.ac.kr
