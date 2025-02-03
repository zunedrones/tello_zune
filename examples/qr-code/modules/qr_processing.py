from pyzbar.pyzbar import decode

x, y, w, h = 0, 0, 0, 0
qr_text = ''

def process(frame: object) -> list:
    '''
    Processa o frame para detectar QR codes.
    Args:
        frame: Frame de vídeo a ser processado para detecção de QR codes.
    Returns:
        frame: Frame processado após a detecção dos QR codes.
        x: Coordenada x do canto superior esquerdo do QR code.
        y: Coordenada y do canto superior esquerdo do QR code.
        w: Largura do QR code.
        h: Altura do QR code.
        len(decoded_objects): Número de QR codes detectados.
        qr_text: Texto decodificado do QR code.
    '''
    decoded_objects = decode(frame)
    global x, y, w, h, data, qr_text
    for obj in decoded_objects:
        (x, y, w, h) = obj.rect
        qr_text = obj.data.decode('utf-8')
    return [frame, x, y, x+w, y+h, len(decoded_objects), qr_text]

#cv2.namedWindow('QR Code', cv2.WINDOW_AUTOSIZE)