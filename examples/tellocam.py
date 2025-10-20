import cv2
from tello_zune import TelloZune

tello = TelloZune()
tello.start_tello()

while True:
    img = tello.get_frame()
    battery, height, temperature, pressure, time = tello.get_info()
    cv2.putText(img, f'Battery: {battery}%', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(img, f'Height: {height}cm', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(img, f'Temperature: {temperature}C', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(img, f'Pressure: {pressure}Pa', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(img, f'Time: {time}s', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow('Tello', img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

tello.end_tello()
cv2.destroyAllWindows()
