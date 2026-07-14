# Arquitetura — Ferrari IoT Postdoc

Camadas L1–L5 para sincronização Arduino↔Raspberry em plataforma veicular experimental.

| Camada | Foco |
|--------|------|
| L1 | Servos porta/teto, relés motor/farol/som, GPS |
| L2 | MQTT `ferrari/*`, REST, WebSocket |
| L3 | Raspberry hub + heartbeat |
| L4 | FastAPI, SQLite, Telemetria SQI |
| L5 | Simulador Ferrari + Research Lab |

SQI = 0.45·skew + 0.30·jitter + 0.25·reliability
