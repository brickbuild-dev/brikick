# Correcções de Warnings nos Testes

## Resultado Actual
- ✅ **28 testes passaram**
- ⏭️ 4 testes skipped
- ⚠️ 4 tipos de warnings a corrigir

---

## PROMPT para GPT Codex - Corrigir Todos os Warnings

Copia e envia este prompt ao GPT Codex:

```
Os testes passaram mas há warnings a corrigir. Corrige todos:

=== 1. DeprecationWarning: datetime.utcnow() ===

PROBLEMA: datetime.utcnow() está deprecated no Python 3.12+

CORRECÇÃO: Substituir em TODOS os ficheiros:

# ANTES (deprecated)
from datetime import datetime
datetime.utcnow()

# DEPOIS (correcto)
from datetime import datetime, timezone
datetime.now(timezone.utc)

Ficheiros a corrigir:
- services/rating.py
- services/penalty_service.py
- tests/unit/test_penalty_evaluation.py
- tests/unit/test_rating_calculation.py
- tests/factories/*.py
- Qualquer outro ficheiro que use datetime.utcnow()

=== 2. DeprecationWarning: HTTP_422_UNPROCESSABLE_ENTITY ===

PROBLEMA: starlette.status.HTTP_422_UNPROCESSABLE_ENTITY deprecated

CORRECÇÃO:

# ANTES
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, ...)

# DEPOIS
from fastapi import status
raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, ...)

# OU simplesmente
raise HTTPException(status_code=422, ...)

=== 3. SAWarning: Ciclo FK entre lots e price_override_requests ===

PROBLEMA: SQLAlchemy detectou ciclo de foreign keys

CORRECÇÃO no modelo Lot (db/models/inventory.py):

# Adicionar use_alter=True na FK problemática
price_override_request_id = Column(
    BigInteger, 
    ForeignKey('price_override_requests.id', use_alter=True, name='fk_lot_override'),
    nullable=True
)

# OU usar string reference em vez de FK directa
# E criar a relação com back_populates

=== 4. passlib CryptContext warning ===

PROBLEMA: crypt deprecated no Python 3.13

CORRECÇÃO em core/security.py:

# ANTES
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# DEPOIS - suprimir o warning (bcrypt ainda funciona)
import warnings
from passlib.context import CryptContext

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OU usar bcrypt directamente
import bcrypt

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

=== 5. Suprimir warnings em pytest (opcional) ===

Adiciona ao pyproject.toml:

[tool.pytest.ini_options]
filterwarnings = [
    "ignore::DeprecationWarning:passlib.*",
]

Faz todas estas correcções e executa os testes novamente.
```

---

## Verificação Final

Após as correcções, os testes devem correr sem warnings:

```bash
pytest tests/ -v --tb=short
```

Output esperado:
```
========================= test session starts =========================
...
========================= 28 passed, 4 skipped in X.XXs =================
```

Sem warnings.

---

## Sobre os 4 Testes Skipped

Os testes skipped podem ser:
- Testes marcados com `@pytest.mark.skip`
- Testes que requerem recursos não disponíveis (ex: API externa)
- Testes E2E que precisam de setup especial

Para ver quais são:
```bash
pytest tests/ -v --tb=short -rs
```

O `-rs` mostra a razão do skip.
