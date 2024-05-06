import os
import easyocr
from base64Handler import  convert_image_to_base64
import cv2
import numpy as np

from various_handlers import delete_file

reader = easyocr.Reader(['es'])  # Asumiendo que el texto es en español


def multipleImages(array_images_path,guid):
    '''
    Funcion para decodificar multiples imagenes y devolver un array con las respuestas
    :param array_images: arreglo con el nombre de las imagenes
    :param guid: GUID electrónico para guardar la imagen y no generar conflictos
    :return: respuesta del ocr con cada imagen definiendo cada pagina
    '''
    array_response = {}
    errors = {}
    for idx, image_path in enumerate(array_images_path):
        json, error = image_ocr(image_path, f'outputs/{guid}-{idx}.png', True)
        if error:
            errors[idx] = error
            continue  # Continúa con la siguiente imagen en caso de error
        array_response[idx] = json
    return array_response, error

def image_decompressor(imageB64, guid):
    '''
    Funcion para decodificar una imagen
    :param imageB64: Imagen codificada en base64
    :param guid: GUID único para guardar la imagen y no generar conflictos
    :return:  retorna el input path y output path para alimentar a image_ocr
    '''

    if imageB64 is None:
        return None,None,'Invalid base64 data'

    # Convertir la cadena base64 en un array de numpy para decodificar
    nparr = np.frombuffer(imageB64, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return None, None,'Failed to load image'

    # Construir las rutas necesarias para guardar la imagen
    base_dir = os.path.abspath(os.path.dirname(__file__))
    images_dir = os.path.normpath(os.path.join(base_dir, 'input_files'))
    image_path = os.path.normpath(os.path.join(images_dir, guid + '.png'))

    outputs_path = os.path.normpath(os.path.join(base_dir, 'outputs'))
    output_path = os.path.normpath(os.path.join(outputs_path, guid + '.png'))
    # Intentar guardar la imagen en el directorio deseado
    try:
        save_success = cv2.imwrite(image_path, img)
        if not save_success:
            raise IOError("No se pudo guardar la imagen")
    except Exception as e:
        return None,None,'Error saving image: ' + str(e)

    # Comprobar si el archivo se ha guardado correctamente
    if not os.path.isfile(image_path):
        return None, 'File not found'

    return image_path, output_path, None


def image_ocr(image_path, output_path, multiple=False):
    '''
    Funcion para realizar OCR en una imagen y devolver el resultado
    :param image_path: path de la imagen de entrada
    :param output_path: path para la imagen de salida
    :param multiple: en caso de llamarlo desde multipleImages, devuelve una u otra respuesta (True | False)
    :return: respuesta del ocr en json
    '''
    # paso la imagen en base64 recibida a archivo

    # Comprobar si el archivo existe para evitar errores.
    if not os.path.isfile(image_path):
        return None,'File not found'

    # Cargar la imagen con OpenCV
    img = cv2.imread(image_path)
    if img is None:
        return None,'Failed to load image'

    # Realizar OCR en la imagen.
    try:
        results = reader.readtext(image_path)

        # Dibujar rectángulos alrededor del texto detectado
        for (bbox, text, prob) in results:
            (top_left, top_right, bottom_right, bottom_left) = bbox
            top_left = tuple(map(int, top_left))
            bottom_right = tuple(map(int, bottom_right))

            # Dibujar el rectángulo
            cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)

        # Guardar la imagen con anotaciones
        cv2.imwrite(output_path, img)

        output_image64 = convert_image_to_base64(output_path)

        # Extraer tanto los textos como sus respectivos valores de confianza de los resultados.
        texts_with_confidence = [{'text': result[1],
                                  'confidence': result[2],
                                  } for result in results]

        extracted_texts = ' '.join([result['text'] for result in texts_with_confidence])
        confidence_mean = np.mean([result['confidence'] for result in texts_with_confidence])

        delete_file(output_path)
        delete_file(image_path)

        # texts = [result[1] for result in results]

        if multiple:
            return  {
                "texto_completo": extracted_texts,
                "textos": texts_with_confidence,
                "imagen_output": output_image64,
                "promedio_confianza": confidence_mean
            }, None
        else:
            return {
                "message": "Recibido",
                "data": {
                    "pages":{
                    "0":{
                        "texto_completo": extracted_texts,
                        "textos": texts_with_confidence,
                        "imagen_output": output_image64,
                        "promedio_confianza": confidence_mean
                         }
                    }
                },
            }, None

    except Exception as e:
        return  str(e)
