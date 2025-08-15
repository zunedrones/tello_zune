"""
Biblioteca tello_zune, serve para controlar, e obter informacoes do drone DJI Tello.
Esta biblioteca é baseada no SDK do Tello, e implementa uma interface de alto nível para controle do drone.
"""
import time
import threading
import numpy as np
from queue import Queue, Empty

WIDTH = 960
HEIGHT = 720

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
    Classe para controlar o drone DJI Tello.
    Args:
        simulate (bool, optional): Se True, inicia no modo de simulação. Padrão: True.
        text_input (bool, optional): Se True, aceita comandos de texto via terminal. Padrão: False.
    """
    import socket
    import cv2
    def __init__(
        self,
        simulate: bool = True,
        TELLOIP: str = '192.168.10.1',
        UDPPORT: int = 8889,
        VIDEO_SOURCE: str = "udp://@0.0.0.0:11111",
        UDPSTATEPORT: int = 8890,
        DEBUG: bool = False,
        text_input: bool = False
    ) -> None:
        # Endereços UDP
        self.localaddr = ('', UDPPORT)
        self.telloaddr = (TELLOIP, UDPPORT)
        self.stateaddr = ('', UDPSTATEPORT)
        self.video_source = VIDEO_SOURCE

        # Estado interno
        self.debug = DEBUG
        self.fps = 0
        self.ready = False
        self.state_value: list[str] = []
        self.image_size: tuple[int, int] = (WIDTH, HEIGHT)
        self.start_time = time.time()
        self.num_frames = 0
        self.elapsed_time = 0
        self.last_rc_control_timestamp = 0
        self.udp_cmd_ret = ''
        self.TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # Intervalo entre comandos de controle remoto
        self.video = None

        # Fila de frames
        self.q = Queue(maxsize=1)
        self.frame = None

        # Fila de comandos
        self.command_queue: Queue[str] = Queue()

        # Eventos e contadores
        self.cmd_recv_ev = threading.Event()
        self.timer_ev = threading.Event()
        self.cmd_count = 1
        self.state_count = 1
        self.eventlist: list[dict] = []
        self.eventlist.append({'cmd': 'command', 'period': 100, 'info': 'keep alive'})
        self.state_list = [
            {'state': 'bat',    'period': 100, 'info': 'Porcentagem de bateria', 'val': ''},
            {'state': 'tof',    'period': 25,  'info': 'Altura em cm',           'val': ''},
            {'state': 'temph',  'period': 100, 'info': 'Temperatura máxima',     'val': ''},
            {'state': 'baro',   'period': 500, 'info': 'Pressão',                'val': '65'},
            {'state': 'time',   'period': 25,  'info': 'Tempo de vôo',           'val': ''},
        ]

        # Sockets
        self.sock_cmd = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        self.sock_cmd.bind(self.localaddr)
        self.sock_state = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        self.sock_state.bind(self.stateaddr)

        # Threads cíclicas seguras
        self.receiverThread = SafeThread(target=self.__receive)
        self.periodicCmdThread = SafeThread(target=self.__periodic_cmd)
        self.videoThread = SafeThread(target=self.__video)
        self.stateThread = SafeThread(target=self.__state_receive)
        self.movesThread = SafeThread(target=self.__read_queue)
        self.periodicStateThread = SafeThread(target=self.__periodic_state)
        self.textInputThread = SafeThread(target=self.__text_input)

        # Inicialização
        self.simulate = simulate
        self.movesThread.start()
        self.periodicStateThread.start()
        self.enable_text_input = text_input

    def __video(self) -> None:
        """Thread de vídeo."""
        try:
            if self.video is not None:
                ret, frame = self.video.read()
                if ret:
                    frame = self.cv2.resize(frame, self.image_size)
                    self.frame = frame
                    if not self.q.full():
                        self.q.put(frame)
            else:
                print("Erro: self.video é None, não é possível ler o frame.")
        except Exception as e:
            print(f"Erro na thread de vídeo: {e}")


    def add_periodic_event(self, cmd: str, period: int, info: str = "") -> None:
        """
        Adiciona evento periódico.
        Args:
            cmd (str): Comando a ser enviado
            period (int): Período em frames
            info (str): Informação adicional
        """
        self.eventlist.append({'cmd':str(cmd), 'period':int(period), 'info':str(info), 'val':str("")})

    def __periodic_cmd(self) -> None:
        """Thread para enviar comandos periódicos."""
        try:
            for ev in self.eventlist:
                period = ev['period']
                if self.cmd_count % int(period) == 0:
                    cmd = ev['cmd']
                    info = ev['info']
                    ret = self.send_cmd_return(cmd).rstrip()
                    ev['val'] = str(ret)
            # Tempo de espera entre os comandos (~100ms)
            self.timer_ev.wait(0.1)
            self.cmd_count += 1
        except Exception:
            pass

    def __periodic_state(self) -> None:
        for ev in self.state_list:
            if self.state_count % ev['period'] == 0:
                raw = self.get_state_field(ev['state']) or ''
                ev['val'] = raw.rstrip()
        self.timer_ev.wait(0.1)
        self.state_count += 1

    def __receive(self) -> None:
        """Recebe strings de resposta de comando."""
        try:
            data, _ = self.sock_cmd.recvfrom(2048)
            self.udp_cmd_ret = data.decode(encoding="utf-8")
            self.cmd_recv_ev.set()
        except Exception:
            pass

    def __state_receive(self) -> None:
        """Recebe strings de estado."""
        data, _ = self.sock_state.recvfrom(512)
        val = data.decode(encoding="utf-8").rstrip()
        self.state_value = val.replace(';',':').split(':')

    def __read_queue(self) -> None:
        """Lê comandos da fila, envia ao drone e exibe resposta."""
        try:
            # Tenta pegar um comando; se não houver em 1s, dispara Empty
            cmd = self.command_queue.get(timeout=1)
        except Empty:
            return  # Sem comando, volta ao loop

        self.send_cmd(cmd) # Envia o comando

        if self.cmd_recv_ev.wait(timeout=2) and self.udp_cmd_ret: # Espera pela resposta
            resp = self.udp_cmd_ret.rstrip()
            self.cmd_recv_ev.clear()
        else:
            resp = '' # Timeout sem resposta

        print(f"{cmd}\t|{resp}")

        # Pequeno intervalo para não sobrecarregar
        time.sleep(0.1)

    def __text_input(self) -> None:
        """Thread para entrada de texto."""
        try:
            cmd = input("Comando digitado: ")
            if cmd.lower() == 'exit':
                self.textInputThread.stop()
            self.add_command(cmd)
        except KeyboardInterrupt:
            self.textInputThread.stop()
        except Exception as e:
            print(f"Erro na entrada de texto: {e}")

    def add_command(self, command: str) -> None:
        """Enfileira um comando."""
        try:
            self.command_queue.put(command)
            print(f"Comando enfileirado: {command}\n")
        except Exception as e:
            print(f"Erro ao adicionar comando: {e}")

    def set_image_size(self, image_size: tuple[int, int] = (960, 720)) -> None:
        """
        Define tamanho da imagem.
        Args:
            image_size (tuple): Tamanho da imagem (largura, altura)
        """
        self.image_size = image_size

    def get_frame(self) -> np.ndarray:
        """
        Retorna próximo frame da fila.
        Returns:
            np.ndarray: Frame do vídeo (920x720)
        """
        return self.q.get()

    def stop_communication(self) -> None:
        """Para threads e fecha sockets."""
        self.receiverThread.stop()
        self.stateThread.stop()
        self.periodicCmdThread.stop()
        self.movesThread.stop()
        self.sock_cmd.close()
        self.sock_state.close()
        self.periodicStateThread.stop()
        if self.textInputThread.is_alive():
            self.textInputThread.stop()
        print("Comunicação finalizada")

    def start_communication(self) -> None:
        """
        Inicia threads de comunicação e leitura de comandos.
        """
        if self.receiverThread.is_alive() is not True: self.receiverThread.start()
        if self.periodicCmdThread.is_alive() is not True:  self.periodicCmdThread.start()
        if self.stateThread.is_alive() is not True:  self.stateThread.start()
        print("Iniciando comunicação")

    def start_video(self: "TelloZune") -> None:
        """
        Inicia a transmissão de vídeo do Tello.
        """
        self.send_cmd('streamon')

        time.sleep(1)

        self.video = self.cv2.VideoCapture(self.video_source, self.cv2.CAP_FFMPEG)

        if not self.videoThread.is_alive():
            self.videoThread.start()
        print("Vídeo iniciado")

    def stop_video(self) -> None:
        """Stop video stream"""
        self.send_cmd('streamoff')
        self.videoThread.stop()

    def wait_till_connected(self, timeout: int = 10) -> None:
        """
        Bloqueia a execução até que o drone Tello esteja conectado.
        Use este método no início do seu código para garantir que o drone esteja pronto para receber comandos.
        """
        self.receiverThread.start()
        start_counter = time.time()

        ret = None
        wait_time = 0
        while True:
            try:
                ret = self.send_cmd_return('command')

                wait_time = time.time() - start_counter

                if self.debug== True: ret = "OK"

            except Exception as e:
                print(f"Erro ao enviar comando: {e}")

            if str(ret) == 'ok':
                print(f"Drone conectado em {wait_time:.2f} segundos.")
                break
            if time.time() - start_counter > timeout:
                print("Tempo limite de conexão excedido. Verifique o drone e a rede.")
                break
            time.sleep(0.1)

    def send_cmd_return(self, cmd: str) -> str:
        """
        Envia um comando para o drone Tello via UDP e espera pela resposta.
        O comando é enviado via UDP e a resposta é recebida na mesma conexão.
        Args:
            cmd (str): Comando a ser enviado para o drone.
        Returns:
            str: Resposta do drone. Verifique a documentação do SDK do Tello para os comandos válidos.
        """
        self.udp_cmd_ret = str()
        cmd_bytes = cmd.encode(encoding="utf-8")
        _ = self.sock_cmd.sendto(cmd_bytes, self.telloaddr)
        self.cmd_recv_ev.wait(1)
        self.cmd_recv_ev.clear()
        return self.udp_cmd_ret

    def send_cmd(self, cmd: str) -> None:
        """
        Envia um comando para o drone Tello via UDP. Não espera pela resposta.
        Args:
            cmd (str): Consulte a documentação do SDK do Tello para os comandos válidos.
        """
        cmd_bytes = cmd.encode(encoding="utf-8")
        _ = self.sock_cmd.sendto(cmd_bytes, self.telloaddr)

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int,
                        yaw_velocity: int) -> None:
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
            cmd = 'rc {} {} {} {}'.format(
                left_right_velocity,
                forward_backward_velocity,
                up_down_velocity,
                yaw_velocity
            )
            self.send_cmd(cmd)

    def takeoff(self) -> None:
        """Decola o drone Tello."""
        print("Decolando")
        self.add_command("takeoff")
        # time.sleep(4)
    
    def land(self) -> None:
        """Pousa o drone Tello."""
        print("Pousando")
        while float(self.get_state_field('tof')) >= 30:
            self.send_rc_control(0, 0, -70, 0)
        self.add_command("land")
        #time.sleep(4)

    def start_tello(self) -> None:
        """
        Inicializa o vídeo e, se não simulação, decola.
        Deve ser chamado após criar instância.
        """
        if not self.receiverThread.is_alive(): # Se a thread de recebimento não estiver ativa
            self.wait_till_connected() # Comentar para usar webcam
            self.start_communication()
            self.start_video()

        if not self.simulate:
            self.takeoff()

        if self.enable_text_input:
            if not self.textInputThread.is_alive():
                self.textInputThread.start()
            print("Entrada de texto habilitada")

    def end_tello(self) -> None:
        """
        Finaliza o drone Tello. Pousa se possivel, encerra o video e a comunicacao.
        """
        self.stop_video()
        if not self.simulate:
            self.land()
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
