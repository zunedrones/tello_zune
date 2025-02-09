import cv2
from tello_zune import TelloZune
import modules.tello_control as tello_control
import time

# Inicialização
#cap = cv2.VideoCapture(0) # Captura de vídeo da webcam
tello = TelloZune() # Cria objeto da classe TelloZune
tello.start_tello() # Inicia a comunicação com o drone
tello.simulate=True

try:
    while True:
        # Captura
        #ret, frame = cap.read() # Captura de vídeo da webcam
        frame = tello.get_frame()
        cv2.putText(frame, f"FPS: {tello.calc_fps()}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        cv2.putText(frame, f"Bat: {tello.get_battery()}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        #frame = cv2.resize(frame, (960, 720)) # Necessário caso esteja usando a webcam

        # Tratamento
        frame = tello_control.moves(tello, frame)

        # Exibição
        cv2.imshow('QR Code', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            tello.stop_receiving.set()
            tello_control.stop_searching.set()
            break
finally:
    # Finalização
    #cap.release()
    tello.end_tello()
    cv2.destroyAllWindows()
    tello.moves_thread.join() # Aguarda a thread de movimentos encerrar
