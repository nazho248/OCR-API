from flask import jsonify

SECRET_KEY = 'OGLIT44458OCR32'

def verify_content(content, data_name):
    if not content or content == '':
        return jsonify({"error": f"{data_name} not provided"}), 400

def verify_key(key):
    if not key or key != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

def delete_file(file_path):
    # Comprobar si el archivo existe
    if os.path.exists(file_path):
        # Eliminar el archivo
        os.remove(file_path)
        print(f"Archivo {file_path} eliminado con éxito.")
    else:
        print(f"El archivo {file_path} no existe.")


def jsonify_rta(message, status, data):
    return jsonify({
        "message": message,
        "data": data,
    }), status
