# Use a standard Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies that may be needed by Python libraries like openslide
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    openslide-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file to leverage Docker layer caching
COPY ./patholens/app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
COPY ./patholens/app /app

# Expose the port the app will run on
EXPOSE 8080

# Define the command to run the application using uvicorn
# The app is located in /app/services/main.py
# --reload is used for development to automatically restart on code changes
CMD ["uvicorn", "services.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
