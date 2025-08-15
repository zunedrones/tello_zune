import cv2
import numpy as np
from tello_zune import TelloZune

import modules.tello_control as tello_control
from ui.display_utils import write_info

# Inicialização
tello = TelloZune(simulate=True, text_input=True) # Cria objeto da classe TelloZune
tello.start_tello() # Inicia a comunicação com o drone

stats = {
    "fps": True,
    "battery": True,
    "height": True,
    "temperature": True,
    "pressure": True,
    "time_elapsed": True
}
try:
    while True:
        # Captura
        #ret, frame = cap.read() # Captura de vídeo da webcam
        frame = tello.get_frame()
        frame = cv2.resize(frame, (960, 720))

        # Tratamento
        frame = tello_control.moves(tello, frame)

        # Exibição
        if isinstance(frame, np.ndarray):
            write_info(frame, tello, stats)
            cv2.imshow('QR Code', frame)
        else:
            print("Erro: frame não é um array de imagem válido.")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Finalização
    tello.end_tello()
    cv2.destroyAllWindows()