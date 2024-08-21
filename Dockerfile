# Usar una imagen base de Python
FROM python:3.8-slim

# Instalar las dependencias del sistema
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    git \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de requisitos y actualizar pip
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar el contenido del proyecto al directorio de trabajo
COPY . .

# Exponer el puerto 5000
EXPOSE 5000

# Configurar el punto de entrada para ejecutar el servidor con waitress
ENTRYPOINT ["python"]

# Cambiar a usar waitress en lugar de gunicorn
CMD ["wsgi.py"]
