# Tello Zune (v0.7.8)

Uma biblioteca Python orientada a eventos thread-safe para o controle, leitura de telemetria e streaming de vídeo do drone DJI Tello. 

A Tello Zune gerencia filas de comandos assíncronas, faz monitoramento contínuo de estado em background e bloqueios de segurança para garantir que o seu drone responda de forma previsível e estável, mesmo durante a execução de rotas complexas.

## Funcionalidades Principais

* **Comunicação Thread-Safe:** Uso de `Locks` e `Queues` para evitar colisões de pacotes UDP.
* **Telemetria Contínua:** Leitura de sensores (bateria, altura, velocidade, temperatura) passiva pela porta 8890, sem bloquear o envio de comandos de voo.
* **Streaming de Vídeo Integrado:** Captura e redimensionamento de frames em tempo real usando OpenCV. Se o stream parar por mais de 2 s (`VIDEO_READ_TIMEOUT_MS`), ele é reaberto automaticamente.
* **Rotas e Eventos Periódicos:** Capacidade de programar sequências de movimentos (ex: patrulhas) com intervalos de tempo precisos usando o comando customizado `delay`.
* **Modo Interativo de Terminal:** Controle o drone enviando comandos de texto direto pelo console enquanto o script de vídeo roda em paralelo.
* **Parada de Emergência:** Limpeza instantânea da fila de comandos e corte de motores com o método `emergency_stop()`.

## Pré-requisitos e Instalação

Este projeto utiliza o [uv](https://docs.astral.sh/uv/) para gerenciamento de pacotes e ambiente virtual, com as dependências definidas no `pyproject.toml`.

Para instalar a biblioteca em um projeto existente via `uv`:
```bash
uv add tello-zune
```

Para clonar e configurar o ambiente de desenvolvimento localmente:
```bash
uv sync
```

Para adicionar novas dependências ao projeto:
```bash
uv add <pacote>
```

Conecte o seu computador à rede Wi-Fi do drone Tello antes de executar os scripts.

---

## Como Usar (Exemplos)

Na pasta `examples/` você encontra scripts prontos para testar as capacidades da Tello Zune. Utilize `uv run` para executá-los dentro do ambiente virtual do projeto:

### 1. Controle por Terminal de Texto (`text_commands.py`)
Este exemplo inicia a câmera do Tello com um HUD de telemetria na tela. Ao mesmo tempo, ele habilita o terminal para que você digite comandos de voo (como `takeoff`, `forward 50`, `cw 90`) manualmente.
```bash
uv run python examples/text_commands.py
```

Comandos aceitos no terminal:

| Comando | Efeito |
|---|---|
| `takeoff`, `forward 50`, `cw 90`, ... | Enfileira o movimento (`up`, `down`, `left`, `right`, `forward`, `back`, `cw`, `ccw` exigem um valor numérico). |
| `land` | Esvazia a fila e pousa na hora. |
| `emergency` | Esvazia a fila e corta os motores na hora. |
| `end` | Entra na fila: depois que os comandos anteriores terminarem, `end_requested()` passa a ser `True`, o laço do exemplo sai e `end_tello()` pousa e encerra o programa. |
| `exit` | Fecha só a entrada de texto; o programa continua. |

Apertar `q` na janela do vídeo também encerra.

### 2. Rotas e Comandos Periódicos (`periodic_commands.py`)
Neste exemplo, o drone é programado para executar uma rota periódica de "Vigilância". Ele se moverá para frente 50cm e girará 90 graus a cada intervalo de tempo determinado, operando de forma autônoma.
```bash
uv run python examples/periodic_commands.py
```

---

## Métodos Principais da API

Aqui estão algumas das funções mais úteis para controlar o Tello programaticamente:

* `add_command(cmd: str)`: Enfileira um comando oficial do SDK do Tello (ex: `up 50`, `flip b`) para ser executado de forma segura na próxima janela disponível.
* `get_speed() -> tuple`: Retorna a velocidade atual em tempo real nos eixos X, Y e Z `(vx, vy, vz)` em cm/s.
* `get_battery() -> int`: Retorna a porcentagem atual da bateria (0-100).
* `get_frame() -> np.ndarray`: Retorna o frame mais recente do vídeo, ou um frame preto se nenhum chegar no timeout.
* `get_frame_stamped(timeout) -> (frame, stamp) | None`: Retorna um frame novo junto com o `time.time()` em que foi lido do stream, ou `None` se nenhum frame novo chegar. Nunca repete frames nem devolve frame preto; indicado para visão computacional, SLAM e ROS.
* `get_state() -> dict`: Retorna todos os campos numéricos do último pacote de estado (atitude em graus, `tof`/`h` em cm, etc.). O instante de chegada fica em `state_stamp`.
* `send_rc_control(lr, fb, ud, yaw)`: Envia velocidades de -100 a 100; valores fora da faixa são saturados.
* `set_rc_watchdog(timeout)`: Se nenhum `send_rc_control()` chegar em `timeout` segundos enquanto o drone se move, envia `rc 0 0 0 0` para ele pairar. `None` desativa (padrão).
* `emergency_stop()`: Esvazia a fila de comandos imediatamente e corta os motores do drone. Ideal para evitar colisões iminentes.
* `clear_command_queue()`: Limpa todos os comandos pendentes na fila sem derrubar o drone.
* `end_tello(land=True)`: Pousa o drone com retentativas automáticas em caso de falha na rede (a menos que a telemetria indique que ele já está no chão), encerra o streaming de vídeo e fecha os sockets de comunicação corretamente. Use `land=False` para só encerrar a comunicação.
* `end_requested() -> bool`: `True` depois que o comando `end` foi executado pela fila (digitado no modo texto ou enfileirado com `add_command("end")`) ou `end_tello()` foi chamado. Use como condição do laço principal: `while not tello.end_requested(): ...` e chame `end_tello()` ao sair.
* `is_flying() -> bool | None`: Indica se o drone está no ar pela altura `h` da telemetria; `None` se ainda não há telemetria.
* `add_periodic_event(cmd, period, info, interval)` / `remove_periodic_event(cmd)`: Comandos ou rotas (`"forward 50 e cw 90"`) repetidos a cada `period` ciclos de 0,1 s. Uma rota só é disparada de novo depois que a anterior terminou de executar.

## Estrutura e Testes

A biblioteca possui cobertura de testes unitários para garantir a estabilidade das funções de rede e de concorrência. Para executar os testes na raiz do projeto, utilize:

```bash
uv run python -m unittest discover -s test -v
```
