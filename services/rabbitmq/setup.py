from setuptools import setup, find_packages

setup(
    name="rabbitmq-client",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pika==1.3.2",
        "fastapi==0.110.0",
        "uvicorn==0.27.1",
        "python-dotenv==1.0.1",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A RabbitMQ client for microservices",
    keywords="rabbitmq, messaging, microservices",
    python_requires=">=3.13",
)
