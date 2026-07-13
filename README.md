<div align="center">

# SmartFerrariIOT

**Plataforma experimental de pós em Engenharia da Computação** · sincronização edge **Arduino ↔ Raspberry Pi** · gêmeo digital formal · HIL/QoS · Web Audio · Research Lab · Ferrari SF90 lab unit

<br/>

<a href="http://127.0.0.1:8001">
  <img src="docs/assets/lab-open-button.png" alt="Abrir Ferrari Lab — http://127.0.0.1:8001" width="920"/>
</a>

<br/>

<a href="http://127.0.0.1:8001"><img src="https://img.shields.io/badge/OPEN_LAB-127.0.0.1%3A8001-e10600?style=for-the-badge" alt="Open Lab"/></a>
<img src="https://img.shields.io/badge/login-admin-1e222b?style=for-the-badge" alt="admin"/>
<img src="https://img.shields.io/badge/password-ferrari123-c9a227?style=for-the-badge" alt="ferrari123"/>
<img src="https://img.shields.io/badge/Stack-FastAPI%20%7C%20MQTT%20%7C%20WS-2a2e32?style=for-the-badge" alt="Stack"/>

---

## Interface do Laboratório (análise / defesa)

**Clique no botão** para abrir a interface local usada na análise e na defesa.

<a href="http://127.0.0.1:8001">
  <img src="https://img.shields.io/badge/Ferrari%20Lab-http%3A%2F%2F127.0.0.1%3A8001-e10600?style=for-the-badge&labelColor=1a0505" alt="Ferrari Lab 8001"/>
</a>

| | |
|:---:|:---:|
| **URL** | **http://127.0.0.1:8001** |
| **Login** | `admin` |
| **Senha** | `ferrari123` |
| **Porta** | `8001` (SmartHomeIOT = `8000`) |

```powershell
cd SmartFerrariIOT
.\start.ps1
```

| Recurso | URL |
|:---:|:---:|
| **UI Lab** | **http://127.0.0.1:8001** |
| Health | http://127.0.0.1:8001/health |
| OpenAPI | http://127.0.0.1:8001/docs |
| Research overview | http://127.0.0.1:8001/api/research/overview |
| Paper Pack LaTeX | http://127.0.0.1:8001/api/research/paper-pack.tex |

<img src="docs/assets/ferrari-studio.png" alt="Ferrari SF90 — referência visual do digital twin" width="920"/>

<em>Referência SF90 · o Lab opera o gêmeo digital animável (portas, rodas, Sport, A/C, HIL, áudio).</em>

---

## Mapa mental do projeto

<img src="docs/assets/mindmap.png" alt="Mapa mental SmartFerrariIOT" width="920"/>

</div>

```mermaid
mindmap
  root((SmartFerrariIOT))
    Edge
      Arduino L1
      Raspberry hub
      MQTT ferrari/*
    Twin
      SECURE IDLE READY RUNNING SPORT
      INV-01..06
    Lab
      Web Audio espectro
      HIL delay/loss
      SQI telemetria
    Security
      HMAC comandos
      Audit hash-chain
    Energy
      P_motor farol som AC
      bateria combustível
    Vision
      gesto partida
      QR track
```

<div align="center">

---

## Arquitetura em camadas (L1–L5)

<img src="docs/assets/architecture-l1-l5.png" alt="Arquitetura L1 a L5" width="920"/>

</div>

```mermaid
flowchart TB
  subgraph L5["L5 Experiência"]
    UI[Digital Twin UI]
    AUD[Web Audio]
    VIS[Visão / QR]
    LAB[Research Lab]
  end
  subgraph L4["L4 Orquestração"]
    API[FastAPI :8001]
    DB[(SQLite)]
    TEL[SQI / Telemetry]
    HIL[HIL Engine]
    SEC[HMAC + Audit]
  end
  subgraph L3["L3 Hub"]
    PI[Raspberry agent]
  end
  subgraph L2["L2 Protocolo"]
    MQTT[MQTT ferrari/*]
    WS[WebSocket /api/ws]
  end
  subgraph L1["L1 Campo"]
    ARD[Arduino atuadores]
  end
  UI --> WS
  UI --> API
  API --> HIL --> TEL
  API --> SEC
  API --> DB
  API --> MQTT
  PI --> MQTT
  ARD --> MQTT
  LAB --> API
  AUD --> UI
  VIS --> API
```

