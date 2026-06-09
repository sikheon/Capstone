# PPT 슬라이드 ↔ 자료 매핑

캡스톤 발표용. `capstone/ppt/` 안의 자산을 어떤 슬라이드에 쓸지 정리.

## 슬라이드 1 — 표지
- 텍스트: "엣지 AI 연합학습 클라이언트 이탈 관리 시스템 / 팀 데굴데굴 (최현식·이승규·남궁재민) × 제이디컴퍼니 / 군산대 SW학과 캡스톤"
- 이미지: 없음 (또는 학과 로고)

## 슬라이드 2 — 문제 정의
- 텍스트: 이종 엣지(Pi/Jetson/Android)에서 연합학습 운영 시 발생하는 **클라이언트 이탈**. 모바일은 배터리·네트워크 변동성 크고, 이탈 시 라운드 실패·정확도 손해.
- 이미지: 없음 (자체 다이어그램)

## 슬라이드 3 — 시스템 구성 (한 장)
- 이미지: `06-dashboard-full.png`
- 설명: FastAPI 백엔드 / React 대시보드 / Kotlin 폰 / Python 엣지 / Node 모니터링 CLI / 시뮬레이터 — 모두 같은 REST + WS 위에서.

## 슬라이드 4 — 폰 참여자 UX
- 이미지: `01-phone-main.png` + `02-phone-conditions.png` (좌우 배치)
- 설명: 토글 하나로 참여. 백그라운드에서 충전 + Wi-Fi + 유휴 + 배터리 50%+ 조건 충족 시 자동 학습. 「내 기여 라운드 / 내 정확도 / 글로벌 정확도」 KPI 와 「함께 학습 중인 디바이스」 fleet.

## 슬라이드 5 — 서버 주도 모듈 swap
- 이미지: `03-phone-settings.png` + `04-phone-collector-dropdown.png`
- 설명: 폰 설정에서 수집기 변경. 또는 어드민이 대시보드에서 dataset 을 swap 하면 폰 / fl-client 가 heartbeat 응답을 보고 자동 추종.

## 슬라이드 6 — **메인 컷: 이탈 관리** ★
- 이미지: `07-dashboard-kpi-dropout.png`
- 설명: KPI strip 바로 아래 풀폭 패널.
  - 높음 / 중간 / 안전 카운트
  - 위험 분포 히스토그램
  - 위험 상위 3명 자동 와치리스트 (이유 텍스트 포함)
  - 예측기 라벨 (rule_based — swap 가능)

## 슬라이드 7 — 라이브 학습 / 글로벌 평가
- 이미지: `08-dashboard-clients.png` (loss / accuracy 차트 + Global model panel)
- 설명: 라운드마다 sample-weighted 평균 + 5 update마다 held-out test set 평가. Fashion-MNIST 로 dataset swap 시 곡선이 새 도메인 기준으로 재시작.

## 슬라이드 8 — 동시 다기기 검증
- 이미지: `06-dashboard-full.png` 의 Connected Clients 영역 (8명 표시)
- 설명: 폰 / Edge / CLI / Sim 동시에 라운드 회전. risk 컬럼이 색상으로 위험도 표시 (sim-000/001 빨강 1.00, 나머지 녹색 0.00).

## 슬라이드 9 — 리눅스 엣지 CLI (1줄 설치)
- 이미지: `09-fl-client-help.txt` 텍스트 박스로 슬라이드에 paste
- 설명: `pip install -e ./client` 한 줄. `fl-client --server …` 시작 즉시 자격증명 발급·학습 참여. systemd 유닛 샘플 동봉.

## 슬라이드 10 — 검증된 수치
- 이미지: 없음 (자체 표)
- 텍스트: `10-numbers.md` 의 표 그대로 paste.

## 슬라이드 11 — 차별점 / 마무리
- 텍스트: `10-numbers.md` 의 "기술적 차별점" 5개

## 시연 시 (라이브)
- 실제 대시보드 띄워두고 `dataset swap mnist↔fashion_mnist` / `selection all↔dropout_aware` 두 액션만 라이브.
- 폰은 미리 토글 ON 상태로 발표대에 둠.
- `python tools/simulate.py --clients 5 --risky 2 --risky-med 1` 백그라운드 실행해서 이탈 패널이 비어보이지 않게.
