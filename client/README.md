# fl-client — 연합학습 엣지 참여자 CLI

군산대 캡스톤 연합학습(FL) 프로젝트의 **엣지 참여 클라이언트**.
라즈베리파이 / Jetson / 리눅스 x86 어디서나 한 줄로 참여한다.

```bash
pip install -e .        # 또는 pipx install .
fl-client --server https://kunsan-fl.loca.lt
```

실행하면 자동으로 다음을 한다:
1. 서버에서 client_id / secret 발급 (provision)
2. 자기 자신 등록 (device info, 모델/CPU/네트워크)
3. heartbeat 시작 (기본 5초 간격)
4. 서버가 라운드에 자기를 선택하면 글로벌 가중치 받아서 **로컬 학습 후 업로드**
5. async 모드면 10초마다 자발적으로 update push

종료는 `Ctrl+C`.

## 옵션

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--server <url>` | `$FL_SERVER_URL` 또는 `http://localhost:8000` | 중앙 코디네이터 URL |
| `--algo <name>` | `fedavg` | 로컬 알고리즘 |
| `--model <name>` | `cnn_mnist` | 모델 |
| `--dataset <name>` | `mnist` | 데이터셋 |
| `--epochs <n>` | `1` | 라운드당 로컬 epoch |
| `--reprovision` | — | 저장된 credential 폐기하고 새로 발급받기 |

환경변수 `FL_SERVER_URL`, `FL_ALGO`, `FL_MODEL`, `FL_DATASET`,
`FL_HEARTBEAT_SEC`, `FL_LOCAL_EPOCHS` 로도 모두 설정 가능.

## systemd 서비스로 상시 가동

```bash
sudo cp systemd/fl-client.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fl-client
sudo systemctl status fl-client
journalctl -u fl-client -f          # 라이브 로그
```

## 라즈베리파이 / Jetson용 PyTorch 휠

`pip install -e .`이 토치를 못 잡으면 플랫폼 맞는 휠을 먼저 깔고
재실행:

```bash
# Raspberry Pi 4/5 (aarch64, CPU only)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Jetson 계열은 NVIDIA 공식 휠 사용
```
