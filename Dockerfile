FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instalar numpy primero (dependencia de surprise)
RUN pip install --no-cache-dir numpy==1.24.3

# Instalar el resto de dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p data models

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]