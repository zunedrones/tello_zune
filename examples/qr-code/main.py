import cv2
from tello_zune import TelloZune
import modules.tello_control as tello_control

# Inicialização
tello = TelloZune(simulate=True, text_input=True) # Cria objeto da classe TelloZune
tello.start_tello() # Inicia a comunicação com o drone

try:
    while True:
        # Captura
        #ret, frame = cap.read() # Captura de vídeo da webcam
        frame = tello.get_frame()
        frame = cv2.resize(frame, (960, 720))

        # Tratamento
        frame = tello_control.moves(tello, frame)
        tello.write_info(frame, True, True, True, True, True, True)

        # Exibição
        cv2.imshow('QR Code', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Finalização
    tello.end_tello()
    cv2.destroyAllWindows()