from djitellopy import Tello
import cv2
import time
import base_detect_yolo

'''
Class TelloZune
-----------------------------------------------
simulate                   # se passado ao declarar como True, inicia o modo simulacao, sem voar. Padrao = False
-----------------------------------------------
start_tello()               # inicializa o tello
end_tello()                 # finaliza o tello
start_video()               # inicia a transmissao de video do tello
end_video()                 # finaliza a transmissao de video do tello
-----------------------------------------------
'''

FONT = cv2.FONT_HERSHEY_SIMPLEX

# Exception para quando a bateria do Tello for menor que 20% nao executar o resto dos comandos.
class BatteryError(Exception):
    pass

def battery_error(tello_battery: int):
    if tello_battery <= 20:
        raise BatteryError("Bateria menor que 20%, operação cancelada.")

class TelloZune():
    '''
    Drone tello
    '''
    def __init__(self, simulate = False):
        self.num_frames = 0
        self.start_time = time.time()
        self.fps = 0
        self.values_detect = []
        self.simulate = simulate
        
    def start_tello(self):
        '''
        Inicializa o drone tello. Conecta, testa se é possivel voar, habilita a transmissao por video.
        '''
        self.tello = Tello()
        self.tello.connect()
        battery_error(self.tello.get_battery())
        self.tello.streamon()
        print("conectei teste")
        if not self.simulate:
            self.tello.takeoff()
            self.tello.send_rc_control(0, 0, 0, 0)
    
    def end_tello(self):
        '''
        Finaliza o drone tello.
        '''
        if not self.simulate:
            self.tello.send_rc_control(0, 0, 0, 0)
            self.tello.land()
        print("finalizei")
    
    def start_video(self, yolo_detect_base):
        '''
        Inicia a transmissao de video do tello. Recebe como argumento: yolo_detect_base (True: Deteccao de base utilizando yolo, False: Nao detecta).
        Pega cada frame da transmissao com tello_frame, converte a cor de RGB para BGR, muda o tamanho do frame para 544 x 306.
        Funcao de calcular frames ja inclusa.
        '''
        if not isinstance(yolo_detect_base, bool):
            raise ValueError("Arg (yolo_detect_base) deve ser True ou False")
        
        self.tello_frame = self.tello.get_frame_read().frame
        self.tello_frame = cv2.cvtColor(self.tello_frame, cv2.COLOR_RGB2BGR)
        self.tello_frame = cv2.resize(self.tello_frame, (544, 306))

        if yolo_detect_base:
            self.values_detect = base_detect_yolo.baseDetect(self.tello_frame)
        self.calc_fps()
        cv2.imshow("video", self.tello_frame)
            
    def end_video(self):
        '''
        Finaiza a transmissao de video do Tello. Desabilita a transmissao de video, fecha todas as janelas cv2.
        '''
        self.tello.streamoff()
        cv2.destroyAllWindows()
    
    def calc_fps(self):
        '''
        Calcula a quantidade de frames por segundo na transmissao e coloca essa quantidade na janela criada cv2.
        '''
        self.num_frames += 1
        self.elapsed_time = time.time() - self.start_time
        if self.elapsed_time >= 1:
            self.fps = int(self.num_frames / self.elapsed_time)
            self.num_frames = 0
            self.start_time = time.time()
        cv2.putText(self.tello_frame, f"FPS: {self.fps}", (30, 30), FONT, 1, (0, 255, 0), 2)