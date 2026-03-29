# Tello Zune (v0.7.7)

Uma biblioteca Python orientada a eventos thread-safe para o controle, leitura de telemetria e streaming de vídeo do drone DJI Tello. 

A Tello Zune gerencia filas de comandos assíncronas, faz monitoramento contínuo de estado em background e bloqueios de segurança para garantir que o seu drone responda de forma previsível e estável, mesmo durante a execução de rotas complexas.

## Funcionalidades Principais

* **Comunicação Thread-Safe:** Uso de `Locks` e `Queues` para evitar colisões de pacotes UDP.
* **Telemetria Contínua:** Leitura de sensores (bateria, altura, velocidade, temperatura) passiva pela porta 8890, sem bloquear o envio de comandos de voo.
* **Streaming de Vídeo Integrado:** Captura e redimensionamento de frames em tempo real usando OpenCV.
* **Rotas e Eventos Periódicos:** Capacidade de programar sequências de movimentos (ex: patrulhas) com intervalos de tempo precisos usando o comando customizado `delay`.
* **Modo Interativo de Terminal:** Controle o drone enviando comandos de texto direto pelo console enquanto o script de vídeo roda em paralelo.
* **Parada de Emergência:** Limpeza instantânea da fila de comandos e corte de motores com o método `emergency_stop()`.

## Pré-requisitos e Instalação

Certifique-se de ter o Python 3 instalado. As dependências principais da biblioteca estão no requirements.txt.

Instale a Tello Zune:
```bash
pip install tello-zune
```

Conecte o seu computador à rede Wi-Fi do drone Tello antes de executar os scripts.

---

## Como Usar (Exemplos)

Na pasta `examples/` você encontra scripts prontos para testar as capacidades da Tello Zune.

### 1. Controle por Terminal de Texto (`text_commands.py`)
Este exemplo inicia a câmera do Tello com um HUD de telemetria na tela. Ao mesmo tempo, ele habilita o terminal para que você digite comandos de voo (como `takeoff`, `forward 50`, `cw 90`) manualmente.

### 2. Rotas e Comandos Periódicos (`periodic_commands.py`)
Neste exemplo, o drone é programado para executar uma rota periódica de "Vigilância". Ele se moverá para frente 50cm e girará 90 graus a cada intervalo de tempo determinado, operando de forma autônoma.

---

## Métodos Principais da API

Aqui estão algumas das funções mais úteis para controlar o Tello programaticamente:

* `add_command(cmd: str)`: Enfileira um comando oficial do SDK do Tello (ex: `up 50`, `flip b`) para ser executado de forma segura na próxima janela disponível.
* `get_speed() -> tuple`: Retorna a velocidade atual em tempo real nos eixos X, Y e Z `(vx, vy, vz)` em cm/s.
* `get_battery() -> int`: Retorna a porcentagem atual da bateria (0-100).
* `emergency_stop()`: Esvazia a fila de comandos imediatamente e corta os motores do drone. Ideal para evitar colisões iminentes.
* `clear_command_queue()`: Limpa todos os comandos pendentes na fila sem derrubar o drone.
* `end_tello()`: Pousa o drone com retentativas automáticas em caso de falha na rede, encerra o streaming de vídeo e fecha os sockets de comunicação corretamente.

## Estrutura e Testes

A biblioteca possui cobertura de testes unitários para garantir a estabilidade das funções de rede e de concorrência. Para executar os testes na raiz do projeto, utilize:

```bash
python -m unittest discover -s test -v
```