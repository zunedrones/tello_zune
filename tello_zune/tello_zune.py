import time
import threading
import numpy as np
import socket
import cv2
from queue import Queue, Empty

class SafeThread(threading.Thread):
    """
    Thread cíclica segura, com evento de parada.
    Target deve ser uma callable sem argumentos.
    """
    def __init__(self, target):
        threading.Thread.__init__(self)
        self.daemon = True
        self.target = target
        self.stop_ev = threading.Event()

    def stop(self):
        self.stop_ev.set()

    def run(self):
        while not self.stop_ev.is_set():
            self.target()

class TelloZune:
    """
    Classe para controlar e se comunicar com o drone DJI Tello.
    Args:
        text_input (bool, optional): Se True, aceita comandos de texto via terminal. Padrão: False.
    """
    def __init__(
        self,
        TELLOIP: str = '192.168.10.1',
        UDPPORT: int = 8889,
        VIDEO_SOURCE: str = "udp://@0.0.0.0:11111",
        UDPSTATEPORT: int = 8890,
        text_input: bool = False
    ) -> None:
        # Endereços UDP
        self.localaddr = ('', UDPPORT)
        self.telloaddr = (TELLOIP, UDPPORT)
        self.stateaddr = ('', UDPSTATEPORT)
        self.video_source = VIDEO_SOURCE

        # Estado interno
        self.fps = 0
        self.ready = False
        self.is_route_active = False
        self.state_value: list[str] = []
        self.image_size: tuple[int, int] = (960, 720)
        self.start_time = time.time()
        self.num_frames = 0
        self.elapsed_time = 0
        self.last_rc_control_timestamp = 0
        self.udp_cmd_ret = ''
        self.TIME_BTW_RC_CONTROL_COMMANDS = 0.001 # Intervalo entre comandos de controle remoto
        self.video = None

        # Fila de frames
        self.q = Queue(maxsize=1)
        self.frame = None

        # Fila de comandos
        self.command_queue: Queue[str] = Queue()
        self.command_events: dict[str, threading.Event] = {}
        self.current_command = None
        self.cmd_lock = threading.Lock()

        # Eventos e contadores
        self.cmd_recv_ev = threading.Event()
        self.timer_ev = threading.Event()
        self.cmd_count = 1
        self.state_count = 1
        self.event_list: list[dict] = []
        self.event_list.append({'commands': ['command'], 'period': 100, 'interval': 0, 'info': 'keep alive'})
        self.state_list = [
            {'state': 'bat',    'period': 200, 'info': 'Porcentagem de bateria', 'val': '80'},
            {'state': 'tof',    'period': 25,  'info': 'Altura em cm',           'val': '10'},
            {'state': 'temph',  'period': 200, 'info': 'Temperatura máxima',     'val': '60'},
            {'state': 'baro',   'period': 600, 'info': 'Pressão',                'val': '65'},
            {'state': 'time',   'period': 50,  'info': 'Tempo de vôo',           'val': '10'},
        ]

        # Sockets
        self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_cmd.bind(self.localaddr)
        self.sock_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_state.bind(self.stateaddr)

        # Threads cíclicas seguras
        self.receiverThread = SafeThread(target=self._response_cmd_receive) # Thread de resposta de comando
        self.periodicCmdThread = SafeThread(target=self._periodic_cmd) # Thread de comandos periódicos
        self.videoThread = SafeThread(target=self._video) # Thread de vídeo
        self.stateThread = SafeThread(target=self._state_receive) # Thread de estado
        self.movesThread = SafeThread(target=self._read_queue) # Thread de movimentos
        self.textInputThread = SafeThread(target=self._text_input) # Thread de entrada de texto pelo terminal

        # Inicialização
        self.enable_text_input = text_input

    def _execute_route(self, commands: list, interval: int=0) -> None:
        """
        Executa uma sequência de comandos (rota) em sua própria thread.
        Args:
            commands (list): A lista de comandos a serem executados.
            interval (int): O tempo de espera em segundos entre cada comando.
        """
        self.is_route_active = True
        try:
            for i, cmd in enumerate(commands):
                print(f"Executando passo {i + 1}/{len(commands)} da rota: '{cmd}'")
                self.add_command(cmd)

                # Se não for o último comando e houver intervalo, manda o comando "delay"
                if i < len(commands) - 1 and interval > 0:
                    self.add_command(f"delay {interval}")
        except Exception as e:
            print(f"Erro ao executar a rota: {e}")
        finally:
            # Garante que a flag seja liberada, mesmo que ocorra um erro
            print("Rota finalizada.")
            self.is_route_active = False

    def _video(self) -> None:
        """Thread de vídeo."""
        try:
            if self.video is not None:
                ret, frame = self.video.read()
                if ret:
                    frame = cv2.resize(frame, self.image_size)
                    self.frame = frame
                    if not self.q.full():
                        self.q.put(frame)
            else:
                print("Erro: self.video é None, não é possível ler o frame.")
        except Exception as e:
            print(f"Erro na thread de vídeo: {e}")

    def _periodic_cmd(self) -> None:
        """
        Thread que verifica e dispara eventos periódicos.
        Ignora o 'keep alive' se outra atividade estiver próxima.
        """
        try:
            cycles_to_next_activity = float('inf') # Ciclos até a próxima atividade programada
            KEEPALIVE_CMD = 'command'
            KEEPALIVE_THRESHOLD_CYCLES = 150 # Limite de 15 segundos = 150 ciclos de 0.1s

            for ev in self.event_list: # Calcula o tempo até a próxima atividade programada
                if 'commands' in ev and ev['commands'] == [KEEPALIVE_CMD]: # Ignora o próprio evento 'keep alive' nesta verificação
                    continue

                if 'period' in ev:
                    period = int(ev['period'])
                    # Calcula quantos ciclos faltam para a próxima execução deste evento
                    cycles_left = period - (self.cmd_count % period)
                    if cycles_left < cycles_to_next_activity:
                        cycles_to_next_activity = cycles_left

            for ev in self.event_list: # Verifica cada evento na lista
                if 'period' not in ev or 'commands' not in ev:
                    continue
                period = int(ev['period'])

                if self.cmd_count % period == 0: # Verifica se é a hora de executar este evento
                    is_keep_alive_event = (ev['commands'] == [KEEPALIVE_CMD])
                    # Lógica para ignorar o 'keep alive' se outra atividade estiver próxima
                    if is_keep_alive_event and cycles_to_next_activity <= KEEPALIVE_THRESHOLD_CYCLES:
                        continue # Pula a execução deste evento

                    # Execução normal
                    # Trata como rota se tiver mais de um comando, nenhuma rota estiver ativa e o intervalo for maior que 0
                    if len(ev['commands']) > 1 and not self.is_route_active and ev['interval'] > 0:
                        print(f"Disparando rota periódica: {ev.get('info', 'N/A')}")
                        threading.Thread(
                            target=self._execute_route,
                            args=(ev['commands'], ev.get('interval')),
                            daemon=True
                        ).start()
                    
                    # Trata como comando simples se tiver exatamente um comando
                    elif len(ev['commands']) == 1:
                        cmd = ev['commands'][0]
                        self.add_command(cmd)

            self.timer_ev.wait(0.1)
            self.cmd_count += 1

        except Exception as e:
            print(f"Erro na thread de comandos periódicos: {e}")
            time.sleep(1)

    def _response_cmd_receive(self) -> None:
        """Recebe strings de resposta de comando via socket UDP."""
        try:
            data, _ = self.sock_cmd.recvfrom(2048)
            self.udp_cmd_ret = data.decode("utf-8")
            self.cmd_recv_ev.set()
        except Exception as e:
            print(f"Erro na thread de recebimento de comando: {e}")

    def _state_receive(self) -> None:
        """Recebe strings de estado via socket UDP e atualiza state_value e state_list."""
        try:
            data, _ = self.sock_state.recvfrom(512)
            val = data.decode("utf-8").rstrip()
            self.state_value = val.replace(';', ':').split(':')
            for state in self.state_list:
                if self.state_count % state['period'] == 0:
                    raw = self.get_state_field(state['state']) or ''
                    state['val'] = raw.rstrip()
            self.state_count += 1
        except Exception as e:
            print(f"Erro na thread de estado: {e}")

    def _read_queue(self):
        """Lê comandos da fila, envia ao drone e exibe resposta."""
        try:
            cmd = self.command_queue.get(timeout=1)
            self.current_command = cmd
            
            if cmd.startswith("delay"): # Novo comando: "delay x" para pausar x segundos
                seconds = float(cmd.split()[1])
                time.sleep(seconds)
                return

            timeout = 8.0 if cmd.split()[0] in ['forward','back','left','right','up','down','cw','ccw'] else 2.0
            resp = self.send_cmd_return(cmd, timeout=timeout)

            print(f"{cmd}\t{resp}")
            time.sleep(0.01)
        except Empty:
            return

    def _text_input(self) -> None:
        """Thread que lê comandos de texto do terminal."""
        try:
            cmd = input("Comando > ")
            if cmd.lower() == 'exit':
                print("Sinal de parada recebido. Encerrando entrada de texto...")
                self.textInputThread.stop() # Sinaliza para a thread parar
                return
            self._process_text_command(cmd) # Para qualquer outro comando, chama o processador
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando entrada de texto...")
            self.textInputThread.stop()
        except Exception as e:
            print(f"Erro inesperado na entrada de texto: {e}")

    def _process_text_command(self, cmd: str) -> None:
        """
        Processa um comando de texto, o divide e chama o método apropriado.
        Args:
            cmd (str): Comando de texto a ser processado
        """
        if not cmd:
            return
        parts = cmd.strip().lower().split()
        base_cmd = parts[0]
        # Comandos simples, sem argumentos
        if base_cmd == 'takeoff':
            self.takeoff()
        elif base_cmd == 'land':
            self.land()
        elif base_cmd == 'emergency':
            self.add_command('emergency')
        # Comandos com 1 argumento (distância ou graus)
        elif base_cmd in ['up', 'down', 'left', 'right', 'forward', 'back', 'cw', 'ccw']:
            if len(parts) == 2:
                self.add_command(cmd)
            else:
                print(f"Erro: O comando '{base_cmd}' requer um valor (ex: '{base_cmd} 50').")
        else: # Nenhum dos anteriores, trata como comando desconhecido
            print(f"Comando desconhecido: '{base_cmd}'")

    def add_command(self, command: str) -> None:
        """
        Enfileira um comando.
        Args:
            command (str): Comando a ser enfileirado
        """
        try:
            self.command_queue.put(command)
        except Exception as e:
            print(f"Erro ao adicionar comando: {e}")

    def add_periodic_event(self, cmd: str, period: int, info: str = "", interval: int = 10) -> None:
        """
        Adiciona evento periódico.
        Args:
            cmd (str): Comando a ser enviado
            period (int): Período em frames
            info (str): Informação adicional
        """
        # Divide a rota em comandos individuais. Ex: "forward 100 e cw 90" -> ['forward 100', 'cw 90']
        command_list = [c.strip() for c in cmd.split(' e ')]

        # Adiciona a rota como um único evento
        self.event_list.append({
            'commands': command_list,
            'period': int(period),
            'interval': int(interval), # Intervalo em segundos
            'info': str(info)
        })
        print(f"Evento periódico adicionado: {info}, período: {period} frames, comandos: {command_list}")

    def remove_periodic_event(self, cmd: str) -> None:
        """
        Remove evento periódico.
        Args:
            cmd (str): Comando a ser removido
        """
        self.event_list = [ev for ev in self.event_list if ev['commands'] != cmd]

    def remove_last_event(self, qtd: int=1) -> list[dict] | None:
        """
        Remove o(s) último(s) evento(s) adicionado(s).
        Args:
            qtd (int): Quantidade de eventos a remover (opcional, padrão=1)
        Returns:
            list[dict]: Eventos removidos ou None se nenhum foi removido
        """
        removed_events = []
        for _ in range(qtd):
            if len(self.event_list) == 1: # Mantém o evento de keep alive
                if not removed_events:
                    print("Nenhum evento para remover.")
                break
            removed_events.append(self.event_list.pop())
        print(f"Eventos removidos: {removed_events}")
        return removed_events if removed_events else None

    def set_image_size(self, image_size: tuple[int, int] = (960, 720)) -> None:
        """
        Define tamanho da imagem.
        Args:
            image_size (tuple): Tamanho da imagem (largura, altura)
        """
        self.image_size = image_size

    def get_frame(self, timeout: float = 1.0) -> np.ndarray:
        """
        Retorna próximo frame da fila.
        Returns:
            np.ndarray: Frame do vídeo (920x720)
        """
        try:
            return self.q.get(timeout=timeout)
        except Empty:
            # Retorna um frame preto
            return np.zeros((self.image_size[1], self.image_size[0], 3), dtype=np.uint8)

    def stop_communication(self) -> None:
        """Para threads e fecha sockets."""
        self.receiverThread.stop()
        self.stateThread.stop()
        self.periodicCmdThread.stop()
        self.movesThread.stop()
        self.sock_cmd.close()
        self.sock_state.close()
        if self.textInputThread.is_alive():
            self.textInputThread.stop()
        print("Comunicação finalizada")

    def start_communication(self) -> None:
        """Inicia threads de comunicação e leitura de comandos."""
        if self.receiverThread.is_alive() is not True: self.receiverThread.start() # Thread de resposta
        if self.periodicCmdThread.is_alive() is not True: self.periodicCmdThread.start() # Thread de comandos periódicos
        if self.stateThread.is_alive() is not True: self.stateThread.start() # Thread de estado
        if self.movesThread.is_alive() is not True: self.movesThread.start() # Thread de movimentos
        print("Iniciando comunicação")

    def start_video(self) -> None:
        """Inicia a transmissão de vídeo do Tello."""
        self.send_cmd('streamon')

        time.sleep(1)

        self.video = cv2.VideoCapture(self.video_source, cv2.CAP_FFMPEG)

        if not self.videoThread.is_alive():
            self.videoThread.start()
        print("Vídeo iniciado")

    def stop_video(self) -> None:
        """Stop video stream"""
        self.send_cmd('streamoff')
        self.videoThread.stop()

    def wait_till_connected(self, timeout: int = 10) -> bool:
        """
        Bloqueia a execução até que o drone Tello esteja conectado.
        Use este método no início do seu código para garantir que o drone esteja pronto para receber comandos.
        Args:
            timeout (int): Tempo máximo de espera em segundos. Padrão é 10 segundos.
        Returns:
            bool: True se conectado com sucesso, False se o tempo limite for excedido.
        """
        # Inicia a thread que ouve as respostas do drone
        if not self.receiverThread.is_alive():
            self.receiverThread.start()

        start_time = time.time()

        while time.time() - start_time < timeout: # Se o loop durar mais que timeout, falha
            try:
                response = self.send_cmd_return('command')
                if response == 'ok':
                    elapsed = time.time() - start_time
                    print(f"Drone conectado em {elapsed:.2f} segundos.")
                    self.ready = True
                    return True
            except Exception as e:
                print(f"Erro durante a tentativa de conexão: {e}")
            
            time.sleep(0.5)

        print(f"Falha na conexão: Tempo limite de {timeout}s excedido. Verifique se o drone está ligado")
        return False

    def send_cmd_return(self, cmd: str, timeout: float = 1.0) -> str:
        """
        Envia um comando para o drone Tello via UDP e espera pela resposta.
        O comando é enviado via UDP e a resposta é recebida na mesma conexão.
        Args:
            cmd (str): Comando a ser enviado para o drone.
            timeout (float): Tempo máximo de espera em segundos. Padrão é 1.0 segundo.
        Returns:
            str: Resposta do drone. Verifique a documentação do SDK do Tello para os comandos válidos.
        """
        with self.cmd_lock:
            self.cmd_recv_ev.clear()
            self.udp_cmd_ret = ""
            
            cmd_bytes = cmd.encode("utf-8")
            self.sock_cmd.sendto(cmd_bytes, self.telloaddr)
            
            # Espera a resposta (a thread recebedora vai dar .set() no evento)
            self.cmd_recv_ev.wait(timeout)
            
            return self.udp_cmd_ret

    def send_cmd(self, cmd: str) -> None:
        """
        Envia um comando para o drone Tello via UDP. Não espera pela resposta.
        Args:
            cmd (str): Consulte a documentação do SDK do Tello para os comandos válidos.
        """
        cmd_bytes = cmd.encode("utf-8")
        _ = self.sock_cmd.sendto(cmd_bytes, self.telloaddr)

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int, yaw_velocity: int) -> None:
        """
        Envia comandos de controle remoto para o drone, enviados a cada 0.001 segundos, para evitar sobrecarga de comandos.
        Intervalo pode ser ajustado por meio da variável TIME_BTW_RC_CONTROL_COMMANDS.
        Args:
            left_right_velocity: -100~100 (left/right)
            forward_backward_velocity: -100~100 (forward/backward)
            up_down_velocity: -100~100 (up/down)
            yaw_velocity: -100~100 (yaw)
        """
        if time.time() - self.last_rc_control_timestamp > self.TIME_BTW_RC_CONTROL_COMMANDS:
            self.last_rc_control_timestamp = time.time()
            cmd = f'rc {left_right_velocity} {forward_backward_velocity} {up_down_velocity} {yaw_velocity}'
            self.send_cmd(cmd)

    def takeoff(self) -> None:
        """Decola o drone."""
        print("Decolando")
        self.add_command("takeoff")
        # time.sleep(4)
    
    def land(self) -> None:
        """Pousa o drone."""
        print("Pousando")
        answer = self.send_cmd_return("land", timeout=5.0) # Bom dar um timeout maior no pouso
        trys = 0
        max_trys = 3
        
        while answer != 'ok' and trys < max_trys:
            print(f"Resposta inesperada para 'land': '{answer}'. Tentando novamente...")
            time.sleep(1)
            answer = self.send_cmd_return("land", timeout=5.0)
            trys += 1
            
        if answer != 'ok':
            print("Aviso: Falha ao confirmar pouso após várias tentativas.")

    def start_tello(self) -> bool:
        """
        Inicializa o vídeo e a comunicação com o drone.
        Deve ser chamado após criar instância.
        Returns:
            bool: True se inicialização bem-sucedida, False caso contrário.
        """
        if not self.receiverThread.is_alive():
            is_connected = self.wait_till_connected() # A chamada retorna True ou False
            if not is_connected: # Se a conexão falhou, interrompe a inicialização
                return False
            self.start_communication()
            self.start_video()
        if self.enable_text_input:
            if not self.textInputThread.is_alive():
                self.textInputThread.start()
            print("Entrada de texto habilitada.")
        
        return True
    
    def is_vertical_moving(self, height_threshold: float = 5.0, sample_interval: float = 0.1) -> bool:
        """
        Detecta movimento vertical comparando a altura em dois instantes.
        Args:
            height_threshold (float): Diferença mínima de altura (cm) para considerar que está se movendo verticalmente.
            sample_interval (float): Tempo em segundos entre as duas amostras de altura.
        Returns:
            bool: True se o drone estiver se movendo verticalmente, False caso contrário.
        """
        h1 = float(self.get_state_field('tof'))
        time.sleep(sample_interval)
        h2 = float(self.get_state_field('tof'))
        return abs(h2 - h1) > height_threshold

    def end_tello(self) -> None:
        """Finaliza o drone Tello. Pousa se possivel, encerra o video e a comunicacao."""
        self.stop_video()
        self.stop_communication()

    def get_state_field(self, key: str) -> str:
        """
        Retorna o valor de um campo específico do estado do drone.
        Args:
            key (str): Field name
        Returns:
            str: Field value
        """
        state = self.state_value
        if key in state:
            index = state.index(key) + 1
            return state[index]
        return ""

    def get_battery(self) -> int:
        """
        Retorna o nível da bateria do drone.
        Returns:
            int: 0-100
        """
        return int(self.get_state_field('bat'))

    def calc_fps(self) -> int:
        """
        Calcula o FPS do vídeo
        Returns:
            int: FPS
        """
        self.num_frames += 1
        self.elapsed_time = time.time() - self.start_time
        if self.elapsed_time >= 1:
            self.fps = int(self.num_frames / self.elapsed_time)
            self.num_frames = 0
            self.start_time = time.time() 
        return self.fps

    def get_info(self) -> tuple:
        """
        Retorna tupla com os valores atualizados em state_list.
        Returns:
            tuple: (bateria, altura, temperatura, pressão, tempo)
        """
        d = {ev['state']: ev['val'] for ev in self.state_list}
        return (
            d.get('bat'),
            d.get('tof'),
            d.get('temph'),
            d.get('baro'),
            d.get('time'),
        )
    
    def get_speed(self) -> tuple[float, float, float]:
        """
        Retorna a velocidade atual do drone.
        Returns:
            tuple: (vx, vy, vz) velocidades em cm/s
        """
        try:
            vx = float(self.get_state_field('vgx'))
            vy = float(self.get_state_field('vgy'))
            vz = float(self.get_state_field('vgz'))
            return vx, vy, vz
        except (ValueError, TypeError):
            return 0.0, 0.0, 0.0

    def clear_command_queue(self):
        """Limpa a fila de comandos"""
        with self.command_queue.mutex:
            self.command_queue.queue.clear()
        print("Fila de comandos limpa.")

    def emergency_stop(self):
        """
        Envia comando de emergência para o drone, parando-o imediatamente. Limpa a fila de comandos antes de enviar o comando de emergência.
        """
        self.clear_command_queue()
        self.send_cmd("emergency")

