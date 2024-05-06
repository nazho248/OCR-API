from flask import Flask, request, jsonify, redirect
import requests
import os
from pdf2image import convert_from_path
from base64Handler import safe_b64decode
from various_handlers import verify_content, jsonify_rta, verify_key, delete_file
from Image_Ocr import image_ocr, image_decompressor, multipleImages

# Inicializar el lector de OCR con el idioma deseado.
baseurl = "https://instagram-videos.vercel.app/api/video"

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify_rta("Corriendo bien", 200, {})


@app.route("/")
def index():
    # obtiene el parámetro url del enlace
    url_value = request.args.get('url')
    # validar que no este vacío el url
    if validation := verify_content(url_value, 'url'):
        return validation

    # if(auth := verify_key(key = request.headers.get('Authorization'))):
    #    return auth
    params = {'postUrl': url_value}  # configurar parametros para hacer la consulta
    response = requests.get(baseurl, params=params)  # enviar peticion
    # Verificar la respuesta de la API
    if response.status_code == 200:
        data = response.json()  # Convertimos la respuesta a JSON aquí
        if request.args.get('d') is not None:  # si tenemos el query d, redireccionamos directamente al video
            return redirect(data['data']['videoUrl'])  # Redireccionamos usando el URL extraído del JSON
        else:
            # Si no tenemos el d, devolvemos el JSON
            return jsonify(data)
    else:
        data = response.json()
        # en caso de error, devolvemos el JSON con el error
        return jsonify({
            "message": "The video wasn't found or the " + data['message']
        }), response.status_code


@app.route("/ocr", methods=['POST'])
def ocr():
    # obtengo el body de la petición
    data = request.json

    # <editor-fold desc="Validaciones">
    # --------------------------------- VALIDACIONES ----------------------
    #    # Verificar la clave secreta
    if auth := verify_key(key=request.headers.get('Authorization')):
        return auth

    # Verificar la presencia de un GUID en la solicitud
    if validation := verify_content(request.headers.get('GUID'), 'GUID'):
        return validation

    # return jsonify(dict(request.headers))
    if validation := verify_content(data, 'Body/data'):
        return validation

    if 'archivo' not in data:
        return jsonify_rta("No se recibió el archivo", 400, {})

    if 'archivo_nombre' not in data:
        return jsonify_rta("No se recibió el nombre del archivo", 400, {})

    if 'filetype' not in data:
        return jsonify_rta("No se recibió el tipo de archivo", 400, {})

    # si el filetype de data es pdf o png
    if data['filetype'] not in ['.pdf', '.png']:
        return jsonify({"error": "El archivo no es soportado"}), 400
    # --------------------------------- FIN VALIDACIONES ----------------------
    # </editor-fold>

    base64_file = data['archivo']
    filetype = data['filetype']
    guid = request.headers.get('GUID')
    archivo, error = safe_b64decode(base64_file)
    if error:
        return jsonify_rta("Error al decodificar el archivo", 500, {'error': error})

    if filetype == '.pdf':
        # decodifico el base64 en pdf
        ruta_archivo_pdf = 'input_files/' + guid + '.pdf'

        # Guardar los datos binarios en un archivo
        with open(ruta_archivo_pdf, 'wb') as file:
            file.write(archivo)

        # Convertir el PDF guardado en imágenes PNG
        imagenes = convert_from_path(ruta_archivo_pdf)

        # Guardar las imágenes en archivos PNG y guardarlos en un array
        output_images = []
        for i, imagen in enumerate(imagenes):
            ruta_imagen_png = f'input_files/p{guid}-{i + 1}.png'
            imagen.save(ruta_imagen_png, 'PNG')
            output_images.append(ruta_imagen_png)

        result, error = multipleImages(output_images,guid)
        if error:
            return jsonify_rta("Error al procesar el pdf: ", 500, {'error': error})
        #eliminar pdf
        delete_file(ruta_archivo_pdf)
        return jsonify_rta("Se han procesado: " + str(len(output_images)) + " paginas", 200, {'pages': result})


    elif filetype == '.png':
        input, output, error=image_decompressor(archivo,guid)
        if error:
            return jsonify_rta("Error al decodificar el archivo", 500, {'error': error})
        ocr_result, error = image_ocr(input, output)
        if error:
            return jsonify_rta("Error al procesar la imagen", 500, {'error': error})
        return jsonify(ocr_result)
    else:
        return jsonify_rta('Formato de archivo no admitido', 400, {})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Usa el puerto proporcionado por Cloud Run o 5000 en local
    app.run(host="0.0.0.0", port=port, debug=True)
