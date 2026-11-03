import cv2
import numpy as np
from tello_zune import TelloZune

import modules.tello_control as tello_control

# Inicialização
tello = TelloZune(text_input=True) # Cria objeto da classe TelloZune
tello.start_tello() # Inicia a comunicação com o drone

def write_info(frame: np.ndarray, tello: TelloZune) -> None:
    """Escreve FPS e telemetria no canto superior esquerdo do frame."""
    bat, height, temph, baro, time_elapsed = tello.get_info()
    lines = [
        f"FPS: {tello.calc_fps()}",
        f"Bat: {bat}%",
        f"Height: {height}cm",
        f"Max. Temp.: {temph}C",
        f"Baro: {baro}cm",
        f"Time: {time_elapsed}s",
    ]
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (10, 255, 0), 2)

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
            write_info(frame, tello)
            cv2.imshow('QR Code', frame)
        else:
            print("Erro: frame não é um array de imagem válido.")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Finalização
    tello.end_tello()
    cv2.destroyAllWindows()
