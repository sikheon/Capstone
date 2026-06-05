# flctl — (deprecated) Node 기반 모니터링 CLI

> **이 도구는 더 이상 "참여" 도구가 아닙니다.** 리눅스 사용자가 실제 연합학습에
> 참여하려면 Python 패키지 [`fl-client`](../client/)를 사용하세요.

## 왜 폐기했나

Node 런타임은 PyTorch를 돌리지 못해, `flctl /join` 은 사실 서버에
`POST /api/heartbeat` 만 보냅니다. 가중치를 받지도, 학습하지도, 업데이트를
밀어올리지도 못합니다 — 즉 "유령 참여자". FL 라운드에 실제로 기여하지 않습니다.

리눅스 사용자가 진짜로 참여하려면 Python 엣지 클라이언트를 사용하세요:

```bash
pip install -e ./client            # capstone/ 루트에서
fl-client --server https://kunsan-fl.loca.lt
```

자동으로 자격증명 발급 → 등록 → heartbeat → 라운드 선택 시 학습/업로드까지
처리합니다. systemd 유닛 샘플은 `client/systemd/` 에 있습니다.

## 기존 사용자 정리

`npm link`로 전역 설치했다면 다음으로 제거:

```bash
cd capstone/cli
npm unlink -g flctl          # 또는: npm uninstall -g flctl
```

## 코드는 왜 남겨뒀나

데모·발표에서 "관리자가 슬래시 명령으로 서버 상태를 빠르게 들여다보는"
장면이 필요할 수 있어 read-only 모니터링 도구로는 동작합니다. 사용 가능한
read-only 명령:

```
/status   /clients   /metrics   /params   /registry   /rounds   /whoami
```

단, "참여"는 더 이상 이 CLI의 책임이 아닙니다.

| 흐름 | 도구 |
| --- | --- |
| 리눅스 / Raspberry Pi / Jetson 참여 | **`fl-client` (Python)** |
| 안드로이드 참여 | `android/` APK |
| 어드민 제어 + 실시간 차트 | `frontend/` 웹 대시보드 |
| 빠른 read-only 점검 | (선택) `flctl` |
