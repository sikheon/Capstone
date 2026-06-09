# 시연 시나리오 — 엣지 AI 연합학습 클라이언트 이탈 관리

군산대 캡스톤디자인 · 팀 **데굴데굴**(최현식·이승규·남궁재민) × 제이디컴퍼니.
발표·영상 촬영용 5분 시나리오. 모든 단계는 검증된 동작이며 별도 트릭 없음.

---

## 등장 컴포넌트

| 역할 | 도구 | 위치 |
| --- | --- | --- |
| 중앙 코디네이터 | FastAPI + uvicorn | `backend/` |
| 어드민 웹 | React + Tailwind v4 + shadcn | `frontend/` |
| 안드로이드 참여자 | Kotlin + WorkManager | `android/` (APK v0.3.0+) |
| Edge 참여자 | Python + PyTorch | `pip install -e ./client` → `fl-client` |
| 외부 노출 | localtunnel | `kunsan-fl.loca.lt` |

## 사전 준비 (촬영 전 5분)

```powershell
# 1) 백엔드 + 터널
Set-Location C:\Users\HS\capstone\backend
.\.venv\Scripts\python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
npx localtunnel --port 8000 --subdomain kunsan-fl

# 2) 어드민 웹
cd ..\frontend; npm run dev          # http://localhost:5173

# 3) 폰
adb install -r app-debug.apk        # 처음 한 번만
```

폰 서버 URL은 빌드 기본값 `https://kunsan-fl.loca.lt` 으로 설정되어 있음.

---

## 컷 1 — "동기·비동기 둘 다 된다" (60s)

1. 웹 대시보드 열기. KPI 6개 (accuracy / loss / state / mode / round / clients) 비어 있음.
2. 어드민 로그인 (헤더 우측 admin/admin). Session Control에서 **Async 시작**.
3. KPI `state: running`, `mode: async`로 전환. 라운드 0 / 클라 0.

**보여주려는 것:** 시작 전엔 학습이 안 돌고 있고, 시작 즉시 라운드가 회전한다.

---

## 컷 2 — Edge 참여자 join (45s)

```powershell
fl-client --server http://localhost:8000
```

콘솔에 `[edge] provisioned id=…` → `[edge] async tick - pushing update` 로그.

대시보드: `clients: 1`, MetricsChart에 train loss/accuracy 곡선이 그려지기 시작.
ClientsTable에 `kind=edge / OS=Windows / network=wifi / cpu_load≈0.3` 행 추가.

**보여주려는 것:** 한 줄로 리눅스/Windows/Pi 누구든 즉시 참여 가능.

---

## 컷 3 — 폰 참여자 join (60s)

폰에서 앱 실행 (FL Client).
- 헤더 우측 **설정** → 서버 URL 확인 (이미 `kunsan-fl.loca.lt`).
- 메인 카드의 **참여 토글 ON** → 상태 dot 회색 → 보라, 라벨 "대기 중" → "참여 중".
- 충전 케이블 연결 → "학습 조건" 카드의 ✓ 4개가 모두 초록으로 채워짐.
- 잠시 후 stateLabel "학습 중…" 으로 바뀌고 progress bar 가 흐름.
- 학습 완료되면 KPI "내 기여 라운드 1", "내 마지막 정확도 9x.xx%" 로 갱신.

대시보드 ClientsTable에 `kind=android / model_hw=SM-S908N` 새 행.

**보여주려는 것:**
- 같은 라운드 루프에 폰이 즉시 합류.
- 폰은 사용자가 토글 하나만 누르면 끝 — 알고리즘/모델/데이터셋을 고를 필요가 없음 (서버 책임).

---

## 컷 4 — 글로벌 학습이 실제로 개선됨 (45s)

대시보드 MetricsChart: train acc가 라운드마다 우상향. 5라운드(또는 5회 update)마다 GlobalModel 패널의 **test accuracy** 가 새로 찍힘.

폰 KPI **글로벌 정확도** = 같은 값이 `round N · test` 로 동기화.

**보여주려는 것:** 폰·Edge가 각자 자기 데이터로만 학습하지만 합쳐서 글로벌 모델이
실제로 좋아진다 (= 연합학습이 "동작한다").

---

## 컷 5 — 함께 학습 중인 디바이스 표시 (30s)

