# ✨ CORRECCIÓN: Usar una imagen de Python más moderna (3.11) para compatibilidad
FROM python:3.11-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos primero para aprovechar el caché de Docker
COPY requirements.txt .

# Instalar las dependencias, incluyendo gunicorn
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copiar el resto del código de la aplicación al directorio de trabajo
COPY . .

# Exponer el puerto en el que la aplicación se ejecutará
EXPOSE 5000

# Comando para ejecutar la aplicación cuando se inicie el contenedor
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]