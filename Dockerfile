FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para mejor cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python de forma segura
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instalar numpy primero (dependencia de compilación)
RUN pip install --no-cache-dir numpy==1.24.3

# Instalar el resto de dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Crear directorios necesarios si no existen
RUN mkdir -p data models

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]