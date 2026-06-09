# 통신 프로토콜 — HTTP vs gRPC vs MQTT

> "통신은 HTTP로 하는게 맞나 싶긴한데 좀더 연합학습에 최적화된 네트워크 없나"

## TL;DR

| 영역 | 추천 | 이유 |
|---|---|---|
| **컨트롤 플레인** (어드민 명령, 메트릭, 클라이언트 목록) | **HTTP + WebSocket** | 작은 JSON, 디버그·캐싱·CORS 모두 잘 풀려있고 어차피 React 대시보드가 HTTP 환경 |
| **데이터 플레인** (모델 가중치 broadcast/upload) | **gRPC bidi-stream**, 또는 클라이언트가 모바일·간헐 연결이면 **MQTT** | 가중치는 수 MB~수십 MB. JSON+HTTP는 5–10× 낭비. gRPC=대역폭 최적, MQTT=연결 끊김 회복 |

지금 코드는 단순화를 위해 **모든 것을 HTTP+WS**로 보낸다. 하지만 `backend/server/transport/`에 plug-in slot을 만들어 두었으므로, 데이터 플레인만 따로 gRPC/MQTT로 옮기는 작업은 인터페이스 한 곳만 갈아끼면 된다.

## 후보 비교

### HTTP (현재)

- **장점**: 의존성 0, 디버그(curl) 친화, 브라우저 그대로 호환
- **단점**: 가중치 같은 큰 바이너리에 JSON 직렬화 비효율, 요청-응답 사이클이 모바일 셀룰러에서 자주 끊김
- **적합한 곳**: 컨트롤 플레인, 메트릭, 어드민

### WebSocket (현재 보조)

- **장점**: 서버 → 클라이언트 push, 브라우저 호환
- **단점**: 백프레셔/재전송 의미론 없음, 메시지 보장 없음, NAT 뒤 모바일에서 idle 시 끊김
- **적합한 곳**: 대시보드 이벤트 fan-out (이미 그렇게 사용 중)

### gRPC + Protobuf

- **장점**:
  - 가중치 직렬화가 JSON 대비 5–10× 작음 (float32 배열을 그대로 packed bytes)
  - HTTP/2 multiplexing — 한 TCP 연결 위에 수많은 stream
  - bidi streaming — `Train(stream Update) returns (stream GlobalWeights)` 한 RPC 로 라운드 전체 처리 가능
  - 강타입 — `.proto` 파일이 양측 인터페이스를 동기화
- **단점**: 브라우저는 gRPC-Web 어댑터 필요, 디버그 도구 빈약, 사내 로드밸런서가 HTTP/2 지원해야 함
- **현실 사례**: Flower, FedML, NVIDIA FLARE 모두 gRPC

### MQTT (사용자 제안한 비동기 유지)

- **장점**:
  - **연결 유지가 본질** — pub/sub 모델이라 클라이언트가 reconnect 해도 토픽 구독이 복원됨. 셀룰러 모바일·BLE 게이트웨이에 강함
  - **비동기 친화** — `_run_async` 모드와 자연스럽게 맞물림. 클라이언트가 `fl/updates/<id>` 로 publish → 서버가 즉시 blend
  - **브로커 분리 가능** — 코디네이터를 무상태로 만들기 쉬움
  - QoS 0/1/2 로 신뢰성 선택 가능
- **단점**: 외부 브로커(Mosquitto, EMQX, HiveMQ) 운영 부담, 큰 메시지는 분할 필요(MQTT 5에서 완화), gRPC만큼 압축 효율은 아님 (페이로드는 여전히 사용자 책임)
- **적합한 곳**: 비동기 FL의 데이터 플레인, 특히 디바이스가 모바일/IoT

### 기타

- **WebRTC**: P2P FL 연구 prototyping용. 운영 시 시그널링/브로커 별도 필요. 본 캡스톤 범위 밖.
- **QUIC / HTTP/3**: 모바일 환경에서 HTTP/2 의 head-of-line 차단 해소. gRPC over HTTP/3 는 실험적.
- **NATS / Redis Streams**: MQTT 와 유사한 pub/sub 대안. NATS 는 가볍고 빠름, 메시지 보관에 JetStream 필요.

## 권장 운영 토폴로지

```
                ┌─────────────────────────────┐
                │   Web 대시보드 (React)      │
                └─┬───────────────────────────┘
                  │   HTTPS / WSS  (작은 JSON)
                  │
   ┌──────────────▼──────────────┐         ┌──────────────┐
   │  FL Coordinator (FastAPI)   │ ◀──────▶│  MQTT broker │ (또는 gRPC 서버)
   │  control plane + REST       │  binary │  대역폭 큰  │
   └──┬──────────────┬───────────┘  weights│  데이터 플레인│
      │ HTTPS (작은) │                      └──────┬───────┘
      │              │                              │ pub/sub
   ┌──▼──┐       ┌───▼───┐                       ┌──▼───┐
   │ CLI │       │ Android│                       │ Edge │
   │     │       │  app   │                       │  Pi  │
   └─────┘       └────────┘                       └──────┘
```

## 본 코드에서의 위치

- `backend/server/transport/base.py` — `Transport` 추상
- `backend/server/transport/{http,mqtt,grpc}_*.py` — 등록된 후보들 (현재 mqtt/grpc 는 stub)
- `backend/server/config.py` 의 `transport: str = "http"` 로 활성 transport 선택
- 실제 운영 전환 시 `mqtt_stub.py` 를 `paho.mqtt.client` 로 채우고, `_run_async` 의 `submit_update` 경로를 MQTT 토픽 구독에서 들어오게 옮기면 된다 (HTTP `POST /api/update` 는 폴백/디버그용으로 남겨도 무방).

## 결정 기준

| 질문 | 답이 "예"라면 |
|---|---|
| 클라이언트가 셀룰러 / 자주 끊김 | MQTT |
| 클라이언트가 안정적 Wi-Fi 또는 사내망 | gRPC |
| 모델이 작아 (< 1MB) | 그냥 HTTP 유지 |
| 브라우저까지 같은 채널로 통일 | HTTP + WS (gRPC-Web 은 가능하지만 추가 복잡도) |
| 비동기 FL (`mode=async`) | MQTT (자연스러움) |
| 동기 라운드 FL (`mode=sync`) | gRPC (한 stream 으로 라운드 전체 진행) |
