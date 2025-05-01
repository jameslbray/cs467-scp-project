FROM python:3.13-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY services/rabbitmq /app/services/rabbitmq/

# Set Python path
ENV PYTHONPATH=/app

# Run setup script
CMD ["python", "-m", "services.rabbitmq.setup"]