<div align="center">

**Documentação:** [ARCHITECTURE](docs/ARCHITECTURE.md) · [PROTOCOL](docs/PROTOCOL.md) · [METHODOLOGY](docs/METHODOLOGY.md)

---

## Gêmeo digital formal (UML / Statechart)

<img src="docs/assets/twin-statechart.png" alt="Statechart e invariantes" width="920"/>

</div>

```mermaid
stateDiagram-v2
  [*] --> SECURE
  SECURE --> IDLE: disarm + unlock
  IDLE --> READY: unlock path
  READY --> RUNNING: engine ON
  RUNNING --> SPORT: sport ON
  SPORT --> RUNNING: sport OFF
  RUNNING --> IDLE: engine OFF
  READY --> SECURE: alarm ARM
```

<div align="center">

| ID | Regra |
|:---:|:---:|
| INV-01 | Não abrir porta se Sport ∧ velocidade > 0 |
| INV-02 | Não ligar motor com alarme armado |
| INV-03 | Sport requer motor ON |
| INV-04 | Teto bloqueado se velocidade > 40 km/h |
| INV-05 | Travar ⇒ fechar portas |
| INV-06 | Não armar alarme com motor ligado |

Violação → **HTTP 409** ou evento WS `invariant_violation`

---

## Fluxo de comando (HIL + Twin + Audit)

<img src="docs/assets/sequence-command.png" alt="Sequência de comando" width="920"/>

</div>

```mermaid
sequenceDiagram
  participant UI as Lab UI
  participant API as FastAPI/WS
  participant HIL as HIL Engine
  participant Twin as Digital Twin
  participant Aud as Audit Chain
  UI->>API: action (engine/door/…)
  API->>HIL: apply(delay, loss?)
  alt dropped
    HIL-->>UI: HIL drop
  else delivered
    HIL->>Twin: guard(INV)
    alt invariant fail
      Twin-->>UI: 409 / invariant_violation
    else ok
      Twin->>Aud: HMAC + hash tip
      Aud-->>UI: state broadcast + QoS
    end
  end
```

<div align="center">

<img src="docs/assets/hil-qos.png" alt="HIL QoS" width="920"/>

---

## Modelo energético (documentado)

$$
P_{total} = P_{motor}(rpm) + P_{farol} + P_{som} + P_{AC} + P_{track} + P_{spoiler}
$$

$$
P_{motor} = P_0 + k_{rpm}\cdot rpm \quad (+35\%\ \text{em Sport})
$$

$$
\Delta E_{bat}\ (Wh) \approx -P_{total}\cdot \Delta t_h, \quad
\Delta fuel \approx -\alpha\cdot P_{motor}\cdot \Delta t_h
$$

Constantes de bancada em `python_server/energy.py` · \(C_{bat}\approx 720\,Wh\)

---

## Research Lab — demonstração na banca

1. **Áudio real** — motor (ronco + rodas), buzina, alarme + espectro  
2. **Invariantes** — armar alarme → tentar motor → `INV-02`  
3. **HIL** — delay 80 ms / loss 20% → gráfico QoS  
4. **Portas** — Abrir Ambas · Travar/Destravar  
5. **Paper Pack** — export LaTeX

---

## Árvore do repositório

```text
SmartFerrariIOT/
├── start.ps1
├── web/
├── python_server/
├── arduino/
├── raspberry/
├── docs/assets/
├── experiments/exports/
└── tests/
```

---

## API rápida

| Método | Endpoint | Função |
|:---:|:---:|:---:|
| POST | `/api/auth/login` | Token |
| GET | `/api/status` | Snapshot |
| POST | `/api/door\|engine\|alarm\|…` | Atuadores |
| WS | `/api/ws` | Estado ao vivo |
| POST | `/api/research/hil` | HIL |
| POST | `/api/research/paper-pack` | LaTeX |
| GET | `/api/research/audit` | Hash-chain |

---

<a href="http://127.0.0.1:8001">
  <img src="docs/assets/lab-open-button.png" alt="Ferrari Lab http://127.0.0.1:8001" width="720"/>
</a>

### [http://127.0.0.1:8001](http://127.0.0.1:8001)

</div>
