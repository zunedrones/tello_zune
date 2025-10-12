import cv2
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.dirname(current_dir)

sys.path.insert(0, project_root)

from tello_zune.tello_zune import TelloZune


cap = cv2.VideoCapture(0) # Captura de vídeo da webcam
# tello.start_communication() # Este método deve ser chamado apenas se for usar a câmera do drone
tello = TelloZune() # Cria objeto da classe TelloZune
tello.start_tello() # Inicia a comunicação com o drone
tello.add_periodic_event("forward 50 e cw 90", 100, "Vigilância", 10) # Adiciona evento periódico

try:
    while True:
        # Captura
        # ret, frame = cap.read() # Captura de vídeo da webcam
        frame = tello.get_frame()

        # Tratamento
        bat, height, temph, pres, time_elapsed = tello.get_info()
        fps = tello.calc_fps()
        cv2.putText(frame, f"FPS: {fps}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        cv2.putText(frame, f"Bat: {bat}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        cv2.putText(frame, f"Height: {height}cm", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        cv2.putText(frame, f"Max. Temp.: {temph}C", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        cv2.putText(frame, f"Press.: {pres}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)
        cv2.putText(frame, f"TOF: {time_elapsed}s", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (10, 255, 0), 2)

        # Exibição
        cv2.imshow('QR Code', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Finalização
    #cap.release()
    tello.end_tello()
    cv2.destroyAllWindows()
