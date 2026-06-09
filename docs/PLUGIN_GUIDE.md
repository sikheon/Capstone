# Plug-in 작성 가이드

새 알고리즘 / 모델 / 데이터셋 / 선택 정책 / 이탈 예측기를 추가하는 방법.
모두 동일한 4단계 패턴을 따른다.

## 공통 패턴

1. `base.py` 의 추상 클래스를 상속한 새 파일을 같은 디렉토리에 추가.
2. 클래스에 고유한 `name` 속성을 선언.
3. `@register` 데코레이터를 붙임.
4. 같은 디렉토리의 `__init__.py` 에 `from . import <new_module>` 한 줄 추가
   (import 시점에 데코레이터가 발화하도록).

서버를 재시작하면 끝. 대시보드 swap 메뉴 / flctl `/registry` 자동완성 /
Android 스피너에 즉시 노출된다.

## 예시 1: 서버측 FL 알고리즘 (FedProx)

`backend/server/algorithms/fedprox.py`:

```python
import numpy as np
from .base import FLAlgorithm
from .registry import register

@register
class FedProx(FLAlgorithm):
    name = "fedprox"

    def __init__(self, mu: float = 0.01):
        self.mu = mu

    def aggregate(self, client_updates, global_weights):
        # FedAvg 와 동일하지만 proximal term 은 클라이언트 측에서 처리한다고 가정
        total = sum(u["num_samples"] for u in client_updates) or 1
        new = {}
        for k in global_weights:
            new[k] = sum(np.asarray(u["weights"][k]) * (u["num_samples"] / total)
                         for u in client_updates)
        return new
```

`backend/server/algorithms/__init__.py`:

```python
from . import fedavg, fedprox  # noqa: F401
```

## 예시 2: 클라이언트 선택 정책 (Power-of-Two-Choices)

`backend/server/selection/power_of_two.py`:

```python
import random
from .base import SelectionPolicy
from .registry import register

@register
class PowerOfTwo(SelectionPolicy):
    name = "p2c"

    def select(self, candidates, round_num, fraction, min_clients):
        rng = random.Random(round_num)
        k = max(min_clients, int(len(candidates) * fraction))
        picked = []
        while len(picked) < k and candidates:
            a, b = rng.sample(candidates, 2) if len(candidates) >= 2 else (candidates[0], candidates[0])
            winner = a if a.dropout_risk <= b.dropout_risk else b
            picked.append(winner)
            candidates = [c for c in candidates if c.client_id != winner.client_id]
        return [c.client_id for c in picked]
```

## 예시 3: 이탈 예측을 ML 모델로 교체

`backend/server/dropout/ml.py`:

```python
import joblib
from .base import DropoutPredictor
from .registry import register

@register
class MlPredictor(DropoutPredictor):
    name = "ml"

    def __init__(self, path: str = "models/dropout_rf.joblib"):
        self.model = joblib.load(path)

    def predict(self, s):
        feats = [[s.battery or 0, int(bool(s.charging)),
                  1 if s.network == "wifi" else 0,
                  s.cpu_load or 0]]
        risk = float(self.model.predict_proba(feats)[0, 1])
        reasons = ["ml score"] if risk >= 0.5 else []
        return risk, reasons
```

이후 대시보드의 「Pluggable modules → dropout」 에서 `rule_based` ↔ `ml` 을
스위치하면 즉시 평가 로직이 바뀐다.

## 예시 4: Android 측 모델을 TFLite 로 교체

`android/.../model/TfliteCnnRunner.kt` 에 `ModelRunner` 인터페이스를 구현한 뒤,
`ModelRegistry.init { register("cnn_mnist") { ... } }` 의 람다를 새 클래스로
교체하거나 새 이름으로 추가 등록하면 된다.

```kotlin
class TfliteCnnRunner(ctx: Context) : ModelRunner {
    override val name = "tflite_cnn"
    private val interpreter = Interpreter(loadModelFile(ctx))
    // ...
}

ModelRegistry.register("tflite_cnn") { TfliteCnnRunner(appContext) }
```

화면의 「Model」 스피너에 `tflite_cnn` 이 나타난다.

## 잘 안 될 때

- 등록은 됐는데 메뉴에 안 보임 → `__init__.py` 의 import 누락. 모든 정의된
  모듈은 import 되어야 데코레이터가 발화한다.
- swap 직후 라운드가 깨짐 → 의도된 동작. 새 모델을 로드하면 `global_weights`
  도 초기화되므로 다음 라운드부터 클라이언트가 빈 시작점을 받는다. 운영
  중에는 비-피크 시간대에 모델 swap 권장.
- Android 에서 ID 가 계속 새로 발급됨 → `EncryptedSharedPreferences` 가 앱
  데이터 클리어로 날아간 경우. 운영 환경에서는 키 백업 정책 검토 필요.
