"""
Biblioteca tello_zune, serve para controlar, e obter informacoes do drone DJI Tello.
"""
import time
import threading
import cv2
import numpy as np

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
    Safe cyclic thread, with stop function 
    Args:
        threading (Thread): Thred object
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
        simulate (bool, optional): Se True, inicia no modo de simulação, o drone não decola. Padrão em True.
    """
    import socket
    import cv2
    from queue import Queue

    def __init__(self, simulate=True, TELLOIP='192.168.10.1', UDPPORT=8889, VIDEO_SOURCE="udp://@0.0.0.0:11111", UDPSTATEPORT=8890, DEBUG=False) -> None:

        global drones

        self.localaddr = ('',UDPPORT)
        self.telloaddr = (TELLOIP,UDPPORT)
        self.video_source = VIDEO_SOURCE
        self.stateaddr = ('',UDPSTATEPORT)
        self.num_frames = 0
        self.start_time = time.time()

        self.debug = DEBUG

        # fps
        self.fps = 0

        # record satate value
        self.state_value = []
    
        # image size
        self.image_size = (WIDTH, HEIGHT) 

        # return measge from UDP
        self.udp_cmd_ret = ''

        # store a single image
        self.q = self.Queue()
        self.q.maxsize = 1

        # store a single image
        self.frame = None
        self.last_rc_control_timestamp = time.time()  # Inicializa o timestamp do controle remoto
        self.TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # in seconds
        
        # scheduler counter
        self.count = 1

        # command received event
        self.cmd_recv_ev = threading.Event()

        # timer event
        self.timer_ev = threading.Event()

        # periodic commands handler
        self.eventlist = list()

        # add first periodic command to be sent, keep-alive
        self.eventlist.append({'cmd':'command','period':100,'info':''})

        # # create UDP packet, for commands
        self.sock_cmd = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        self.sock_cmd.bind(self.localaddr)

        # tello state
        self.sock_state = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        self.sock_state.bind(self.stateaddr)

        # start receive thread
        self.receiverThread = SafeThread(target=self.__receive)
        #self.receiverThread.daemon = True
        
        # send periodic commands
        self.eventThread = SafeThread(target=self.__periodic_cmd)
        
        # start video thread
        self.videoThread = SafeThread(target=self.__video)

        # start video thread
        self.stateThread = SafeThread(target=self.__state_receive)

        self.simulate = simulate

        self.moves_thread = threading.Thread(target=self.readQueue) # Thread para ler a fila de comandos em paralelo
        self.stop_receiving = threading.Event() # Evento para parar de receber comandos
        self.queue_lock = threading.Lock() # Lock para a fila de comandos, assim não é alterada enquanto é lida
        self.command_queue = [] # Fila de comandos
        self.moves_thread.start()


    def __video(self):
        """Video thread
        """
        # stream handling
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

    def add_periodic_event(self,cmd,period,info=''):
        """Add periodic commands to the list

        Args:
            cmd (str): see tello SDK for command 
            period (cycle time): time interval for recurrent mesages
            info (str, optional): Hols a description of the command
        """
        self.eventlist.append({'cmd':str(cmd),'period':int(period),'info':str(info), 'val':str("")})

    def __periodic_cmd(self):
        """Thread to send periodic commands
        """
        try:

            for ev in self.eventlist:
                period = ev['period']

                if self.count % int(period) == 0:
                    #is time to run the command
                    cmd = ev['cmd']
                    info = ev['info']
                    ret = self.send_cmd_return(cmd).rstrip()
                    # if self.debug:
                    #     print (str(cmd) + ": " + str(ret))

                    #update info field
                    ev['val'] = str(ret)
                
            # scheduler base time ~ 100 ms
            self.timer_ev.wait(0.1)
                
            self.count +=1
        except Exception:
            pass

    def __receive(self):
        """Receive UDP return string
        """
        try:
            data, _ = self.sock_cmd.recvfrom(2048)
            self.udp_cmd_ret = data.decode(encoding="utf-8")
            self.cmd_recv_ev.set()
        except Exception:
            pass

    def __state_receive(self):
        """Receive UDP return string
        """
        data, _ = self.sock_state.recvfrom(512)
        val = data.decode(encoding="utf-8").rstrip()

        # data split
        self.state_value = val.replace(';',':').split(':')

    def set_image_size(self, image_size=(960,720)):
        """Set size of the aptured image

        Args:
            image_size (tuple, optional): Retun image size. Defaults to (960,720).
        """
        self.image_size = image_size

    def get_frame(self):
        """get frame from queue

        Returns:
            (w,h,3) array: 920x720 RGB frame
        """
        #return self.frame
        return self.q.get()

    def stop_communication(self):
        """Close commnucation threads
        """
        self.receiverThread.stop()
        self.stateThread.stop()
        self.eventThread.stop()

        # close the socket too
        self.sock_cmd.close()

    def start_communication(self):
        """Start low level communication
        """
        # start communication / listens to UDP
        if self.receiverThread.is_alive() is not True: self.receiverThread.start()
        if self.eventThread.is_alive() is not True:  self.eventThread.start()
        if self.stateThread.is_alive() is not True:  self.stateThread.start()
        

    def stop_video(self):
        """Stop video stream
        """
        self.send_cmd('streamoff')
        self.videoThread.stop()
    
    def wait_till_connected(self):
        """
        Blocking command to wait till Tello is available
        Use this command at program startup, to determin connection status
        """
        self.receiverThread.start()

        while True:
            try:
                ret = self.send_cmd_return('command')
                
                # force tello to 'DEBUG' mode
                if self.debug== True: ret = "OK"

            except Exception:
                exit()
            if str(ret) != 'None':
                break

    def send_cmd_return(self,cmd):
        """Send a command to Tello over UDP, wait for the return value

        Args:
            cmd (str): See Tello SDK for walid commands

        Returns:
            [str]: UPD aswer to the emmited command, see Tello SDK for valid answers
        """
        # send cmd over UDP
        self.udp_cmd_ret = None
        cmd = cmd.encode(encoding="utf-8")
        _ = self.sock_cmd.sendto(cmd, self.telloaddr)

        # wait for ans answer over UDP
        self.cmd_recv_ev.wait(0.3)
 
        # prepare for next received message
        self.cmd_recv_ev.clear()
        
        return self.udp_cmd_ret
    
    def send_cmd(self,cmd):
        """Send a command to Tello over UDP, do not wait for the return value

        Args:
            cmd (str): See Tello SDK for walid commands

        Returns:
            [str]: UPD aswer to the emmited command, see Tello SDK for valid answers
        """
        # send cmd over UDP
        cmd = cmd.encode(encoding="utf-8")
        _ = self.sock_cmd.sendto(cmd, self.telloaddr)

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int,
                        yaw_velocity: int):
        """Send RC control via four channels. Command is sent every self.TIME_BTW_RC_CONTROL_COMMANDS seconds.
        Arguments:
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
    
    def takeoff(self: object) -> None:
        """
        Decola o drone Tello.
        """
        self.send_cmd("takeoff")
        time.sleep(4)
        self.send_rc_control(0, 0, 0, 0)
    
    def land(self: object) -> None:
        """
        Pousa o drone Tello.
        """
        while float(self.get_state_field('tof')) >= 30:
            self.send_rc_control(0, 0, -70, 0)
        self.send_rc_control(0, 0, 0, 0)
        self.send_cmd("land")
        #time.sleep(4)
        
    def start_tello(self: object) -> None:
        '''
        Inicializa o drone tello. Conecta, testa se é possível voar, habilita a transmissão por vídeo.
        '''
        if not self.receiverThread.is_alive(): # Se a thread de recebimento não estiver ativa
            self.wait_till_connected()
            self.start_communication()
            self.start_video()
            print("Conectei ao Tello")
            print("Abrindo vídeo do Tello")

        if not self.simulate:
            self.takeoff()

    def end_tello(self: object) -> None:
        '''
        Finaliza o drone Tello. Pousa se possivel, encerra o video e a comunicacao.
        '''
        self.stop_video()
        if not self.simulate:
            self.land()
        self.stop_communication()
        print("Finalizei")

    def get_state_field(self, key: str) -> str:
        """Get a specific sate field by name.
        Internal method, you normally wouldn't call this yourself.
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
        """Get current battery percentage
        Returns:
            int: 0-100
        """
        return self.get_state_field('bat')

    def start_video(self: object) -> None:
        '''
        Inicia a transmissão de vídeo do Tello.
        '''
        self.send_cmd('streamon')
        if self.videoThread.is_alive() is False:  self.videoThread.start()
        
    def calc_fps(self: object) -> int:
        """Calcula o FPS do video
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
    
    def readQueue(self: object) -> None:
        """Lê a fila de comandos e envia-os ao drone Tello.
        Args:
            tello: Objeto TelloZune
        """
        while not self.stop_receiving.is_set():
            command = None
            with self.queue_lock:   # Evita que a lista seja alterada enquanto é lida
                if self.command_queue:
                    command = self.command_queue.pop(0)
            if command:        # Se houver comando na fila
                response = self.send_cmd_return(command)
                time.sleep(3)
                print(f"{command}, {response}")
            time.sleep(3)

    def get_info(self: object) -> tuple:
        """Retorna informações do drone.
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
        """Escreve informações no frame atual, posicionadas corretamente.
        
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
