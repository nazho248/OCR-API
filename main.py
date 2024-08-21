import zipfile

from flask import Flask, request, jsonify, redirect, render_template, url_for
import requests
import os
import io
from PIL import Image
from pdf2image import convert_from_path
import base64
import textwrap
import base64Handler
from base64Handler import safe_b64decode
from various_handlers import verify_content, jsonify_rta, verify_key, delete_file
#from Image_Ocr import image_ocr, image_decompressor, multipleImages
#import time
# Inicializar el lector de OCR con el idioma deseado.
baseurl = "https://instagram-videos.vercel.app/api/video"

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify_rta("Corriendo bien", 200, {})

@app.route('/', methods=['GET', 'POST'])
def index():
    processed_text = ''
    char_count = 0
    if request.method == 'POST':
        text = request.form['text_input']
        processed_text, char_count = process_text(text)
    return render_template('index.html', processed_text=processed_text, char_count=char_count)


def process_text(text):
    # Limitar el texto a 600 caracteres
    text = text[:600]

    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + len(current_line) <= 60:
            current_line.append(word)
            current_length += len(word)
        else:
            if current_line:
                spaces_needed = 60 - current_length
                spaces_between = spaces_needed // max(1, len(current_line) - 1)
                extra_spaces = spaces_needed % max(1, len(current_line) - 1)

                justified_line = ""
                for i, w in enumerate(current_line):
                    justified_line += w
                    if i < len(current_line) - 1:
                        justified_line += " " * spaces_between
                        if i < extra_spaces:
                            justified_line += " "

                lines.append(justified_line)

            current_line = [word]
            current_length = len(word)

    # Añadir la última línea sin justificar
    if current_line:
        lines.append(" ".join(current_line).ljust(60))

    processed_text = "".join(lines)
    char_count = len(processed_text)

    return processed_text, char_count


@app.route("/instagram")
def instagram():
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


@app.route("/convert", methods=['POST'])
def convert():
    print("<------------------------------CONVERT INICIO------------------------------>")
    # Convierte un PDF en imagenes PNG y las entrega en un ZIP
    # obtengo el body de la petición
    data = request.json

    #verifico la clave secreta
    if auth := verify_key(key=request.headers.get('Authorization')):
        return auth

    # verifico que el guid este presente en la solicitud
    if validation := verify_content(request.headers.get('GUID'), 'GUID'):
        return validation

    # verifico que el archivo este presente en la solicitud
    if data['archivo'] == '':
        return jsonify_rta("No se recibió el archivo", 400, {})

    #verifico que el filetype sea pdf y esté presente en la solicitud
    if data['filetype'] not in ['.pdf']:
        return jsonify({"error": "El archivo no es soportado"}), 400

    base64_file = data['archivo']
    filetype = data['filetype']
    guid = request.headers.get('GUID')
    print("Se inició el proceso para : " + guid)
    archivo, error = safe_b64decode(base64_file)
    if error:
        return jsonify_rta("Error al decodificar el archivo inicial", 500, {'error': error})

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

    #crear un zip con las imagenes
    with zipfile.ZipFile(f'outputs/{guid}.zip', 'w') as zip:
        for file in output_images:
            zip.write(file, os.path.basename(file))

    #convertir el zip a base64
    zip_content = base64Handler.convert_to_base64(f'outputs/{guid}.zip')

    #eliminar archivos
    delete_file(ruta_archivo_pdf)
    for file in output_images:
        delete_file(file)

    #size in mb of zip
    zip_size = os.path.getsize(f'outputs/{guid}.zip') / 1024 / 1024
    #borrar zip
    delete_file(f'outputs/{guid}.zip')

    print("Se ha procesado el documento con " + str(len(output_images)) + " paginas, con GUID: " + guid + " y tamaño del zip: " + str(zip_size) + " MB")

    return jsonify_rta("Se ha procesado el documento con " + str(len(output_images)) + " paginas", 200, {'pages': zip_content})


