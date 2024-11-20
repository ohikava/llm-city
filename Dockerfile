FROM --platform=linux/amd64 python:3.12

# Rest of your Dockerfile remains the same
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "run.py"]