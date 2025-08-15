import cv2
import numpy as np

from tello_zune import TelloZune

FONT = cv2.FONT_HERSHEY_SIMPLEX
COLOR = (0, 255, 0)
WIDTH, HEIGHT = 960, 720
ORG_FPS = (10, 30)
ORG_BAT = (WIDTH - 200, HEIGHT - 10)

def write_info(frame: np.ndarray, tello: TelloZune, info_flags: dict) -> None:
    """
    Desenha as informações do drone no frame de vídeo.

    Args:
        frame: O frame do vídeo onde as informações serão desenhadas.
        tello: A instância do objeto TelloZune para obter os dados.
        info_flags: Um dicionário indicando quais informações desenhar (ex: {'fps': True, 'bat': True})
    """
    if info_flags.get('fps'):
        valor_fps = tello.calc_fps()
        cv2.putText(frame, f"FPS: {valor_fps}", ORG_FPS, FONT, 1, COLOR, 2)

    bat_val, h_val, temp_val, pres_val, time_val = tello.get_info()

    if info_flags.get('bat'):
        cv2.putText(frame, f"Battery: {bat_val}%", ORG_BAT, FONT, 1, COLOR, 2)
    if info_flags.get('height'):
        cv2.putText(frame, f"Height: {h_val} cm", (ORG_BAT[0], ORG_BAT[1] - 30), FONT, 1, COLOR, 2)
    if info_flags.get('temperature'):
        cv2.putText(frame, f"Temperature: {temp_val} C", (ORG_BAT[0], ORG_BAT[1] - 60), FONT, 1, COLOR, 2)
    if info_flags.get('pressure'):
        cv2.putText(frame, f"Pressure: {pres_val} hPa", (ORG_BAT[0], ORG_BAT[1] - 90), FONT, 1, COLOR, 2)
    if info_flags.get('time'):
        cv2.putText(frame, f"Time: {time_val} s", (ORG_BAT[0], ORG_BAT[1] - 120), FONT, 1, COLOR, 2)
