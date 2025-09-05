# Usa una imagen base de Python
FROM python:3.11.9-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo requirements.txt y instala las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente del servicio
COPY . .

# Expone el puerto en el que el servicio estará disponible
EXPOSE 5003

# Comando para ejecutar el servicio
CMD ["python", "app.py"]