@app.route("/convertjpg", methods=['POST'])
def converttojpg():
    print("<------------------------------CONVERT JPG INICIO------------------------------>")
    # Convierte un PDF en imagenes PNG y las entrega en un ZIP
    # obtengo el body de la petición
    data = request.json

    #verifico la clave secreta
    if auth := verify_key(key=request.headers.get('Authorization')):
        return auth

    # verifico que el guid este presente en la solicitud
    if validation := verify_content(request.headers.get('GUID'), 'GUID'):
        return validation

    # verifico que el archivo este presente en la solicitud
    if data['archivo'] == '':
        return jsonify_rta("No se recibió el archivo", 400, {})

    #verifico que el filetype sea pdf y esté presente en la solicitud
    if data['filetype'] not in ['.pdf']:
        return jsonify({"error": "El archivo no es soportado"}), 400

    #ver si existe quality, si no existe se asigna a 90
    qualityimage = 95
    if 'quality' in data:
        qualityimage = data['quality']


    base64_file = data['archivo']
    filetype = data['filetype']
    guid = request.headers.get('GUID')
    print("Se inició el proceso para : " + guid)
    archivo, error = safe_b64decode(base64_file)
    if error:
        return jsonify_rta("Error al decodificar el archivo inicial", 500, {'error': error})

    # decodifico el base64 en pdf
    ruta_archivo_pdf = 'input_files/' + guid + '.pdf'

    # Guardar los datos binarios en un archivo
    with open(ruta_archivo_pdf, 'wb') as file:
        file.write(archivo)

    imagenes = convert_from_path(ruta_archivo_pdf)

    # Crear un archivo ZIP en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
        for i, imagen in enumerate(imagenes):
            # Resize image if needed (adjust dimensions as required)
            imagen = imagen.resize((1000, int(1000 * imagen.height / imagen.width)))

            # Determine if the image has transparency
            if imagen.mode in ('RGBA', 'LA') or (imagen.mode == 'P' and 'transparency' in imagen.info):
                # For images with transparency, use optimized PNG
                img_buffer = io.BytesIO()
                imagen.save(img_buffer, format='PNG', optimize=True, quality=qualityimage)
                img_buffer.seek(0)
                zip_file.writestr(f'page-{i+1}.png', img_buffer.getvalue())
            else:
                # For images without transparency, use JPEG
                img_buffer = io.BytesIO()
                imagen = imagen.convert('RGB')
                imagen.save(img_buffer, format='JPEG', optimize=True, quality=qualityimage)
                img_buffer.seek(0)
                zip_file.writestr(f'page-{i+1}.jpg', img_buffer.getvalue())

    # Get the ZIP content as bytes
    zip_content = zip_buffer.getvalue()

    # Convert ZIP content to base64
    zip_base64 = base64.b64encode(zip_content).decode('utf-8')

    # Calculate ZIP size in MB
    zip_size = len(zip_content) / (1024 * 1024)

    print(f"Se ha procesado el documento con {len(imagenes)} paginas, con GUID: {guid} y tamaño del zip: {zip_size:.2f} MB")
    return jsonify_rta(f"Se ha procesado el documento con {len(imagenes)} paginas", 200, {'pages': zip_base64})



'''
@app.route("/ocr", methods=['POST'])
def ocr():
    print("<------------------------------OCR INICIO------------------------------>")
    # obtengo el body de la petición
    data = request.json
    # asignar return_images a False por defecto, en caso de que no se especifique en el body
    return_images = False
    #si return images es "True"
    if 'return_images' in data and data['return_images'].lower() == 'true':
        return_images = True

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

    if data['archivo'] == '':
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
        return jsonify_rta("Error al decodificar el archivo inicial", 500, {'error': error})

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

        start = time.time()
        result, error = multipleImages(output_images,guid,return_images)
        end = time.time()
        print(f"OCR terminado en {end - start} seconds")
        if error:
            return jsonify_rta("Error al procesar el pdf: ", 500, {'error': error})
        #eliminar pdf
        delete_file(ruta_archivo_pdf)
        return jsonify_rta("Se han procesado: " + str(len(output_images)) + " paginas", 200, {'pages': result})


    elif filetype == '.png':
        input, output, error=image_decompressor(archivo,guid)
        if error:
            return jsonify_rta("Error al decodificar el archivo.", 500, {'error': error})
        ocr_result, error = image_ocr(input, output, return_images)
        if error:
            return jsonify_rta("Error al procesar la imagen", 500, {'error': error})
        return jsonify(ocr_result)
    else:
        return jsonify_rta('Formato de archivo no admitido', 400, {})
'''

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Usa el puerto proporcionado por Cloud Run o 5000 en local
    app.run(host="0.0.0.0", port=port, debug=True)
