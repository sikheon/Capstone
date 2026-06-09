# Architecture

전체 시스템은 **중앙 코디네이터**(FastAPI) 한 대와, 그에 붙는 **이기종 클라이언트**(Android / 라즈베리파이·Jetson 파이썬 / flctl CLI / 웹 대시보드)들로 구성된다. 통신은 평이한 HTTP + 단일 WebSocket 채널(이벤트 stream)로만 일어난다.

## 데이터 흐름

```
[ Android / Edge ]                 [ Server ]                  [ Web Dashboard ]
        │                              │                              │
   POST /api/provision  ────────────▶  │                              │
        │   ◀───── { client_id, secret }                              │
        │                              │                              │
   POST /api/register  (+secret) ───▶  │                              │
   POST /api/heartbeat (+secret) ───▶  client_manager.upsert()        │
        │                              │                              │
        │                              orchestrator._run_round(r)     │
        │                              ├─ selection.select(...)       │
        │   ◀── (out-of-band fetch     │                              │
        │       global_weights once    │                              │
        │       per round in future)   │                              │
   POST /api/update    (+secret) ───▶  algorithm.aggregate(updates)   │
        │                              ├─ EventBus.publish("round_finished")
        │                              │                              │
        │                              WS  /ws/events  ─────────────▶ MetricsChart.append()
```

## 핵심 경계

1. **알고리즘 / 모델 / 데이터셋 / 선택 정책 / 이탈 예측기** — 모두 *추상 클래스 + 레지스트리* 패턴. 새 구현을 한 파일에 추가하고 `__init__.py` 에 `import` 한 줄 추가하면 시스템 전체에 노출된다.

2. **인증 경계** — 두 종류뿐:
   - *클라이언트* 자격증명 `(X-Client-Id, X-Client-Secret)` : telemetry 엔드포인트(register/heartbeat/update)에서만 검증.
   - *어드민* Bearer 토큰 : 모든 변경(`patch /params`, `post /algorithm` 등)과 관리(`kick`/`ban`)에서 검증.

3. **서버 주소 의존성** — 클라이언트 코드 내에 호스트가 박혀있지 않다. 모두 런타임 입력(환경변수·플래그·UI)으로 받고, 클라이언트는 새 서버에서 다시 `provision` 한다.

## 디렉토리 의도

| 경로 | 책임 |
|---|---|
| `backend/server/algorithms/` | 서버측 집계 (FedAvg, FedProx, q-FedAvg, …) |
| `backend/server/models/` | 글로벌 모델 메타데이터 + 초기 가중치 |
| `backend/server/datasets/` | 데이터셋 메타데이터 + 클라이언트 파티셔닝 정책 |
| `backend/server/selection/` | 어떤 클라이언트를 다음 라운드에 부를지 결정 |
| `backend/server/dropout/` | client_state → (risk, reasons) 매핑 |
| `backend/server/core/orchestrator.py` | 라운드 루프, 메트릭 집계, swap dispatch |
| `backend/server/core/client_manager.py` | 등록된 클라이언트 상태 캐시 (thread-safe) |
| `backend/server/auth.py` | in-memory 자격증명 저장소, ban 리스트 |
| `backend/server/api/rest.py` | 모든 HTTP 엔드포인트 + Depends 기반 권한 |
| `backend/server/api/ws.py` | EventBus + `/ws/events` 핸들러 |
| `frontend/src/api/{client,ws}.js` | REST + WS 래퍼 (admin token / server URL 동적) |
| `frontend/src/components/` | 화면 단위 (헤더, 상태, 레지스트리, 파라미터, 표, 차트) |
| `client/{algorithms,models,datasets}/` | edge 측 동일 구조의 plug-in |
| `client/credentials.py` | `~/.flclient/credentials.json` 영속화 |
| `cli/flctl/commands.py` | 슬래시 커맨드 등록부 (Claude Code 스타일) |
| `android/app/.../{fl,model,data}/` | 모바일 측 동일 구조의 plug-in |

## 라운드 루프 (orchestrator)

```
while running:
  pool      = clients.all().active()                 # 살아있는 후보만
  selected  = selection.select(pool, r, fraction, min_clients)
  if auto_dropout_control:
      selected = selected − { c | c.dropout_risk ≥ threshold }
  if len(selected) < min_clients: continue

  emit("round_started", { round, selected, ... })

  wait until len(received) == len(selected) or timeout
  global_weights = algorithm.aggregate(received, global_weights)
  metrics        = weighted_avg(received.metrics, by num_samples)
  emit("round_finished", { round, metrics, ... })
```

`set_algorithm` / `set_model` / `set_dataset` / `set_selection` 은 모두 *다음
라운드부터* 적용된다 — 진행 중인 라운드를 죽이지 않는다.

## 확장 시나리오

| 하고 싶은 일 | 만져야 하는 곳 |
|---|---|
| **새 FL 알고리즘 추가** | `backend/server/algorithms/<name>.py` + `algorithms/__init__.py` import |
| **이탈 예측을 ML 모델로 교체** | `backend/server/dropout/ml_model.py` 에 `DropoutPredictor` 구현 |
| **모델을 PyTorch 진짜 모델로 교체** | `client/models/cnn_mnist.py` 의 `train()`/`get_weights()` 만 변경 |
| **Android 측 모델을 TFLite 로 교체** | `android/.../model/CnnMnistRunner.kt` 만 다시 작성 |
| **인증을 DB / OAuth 로 교체** | `backend/server/auth.py` 의 `AuthManager` 만 다른 구현으로 |
| **WS 이벤트 추가** | `orchestrator._emit("event", payload)` + 프론트 `App.jsx` switch |
