import cv2
from tello_zune import TelloZune
import modules.tello_control as tello_control
import time

# Inicialização
cap = cv2.VideoCapture(0) # Captura de vídeo da webcam
tello = TelloZune() # Cria objeto da classe TelloZune
tello.simulate = False # False: o drone decola; True: simula o voo
#tello.start_tello() # Inicia a comunicação com o drone
#tello_control.enable_search = True # Ativa a busca
timer = time.time()
bat, height, temph, pres, time_elapsed = tello.get_info()

try:
    while True:
        # Captura
        ret, frame = cap.read() # Captura de vídeo da webcam
        #frame = tello.get_frame()
        frame = cv2.resize(frame, (960, 720))

        # Tratamento
        frame = tello_control.moves(tello, frame)
        fps = tello.calc_fps()
        tello.write_info(frame, True, True, True, True, True, True)

        # Atualização
        if time.time() - timer > 10:
            timer = time.time()
            bat, height, temph, pres, time_elapsed = tello.get_info()

        # Exibição
        cv2.imshow('QR Code', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            tello.movesThread.stop()
            tello_control.stop_searching.set()
            break
finally:
    # Finalização
    cap.release()
    #tello.end_tello()
    cv2.destroyAllWindows()