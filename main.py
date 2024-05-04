from flask import Flask, request, jsonify, send_file
import easyocr
import os
import cv2
import numpy as np
import base64
from pdf2image import convert_from_path

# Inicializar el lector de OCR con el idioma deseado.
reader = easyocr.Reader(['es'])  # Asumiendo que el texto es en español

app = Flask(__name__)
SECRET_KEY = 'OGLIT44458OCR32'


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
    input_string = input_string.replace(" ", "+")
    try:
        return base64.b64decode(input_string)
    except ValueError as e:
        print("Error de decodificación Base64:", e)
        return None

def delete_file(file_path):
    # Comprobar si el archivo existe
    if os.path.exists(file_path):
        # Eliminar el archivo
        os.remove(file_path)
        print(f"Archivo {file_path} eliminado con éxito.")
    else:
        print(f"El archivo {file_path} no existe.")


@app.route("/health")
def health():
    return jsonify({
        "Status": "Server corriendo bien :)"
    }), 200


@app.route("/")
def index():
    return jsonify({
        "message":"Hola mundo"
    }),200


@app.route("/ocr", methods=['POST'])
def ocr():
    print("peticion recibida)")

    #    # Verificar la clave secreta
    key = request.headers.get('Authorization')
    # --------------------------------- VALIDACIONES ----------------------
    if not key or key != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

        # Verificar la presencia de un GUID en la solicitud
    guid = request.headers.get('GUID')
    if not guid:
        return jsonify({"error": "GUID not provided"}), 400

    # obtengo el body de la peticion
    data = request.json
    # return jsonify(dict(request.headers))

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if 'archivo' not in data:
        return jsonify({"error": "No se envio ningun archivo"}), 400

    if 'archivo_nombre' not in data:
        return jsonify({"error": "No se envio el nombre del documento"}), 400

    base64_file = data['archivo']

    # verificar que el archivo
    filetype = data['filetype']
    print(filetype)

    match filetype:
        case '.pdf':
            # decodifico el base64 en pdf
            archivo = base64.b64decode(base64_file)
            ruta_archivo_pdf = 'input_files/' + guid + '.pdf'

            # Guardar los datos binarios en un archivo
            with open(ruta_archivo_pdf, 'wb') as file:
                file.write(archivo)

            # Convertir el PDF guardado en imágenes PNG
            imagenes = convert_from_path(ruta_archivo_pdf)

            # Guardar las imágenes en archivos PNG
            output_images = []
            for i, imagen in enumerate(imagenes):
                ruta_imagen_png = f'outputs/p{guid}{i + 1}.png'
                imagen.save(ruta_imagen_png, 'PNG')
                output_images.append(ruta_imagen_png)

            return jsonify({'message': 'Correcto', 'images': output_images}), 200





        case '.png':
            return jsonify({'mesage': 'No implementado'})
        case _:
            return jsonify({'mesage': 'Archivo no soportado'}), 400


    # paso la imagen en base64 recibida a archivo
    base64_file = data['archivo']

    image_data = safe_b64decode(base64_file)

    if image_data is None:
        return jsonify({'message': 'Invalid base64 data'}), 400

    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Definir la ruta de la imagen
    # image_path = 'D:/Proyectos/Oglit/OCR API/input_files/test_image.png'
    base_dir = os.path.abspath(os.path.dirname(__file__))
    images_dir = os.path.normpath(os.path.join(base_dir, 'input_files'))
    image_path = os.path.normpath(os.path.join(images_dir, guid + '.png'))

    outputs_path = os.path.normpath(os.path.join(base_dir, 'outputs'))
    output_path = os.path.normpath(os.path.join(outputs_path, guid + '.png'))

    if img is None:
        return jsonify({'message': 'Failed to load image'}), 500

    try:
        save_success = cv2.imwrite(image_path, img)
        if not save_success:
            raise IOError("No se pudo guardar la imagen")
    except Exception as e:
        return jsonify({'message': str(e)}), 500

    # para ocr de imagenes dentro del propio directorio
    '''base_dir = os.path.dirname(os.path.abspath(__file__))  # Obtiene el directorio donde está el script
    image_path = os.path.join(base_dir, 'text.png')  # Construye la ruta hacia text.png
    '''

    # Comprobar si el archivo existe para evitar errores.
    if not os.path.isfile(image_path):
        return jsonify({'message': 'File not found'}), 500

    # Cargar la imagen con OpenCV
    img = cv2.imread(image_path)
    if img is None:
        return jsonify({'message': 'Failed to load image'}), 500

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

        delete_file(output_path)
        delete_file(image_path)

        # texts = [result[1] for result in results]
        return {
            "message": "Recibido",
            "data":{
            "texto_completo":extracted_texts,
            "textos": texts_with_confidence,
            "imagen_output": output_image64,
        },

        }, 200


    except Exception as e:
        return jsonify({'message': str(e)}), 500

    except Exception as e:
        return jsonify({'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Usa el puerto proporcionado por Cloud Run o 5000 en local
    app.run(host="0.0.0.0", port=port, debug=True)
