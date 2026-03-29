import cv2

from tello_zune.tello_zune import TelloZune

tello = TelloZune() # Cria objeto da classe TelloZune
tello.start_tello() # Inicia a comunicação com o drone
tello.add_periodic_event("forward 50 e cw 90", 100, "Vigilância", 10) # Adiciona evento periódico

try:
    while True:
        # Captura
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
    tello.end_tello()
    cv2.destroyAllWindows()
