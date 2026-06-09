# HTTP / WebSocket API

기본 prefix: `/api` (REST), `/ws` (WebSocket).

## 인증 헤더

| 헤더 | 발급 방법 | 용도 |
|---|---|---|
| `X-Client-Id`, `X-Client-Secret` | `POST /api/provision` | 클라이언트 telemetry |
| `Authorization: Bearer <token>` | `POST /api/admin/login` | 어드민 조작 |

## 공개 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/status` | 현재 모듈 + 라운드 + 클라이언트 수 |
| GET | `/api/registry` | 등록된 모든 plug-in 이름 |
| GET | `/api/clients` | 클라이언트 목록 + risk 평가 |
| GET | `/api/metrics` | 라운드별 누적 (loss, accuracy, ...) |
| GET | `/api/params` | 런타임 파라미터 |
| POST | `/api/provision` | `{ client_id, client_secret }` 발급 |

## 클라이언트 telemetry (client 자격증명 필요)

| Method | Path | Body |
|---|---|---|
| POST | `/api/register` | `{ client_id, kind, os, arch, hostname, model_hw, app_version, metadata }` |
| POST | `/api/heartbeat` | `{ client_id, kind, battery, charging, network, cpu_load }` |
| POST | `/api/update` | `{ client_id, weights, num_samples, metrics }` |

## 어드민 (Bearer 토큰 필요)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/admin/login` | `{ username, password }` → `{ token, ttl_sec }` |
| POST | `/api/admin/logout` | 토큰 폐기 |
| PATCH | `/api/params` | 일부 키만 보내면 됨 |
| POST | `/api/algorithm` | `{ name }` |
| POST | `/api/model` | `{ name }` |
| POST | `/api/dataset` | `{ name }` |
| POST | `/api/selection` | `{ name }` |
| POST | `/api/dropout` | `{ name }` |
| POST | `/api/admin/kick/{client_id}` | 즉시 탈락 + 자격증명 폐기 |
| POST | `/api/admin/ban/{client_id}` | 영구 차단 |
| POST | `/api/admin/unban/{client_id}` | 차단 해제 |
| GET | `/api/admin/banned` | 차단된 client_id 목록 |

## WebSocket

`GET /ws/events` — 서버가 push 하는 JSON 메시지를 받음:

```jsonc
{ "event": "round_started",  "payload": { "round": 7, "selected": [...], "algorithm": "fedavg", ... } }
{ "event": "round_finished", "payload": { "round": 7, "metrics": { "loss": 0.21, "accuracy": 0.88, ... } } }
```

대시보드는 끊기면 1초 → 2 → 4 → … 최대 15초 backoff 로 자동 재연결한다.
