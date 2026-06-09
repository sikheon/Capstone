# 자체 호스팅 가이드

`localtunnel` 은 발표·시연 단계 임시방편입니다. 학과 내부망에 진짜로 띄우는
순서를 정리합니다.

## 0. 어떤 길이 있나

| 방식 | 누구한테 좋나 | 인증서 | 외부 접속 | 비용 |
| --- | --- | --- | --- | --- |
| **A. localtunnel** | 30초 데모, 발표 직전 | 자체 발급 | OK (단명 URL) | 무료 |
| **B. ngrok** | 며칠짜리 대외 테스트 | 자체 발급 | OK (고정 도메인 무료티어) | 무료/유료 |
| **C. 학과 내부망 + 내 PC** | 학내 시연 | 없음 (HTTP) | 학내만 | 무료 |
| **D. 학교 도메인 + Caddy 자동 TLS** | **인수인계 후 정착** | Let's Encrypt | OK | 무료 |
| **E. 공용 클라우드 (EC2/GCP) + 도메인** | 외부 협업사(제이디) 접근 | Let's Encrypt | OK | 월 $5~ |

이 문서는 **D**(권장) + **C/E** 부속을 다룹니다.

## A. localtunnel 빠른 재기동 (지금 운영중인 방식)

```powershell
# 백엔드 8000 떠 있는 상태에서
npx localtunnel --port 8000 --subdomain kunsan-fl
# → https://kunsan-fl.loca.lt
```

주의:
- 첫 외부 접속 시 IP 확인 HTML 인터스티셜이 뜸. Android 앱과 fl-client 는
  `bypass-tunnel-reminder: 1` 헤더로 우회함(이미 반영).
- localtunnel 프로세스가 죽으면 URL 도 죽음 → 학과 발표 직전엔 재기동 필수.

## C. 학과 내부망 + 본인 PC (가장 가벼움)

내 PC의 학과망 IP 그대로 노출:

```powershell
# 본인 PC 외부 학과 IP
ipconfig | findstr IPv4

# 백엔드 띄우기 (0.0.0.0 바인딩 필수)
uvicorn server.main:app --host 0.0.0.0 --port 8000

# 방화벽 8000 열기 (관리자 PowerShell)
New-NetFirewallRule -DisplayName 'Kunsan FL 8000' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

폰 / Pi / 다른 PC 에서 `http://<내PC학과IP>:8000` 으로 접속.

한계: 본인 PC 가 꺼지면 죽음. 학과망 NAT 따라 외부에선 안 보임.

## D. 학교 도메인 + Caddy 자동 TLS (인수인계 후 정착 권장)

### 전제

- 학과에서 `fl.cs.kunsan.ac.kr` (또는 유사) 서브도메인 / 인바운드 443 포트 허락
- 운영용 PC (또는 학과 서버 VM) 가 24/7 가동
- 해당 호스트가 정적 IP / 학과 DNS 에 A 레코드 등록

### Caddyfile

`/etc/caddy/Caddyfile`:

```
fl.cs.kunsan.ac.kr {
    encode gzip
    # API + WS 둘 다 같은 백엔드로
    reverse_proxy 127.0.0.1:8000

    # 어드민 대시보드 정적 빌드를 정적 서빙하고 싶다면
    handle_path /admin/* {
        root * /srv/kunsan-fl-frontend/dist
        try_files {path} /index.html
        file_server
    }
}
```

설치 (Debian/Ubuntu):

```bash
sudo apt install caddy
sudo systemctl enable --now caddy
# Let's Encrypt 인증서 자동 발급 + 자동 갱신
```

대시보드 빌드:

```bash
cd frontend
VITE_SERVER_URL=https://fl.cs.kunsan.ac.kr npm run build
sudo cp -r dist/* /srv/kunsan-fl-frontend/dist/
```

### 백엔드를 systemd 서비스로

`/etc/systemd/system/kunsan-fl.service`:

```ini
[Unit]
Description=Kunsan FL coordinator
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/srv/kunsan-fl/backend
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONIOENCODING=utf-8
Environment=FL_ADMIN_USER=kunsan-fl-admin
EnvironmentFile=/etc/kunsan-fl.env       # FL_ADMIN_PASS 같은 비밀값
ExecStart=/srv/kunsan-fl/backend/.venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
User=kunsan-fl

[Install]
WantedBy=multi-user.target
```

`/etc/kunsan-fl.env` (chmod 600):

```
FL_ADMIN_PASS=<강한 패스워드>
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kunsan-fl
sudo journalctl -u kunsan-fl -f
```

### 클라이언트 측 새 도메인 반영

| 컴포넌트 | 변경 |
| --- | --- |
| 폰 (Android) | 「설정」 다이얼로그에서 서버 URL을 `https://fl.cs.kunsan.ac.kr` 로. 또는 다음 빌드부터 `android/app/build.gradle.kts` 의 `DEFAULT_SERVER_URL` 갱신. |
| `fl-client` | `fl-client --server https://fl.cs.kunsan.ac.kr` 또는 `FL_SERVER_URL` env, systemd unit `ExecStart` 수정 |
| 웹 대시보드 | `VITE_SERVER_URL` 박은 채 빌드 / 헤더 「change」 |
| flctl | `flctl --server …` / `/server` 명령 |

## E. EC2 / GCP 한 줄 (외부 협업사 접근)

도커 1대로 캐디 + 백엔드 + 프론트엔드 빌드까지 같이 굴립니다. 별도
`docs/cloud-deploy.md` 로 분리할 만한 분량이라 이 문서에는 골격만:

```yaml
# docker-compose.yml (요약)
services:
  caddy:
    image: caddy:2
    ports: [ "80:80", "443:443" ]
    volumes: [ "./Caddyfile:/etc/caddy/Caddyfile", "caddy_data:/data" ]
  backend:
    build: ./backend
    environment:
      FL_ADMIN_PASS: ${FL_ADMIN_PASS}
    expose: [ "8000" ]
volumes: { caddy_data: }
```

## 체크리스트 (마이그 끝났는지)

- [ ] 외부에서 `https://<신도메인>/api/status` 가 200
- [ ] 인증서가 Let's Encrypt 정상 (브라우저 자물쇠)
- [ ] WebSocket (`wss://<신도메인>/ws/events`) 이 대시보드에서 라이브 메트릭 push
- [ ] 폰 서버 URL 갱신 후 fleet 카드에 자기 안드로이드가 카운트됨
- [ ] systemd `restart=always` 가 실제로 죽었다 살아남 — `kill <pid>` 후 자동 복구 확인
- [ ] 어드민 계정 비밀번호가 디폴트(admin)가 아님
- [ ] `tools/simulate.py` 으로 가상 6대 띄워서 라운드 회전 확인