폰 앱의 **함께 학습 중인 디바이스** 카드 — 안드로이드/엣지/CLI 그룹별 카운트.
새 fl-client를 한 대 더 띄우면 카드의 "엣지" 숫자가 +1.

**보여주려는 것:** 폰에서도 다른 참여자가 실시간으로 보임 = 연합학습의 "다중성" 체감.

---

## 컷 6 — 이탈 관리 (90s · 본 캡스톤의 메인 컷)

발표 직전 별도 터미널에서 위험 시뮬을 미리 띄워둔다:

```powershell
python tools/simulate.py --server http://localhost:8000 `
    --clients 5 --risky 2 --risky-med 1 --dataset fashion_mnist
```

5대 가운데 2대는 배터리 15% 이하·cell/no-network·CPU 94%+ (rule_based 예측기가
즉시 risk≈1.0), 1대는 중간, 2대는 안전 프로필.

대시보드의 **이탈 위험 관리** 패널:
1. KPI strip 바로 아래 풀폭 카드. `높음 2 · 중간 1 · 안전 4` 카운트.
2. 5-bucket 위험 분포 히스토그램의 오른쪽 마지막 막대(0.8–1.0)가 빨갛게 채워짐.
3. **위험 상위 3명 자동 와치리스트** 가 이유까지 텍스트로 노출:
   `sim-001 1.00 · low battery (17%) and not charging · unstable network (cell) · cpu saturated (94%)`
4. Connected Clients 표의 RISK 컬럼이 sim-000/001 빨강(1.00), sim-002 주황(0.30), 나머지 녹색.

다음 어드민 액션을 라이브로:
- 한 클라이언트를 **kick** → ClientsTable 행이 즉시 회색(active=false). 폰 fleet 카드 카운트 -1.
- **ban** → 영구 차단, **unban** 으로 해제.
- Registry 패널에서 **selection** 을 `all` → `dropout_aware` 로 swap. 다음 라운드부터 위험 상위 클라이언트는 자동으로 라운드에서 제외되고, MetricsChart의 train acc 가 안정화되는 게 보임.

**보여주려는 것:** 그냥 "참여시킨다" 가 아니라, 누가 떨어질지 예측·표시하고
운영자/시스템이 동시에 통제 가능하다 — 이게 본 캡스톤의 차별점.

---

## 컷 7 — 모듈 swap (45s)

대시보드 Registry 패널에서:
1. **dataset** `mnist` → `fashion_mnist` swap. 모델은 그대로(`cnn_mnist`).
2. 글로벌 평가 KPI 가 새 도메인 기준 acc 로 리셋되며 다시 우상향.
3. **알고리즘** / **선택 정책** / **이탈 예측기** 도 같은 방식으로 swap 가능.

**보여주려는 것:** 같은 모델 + 같은 클라이언트로 **데이터 도메인만 즉시 교체** —
plug-in 구조의 가치. 검증값: MNIST r275 98.98% → Fashion-MNIST r5 57.94%
(난이도 차이까지 그래프에 나타남).

---

## 마무리 슬라이드 1장에 들어가야 할 것

- 검증된 글로벌 acc: **r5 92.39%, r115 99.05% (이전 세션)**
- 검증된 다기기 동시 라운드: 폰 1 + Edge 2 + CLI 1
- 핵심 기여: 모듈식 plug-in + 이탈 예측·제어 + Gboard식 폰 참여 + Linux/Pi 원-라인 참여

---

## 영상 촬영 팁

- 폰 캡쳐: `adb shell screencap -p /sdcard/x.png; adb pull …` (PowerShell `>` 리다이렉트는 PNG 깨짐 — 반드시 on-device 저장 → pull)
- 대시보드 캡쳐: 1440px 폭으로 브라우저 창 고정 (App.jsx의 `max-w-[1440px]` 매칭)
- 폰 시퀀스는 항상 **앱 켜기 → 토글 ON → 충전 케이블 연결** 순서. 케이블이 먼저면 조건 카드가 정적으로 보여서 임팩트 약함.
- 라운드 자동 회전 속도가 시연 호흡과 안 맞으면 `backend/server/core/orchestrator.py:54` 의
  `_async_eval_every_updates`를 1로 임시 조정 (매 업데이트마다 test acc 갱신).
