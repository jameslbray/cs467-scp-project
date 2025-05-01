#!/bin/bash
set -e

# Start RabbitMQ in the background
docker-entrypoint.sh rabbitmq-server &

# Wait for RabbitMQ to be ready
until rabbitmq-diagnostics check_port_connectivity; do
    echo "Waiting for RabbitMQ to be ready..."
    sleep 2
done

echo "RabbitMQ is ready! Setting up queues..."

# Run our Python setup script
python -m services.rabbitmq.setup

# Keep container running
wait $!