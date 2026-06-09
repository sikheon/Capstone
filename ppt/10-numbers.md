# 검증된 수치 (발표용)

| 항목 | 값 | 비고 |
| --- | --- | --- |
| 글로벌 MNIST 정확도 | r5 92.39 % → r20 98.75 % → r275 98.98 % → r115(이전 세션) 99.05 % | held-out 10k test set |
| 글로벌 Fashion-MNIST 정확도 | r5 57.94 % → r2290 45.29 % | 같은 모델(cnn_mnist), 데이터셋만 swap. 어려운 도메인이라 시간 더 필요. |
| 동시 라운드 (실기) | 폰 1 + Edge 2 + CLI/sim 5 = 클라이언트 8명 | clients=8 캡쳐로 검증 |
| 라운드 wall-clock | < 200 ms (async, MNIST) | metric → WS 이벤트 |
| Held-out 평가 빈도 | 5 update마다 | `_async_eval_every_updates` |
| 이탈 예측 응답 | < 1초 (heartbeat 주기 5초) | dropout_risk가 매 heartbeat에 갱신 |
| 위험 분포 (시뮬) | 높음 2 / 중간 0 / 안전 6 (5대 sim + 2 edge + 1 cli) | rule_based 예측기 + simulate.py --risky 2 |
| 폰 앱 라이브 갱신 | 2.5초 폴링 | global acc / fleet / sparkline / 수집 카드 |
| 빌드 / 런타임 | Android v0.3.0 (Kotlin, WorkManager 2.9.1), backend FastAPI + PyTorch 2.x, frontend React + Tailwind v4 + shadcn | |

## 기술적 차별점 (한 줄씩)

1. **Plug-in 레지스트리** — 알고리즘 / 모델 / 데이터셋 / 선택 정책 / 이탈 예측기 모두 런타임 swap. 발표 1컷에서 dataset mnist → fashion_mnist 라이브로.
2. **이탈 예측 → 표시 → 제어** 통합 — 백엔드 rule_based 예측기 → DropoutPanel UI (high/med/safe + 와치리스트 + 분포) → selection을 `dropout_aware` 로 swap 시 위험 클라이언트 자동 배제.
3. **다기기 실증** — Python (Pi/Jetson 라이브러리 호환) + Kotlin (Android WorkManager + Gboard식 제약) + Node (모니터링용) + 시뮬레이터.
4. **서버 주도 모듈 추종** — fl-client / Android 둘 다 heartbeat 응답의 algorithm/model/dataset 을 따라가서 자동 reload (auto-follow). 어드민이 swap 하면 모든 참여 클라가 즉시 합류.
5. **Gboard 패턴 자리** — DataCollector 인터페이스 + 더미 (Noop / Mock) 구현. 키보드·센서·카메라 도메인 collector 추가 시 FLWorker 손 안 댐.

## 데모 시나리오 한 줄

1. 백엔드 + 터널 + 대시보드 띄우기
2. `python tools/simulate.py --clients 5 --risky 2 --risky-med 1 --dataset fashion_mnist`
3. 폰 「참여」 토글 ON
4. 대시보드 KPI 상승 + DropoutPanel 빨강 채워짐
5. Registry 패널에서 dataset mnist↔fashion_mnist / selection all↔dropout_aware swap 라이브
