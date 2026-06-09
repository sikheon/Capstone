# 배포 가이드

## 서버

운영용 minimal 배포(systemd):

```ini
# /etc/systemd/system/fl-server.service
[Unit]
Description=FL Coordinator
After=network.target

[Service]
User=fl
WorkingDirectory=/opt/fl/backend
Environment=FL_ADMIN_USER=admin
Environment=FL_ADMIN_PASS=<strong-secret>
ExecStart=/opt/fl/venv/bin/python -m server.main
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

리버스 프록시 뒤에 둘 경우 WS 업그레이드 헤더(`Upgrade`, `Connection`) 와
CORS(`*` → 화이트리스트) 를 정리할 것.

## flctl (CLI)

가장 단순한 배포 방법:

```bash
# 사내 PyPI/내부 인덱스가 있다면
pip install flctl

# 없다면 git 체크아웃 + 원클릭 설치
git clone <repo> && cd capstone/cli && bash install.sh
```

`install.sh` 는 `~/.flctl` 가상환경을 만들고 `~/.local/bin/flctl` 심볼릭
링크를 건다. `~/.local/bin` 이 PATH 에 있는지만 확인하면 끝.

여러 서버를 사용한다면 알리아스로 분리:

```bash
alias flctl-prod='FL_SERVER_URL=https://prod.fl.example.com flctl'
alias flctl-dev='FL_SERVER_URL=http://dev.fl.example.com:8000 flctl'
```

## Python edge

라즈베리파이 / Jetson 부팅 시 자동 실행:

```ini
# /etc/systemd/system/fl-client.service
[Unit]
Description=FL Edge Client
After=network-online.target

[Service]
User=pi
WorkingDirectory=/opt/fl/client
Environment=FL_SERVER_URL=https://fl.example.com
Environment=FL_HEARTBEAT_SEC=5
ExecStart=/opt/fl/venv/bin/python -m client.main
Restart=always

[Install]
WantedBy=multi-user.target
```

자격증명은 `~pi/.flclient/credentials.json` 에 저장된다(0600 권한). 서버를
옮기면 처음 한 번 `--reprovision` 으로 다시 발급받으면 된다.

## Android

`android/app/build.gradle.kts` 의 `DEFAULT_SERVER_URL` 만 운영용 도메인으로
바꾸고 release 빌드. 사용자가 첫 실행 시 서버 URL을 변경하면 그 값이
EncryptedSharedPreferences 에 들어가 이후 영구 사용된다.

## 웹 대시보드

```bash
cd frontend
VITE_SERVER_URL=https://fl.example.com npm run build
# dist/ 를 nginx / Cloudflare Pages / S3 정적 호스팅에 업로드
```

## 운영 체크리스트

- [ ] 기본 어드민 비밀번호(`admin`) 교체 — `FL_ADMIN_PASS` env
- [ ] HTTPS 종단 (uvicorn 단독 X — Caddy / Nginx 권장)
- [ ] `usesCleartextTraffic="true"` 는 개발 편의용. release 빌드 시 https 강제
- [ ] CORS `allow_origins=["*"]` 를 운영 도메인 목록으로 좁히기
- [ ] AuthManager 가 in-memory — 서버 재시작 시 발급된 모든 자격증명이 무효화됨.
  영속화가 필요하면 SQLite/Redis 어댑터로 `AuthManager` 만 교체 (인터페이스
  유지).
