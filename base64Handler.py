import base64
import cv2

def convert_image_to_base64(image_path):
    # Leer la imagen desde el archivo
    image = cv2.imread(image_path)
    if image is None:
        return None

    # Codificar la imagen como PNG
    _, buffer = cv2.imencode('.png', image)

    # Convertir los bytes a Base64 y luego a cadena para JSON
    image_base64 = base64.b64encode(buffer).decode('utf-8')

    return image_base64


def safe_b64decode(input_string):
    # Normalizar y limpiar la cadena de entrada
    input_string = input_string.strip()
    # Reemplazar caracteres no base64 que podrían ser añadidos en algunos casos
    #input_string = input_string.replace(" ", "+")
    try:
        return base64.b64decode(input_string), None
    except ValueError as e:
        print("Error de decodificación Base64:", e)
        return None, str(e)


#convierte el archivo del path a base64
def convert_to_base64(path):
    with open(path, 'rb') as file:
        data = file.read()
        return base64.b64encode(data).decode('utf-8')
