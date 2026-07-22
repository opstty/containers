# Use a lightweight Python image
FROM python:3.14-slim

# Set environment variables to ensure Python output is sent straight to terminal 
# without buffering (crucial for seeing logs in ArgoCD/Kubernetes)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies if needed (none strictly required for this script, 
# but good practice for network-heavy containers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the sync script into the container
COPY password.py .

# Run the script when the container starts
CMD ["python", "password.py"]
