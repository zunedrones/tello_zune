"""
Biblioteca tello_zune, serve para controlar, e obter informacoes do drone DJI Tello.
"""
import time
import threading
import cv2
import numpy as np
from queue import Queue, Empty

FONT = cv2.FONT_HERSHEY_SIMPLEX
COLOR = (0, 255, 0)

WIDTH = 960
HEIGHT = 720

ORG = (30, 30)
ORG_FPS = (10, 30)  # Canto superior esquerdo
ORG_BAT = (WIDTH - 200, HEIGHT - 10)  # Canto inferior direito
ORG_INFO = (10, HEIGHT - 90)  # Canto inferior esquerdo

FONTSCALE = 1
FONTSCALE_SMALL = 0.6
THICKNESS = 2
THICKNESS_SMALL = 1
LINE_SPACING = 20 # Espaço entre linhas, para exibição de dados

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
    """
    def __init__(
        self,
        simulate: bool = True,
        TELLOIP: str = '192.168.10.1',
        UDPPORT: int = 8889,
        VIDEO_SOURCE: str = "udp://@0.0.0.0:11111",
        UDPSTATEPORT: int = 8890,
        DEBUG: bool = False,
    ) -> None:
        # Endereços UDP
        self.localaddr = ('', UDPPORT)
        self.telloaddr = (TELLOIP, UDPPORT)
        self.stateaddr = ('', UDPSTATEPORT)
        self.video_source = VIDEO_SOURCE

        # Estado interno
        self.debug = DEBUG
        self.fps = 0
        self.state_value: list[str] = []
        self.image_size: tuple[int, int] = (WIDTH, HEIGHT)
        self.start_time = time.time()
        self.num_frames = 0
        self.elapsed_time = 0
        self.last_rc_control_timestamp = 0
        self.udp_cmd_ret = ''
        self.TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # Intervalo entre comandos de controle remoto

        # Fila de frames
        self.q = Queue(maxsize=1)
        self.frame = None

        # Fila de comandos
        self.command_queue: Queue[str] = Queue()

        # Eventos e contadores
        self.cmd_recv_ev = threading.Event()
        self.timer_ev = threading.Event()
        self.count = 1
        self.eventlist: list[dict] = []
        self.eventlist.append({'cmd': 'command', 'period': 100, 'info': ''})

        # Sockets
        import socket
        self.sock_cmd = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        self.sock_cmd.bind(self.localaddr)
        self.sock_state = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        self.sock_state.bind(self.stateaddr)

        # Threads seguras
        self.receiverThread = SafeThread(target=self.__receive, name="ReceiverThread")
        self.eventThread = SafeThread(target=self.__periodic_cmd, name="PeriodicCmdThread")
        self.videoThread = SafeThread(target=self.__video, name="VideoThread")
        self.stateThread = SafeThread(target=self.__state_receive, name="StateReceiveThread")
        self.movesThread = SafeThread(target=self.__read_queue, name="CommandQueueThread")

        # Inicialização
        self.simulate = simulate
        self.movesThread.start()

    def __video(self) -> None:
        """Thread de vídeo."""
        self.video = self.cv2.VideoCapture(self.video_source)
        while True:
            try:
                # frame from stream
                ret, frame = self.video.read()
                if ret:
                    frame = self.cv2.resize(frame, self.image_size)
                    self.frame = frame
                    if not self.q.full():
                        self.q.put(frame)
            except Exception as e:
                print(f"Error in __video thread: {e}")

    def add_periodic_event(self, cmd: str, period: int, info: str = "") -> None:
        """
        Adiciona evento periódico.
        Args:
            cmd (str): Comando a ser enviado
            period (int): Período em frames
            info (str): Informação adicional
        """
        self.eventlist.append({'cmd':str(cmd),'period':int(period),'info':str(info), 'val':str("")})
    def __periodic_cmd(self) -> None:
        """Thread para enviar comandos periódicos."""
        try:

            for ev in self.eventlist:
                period = ev['period']
                if self.count % int(period) == 0:
                    cmd = ev['cmd']
                    info = ev['info']
                    ret = self.send_cmd_return(cmd).rstrip()

                    ev['val'] = str(ret)

            # scheduler base time ~ 100 ms
            self.timer_ev.wait(0.1)

            self.count +=1
        except Exception:
            pass

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
        """Lê comandos da fila e envia ao drone."""
        while True:
            try:
                cmd = self.command_queue.get(timeout=1)
                resp = self.send_cmd_return(cmd)
                time.sleep(3)
                print(f"{cmd}, {resp}")
            except Empty:
                continue

    def add_command(self, command: str) -> None:
        """Enfileira um comando."""
        try:
            self.command_queue.put(command)
            print(f"Comando enfileirado: {command}")
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
        self.eventThread.stop()
        self.sock_cmd.close()

    def start_communication(self) -> None:
        """
        Inicia threads de comunicação e leitura de comandos.
        """
        if self.receiverThread.is_alive() is not True: self.receiverThread.start()
        if self.eventThread.is_alive() is not True:  self.eventThread.start()
        if self.stateThread.is_alive() is not True:  self.stateThread.start()

    def stop_video(self) -> None:
        """Stop video stream"""
        self.send_cmd('streamoff')
        self.videoThread.stop()

    def wait_till_connected(self) -> None:
        """
        Bloqueia a execução até que o drone Tello esteja conectado.
        Use este método no início do seu código para garantir que o drone esteja pronto para receber comandos.
        """
        self.receiverThread.start()

        while True:
            try:
                ret = self.send_cmd_return('command')

                if self.debug== True: ret = "OK"

            except Exception:
                exit()
            if str(ret) != 'None':
                break

    def send_cmd_return(self, cmd: str) -> str:
        """
        Envia um comando para o drone Tello via UDP e espera pela resposta.
        O comando é enviado via UDP e a resposta é recebida na mesma conexão.
        Args:
            cmd (str): Comando a ser enviado para o drone.
        Returns:
            str: Resposta do drone. Verifique a documentação do SDK do Tello para os comandos válidos.
        """
        self.udp_cmd_ret = None
        cmd = cmd.encode(encoding="utf-8")
        _ = self.sock_cmd.sendto(cmd, self.telloaddr)
        self.cmd_recv_ev.wait(0.3)
        self.cmd_recv_ev.clear()
        return self.udp_cmd_ret

    def send_cmd(self, cmd: str) -> None:
        """
        Envia um comando para o drone Tello via UDP. Não espera pela resposta.
        Args:
            cmd (str): See Tello SDK for walid commands
        """
        cmd = cmd.encode(encoding="utf-8")
        _ = self.sock_cmd.sendto(cmd, self.telloaddr)

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
        self.send_cmd("takeoff")
        time.sleep(4)
    
    def land(self) -> None:
        """Pousa o drone Tello."""
        while float(self.get_state_field('tof')) >= 30:
            self.send_rc_control(0, 0, -70, 0)
        self.send_cmd("land")
        #time.sleep(4)

    def start_tello(self) -> None:
        """
        Inicializa o vídeo e, se não simulação, decola.
        Deve ser chamado após criar instância.
        """
        if not self.receiverThread.is_alive(): # Se a thread de recebimento não estiver ativa
            self.wait_till_connected()
            self.start_communication()
            self.start_video()
            print("Conectei ao Tello")
            print("Abrindo vídeo do Tello")

        if not self.simulate:
            self.takeoff()

    def end_tello(self) -> None:
        """
        Finaliza o drone Tello. Pousa se possivel, encerra o video e a comunicacao.
        """
        self.stop_video()
        if not self.simulate:
            print("Pousando")
            self.land()
        self.stop_communication()
        print("Finalizei")

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

    def get_battery(self) -> int:
        """Retorna o nível da bateria do drone.
        Returns:
            int: 0-100
        """
        return self.get_state_field('bat')

    def calc_fps(self) -> int:
        """Calcula o FPS do vídeo
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
        Retorna informações do drone.
        Returns:
            tuple: (bateria, altura, temperatura máxima, pressão, tempo decorrido)
        """
        bat = self.get_state_field('bat')
        height = self.get_state_field('tof')
        temph = self.get_state_field('temph')
        pres = self.get_state_field('baro')
        time_elapsed = self.get_state_field('time')
        return bat, height, temph, pres, time_elapsed

    def write_info(self, frame: np.ndarray, fps: bool = False, bat: bool = False,
                   height: bool = False, temph: bool = False, pres: bool = False,
                   time_elapsed: bool = False) -> None:
        """
        Escreve informações no frame atual, posicionadas corretamente.

        Args:
            frame (MatLike): Frame do vídeo
            fps (bool): Escrever FPS (canto superior esquerdo)
            bat (bool): Escrever bateria (canto inferior direito)
            height (bool): Escrever altura (canto inferior esquerdo, reduzido)
            temph (bool): Escrever temperatura máxima (canto inferior esquerdo, reduzido)
            pres (bool): Escrever pressão (canto inferior esquerdo, reduzido)
            time_elapsed (bool): Escrever tempo decorrido (canto inferior esquerdo, reduzido)
        """

        if fps:
            cv2.putText(frame, f"FPS: {self.calc_fps()}", ORG_FPS, FONT, FONTSCALE, COLOR, THICKNESS)

        if bat:
            cv2.putText(frame, f"Battery: {self.get_battery()}%", ORG_BAT, FONT, FONTSCALE, COLOR, THICKNESS)

        y_offset = 0  # Para organizar as informações na parte inferior esquerda

        if height:
            cv2.putText(frame, f"{self.get_state_field('tof')}cm",
                        (ORG_INFO[0], ORG_INFO[1] + y_offset), FONT, FONTSCALE_SMALL, COLOR, THICKNESS_SMALL)
            y_offset += LINE_SPACING

        if temph:
            cv2.putText(frame, f"{self.get_state_field('temph')} C",
                        (ORG_INFO[0], ORG_INFO[1] + y_offset), FONT, FONTSCALE_SMALL, COLOR, THICKNESS_SMALL)
            y_offset += LINE_SPACING

        if pres:
            cv2.putText(frame, f"{self.get_state_field('baro')}hPa",
                        (ORG_INFO[0], ORG_INFO[1] + y_offset), FONT, FONTSCALE_SMALL, COLOR, THICKNESS_SMALL)
            y_offset += LINE_SPACING

        if time_elapsed:
            cv2.putText(frame, f"{self.get_state_field('time')}s",
                        (ORG_INFO[0], ORG_INFO[1] + y_offset), FONT, FONTSCALE_SMALL, COLOR, THICKNESS_SMALL)