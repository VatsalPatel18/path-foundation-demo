# Use a standard Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install git and system dependencies required by openslide and trident (e.g., libvips)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    openslide-tools \
    libvips-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# --- Install Trident from source ---
# Clone the repository and install in editable mode so it's in the python path
RUN git clone https://github.com/mahmoodlab/trident.git /app/trident
RUN pip install --no-cache-dir -e /app/trident

# Copy only the requirements file for PathoLens to leverage Docker layer caching
COPY ./patholens/app/requirements.txt .

# Install PathoLens's Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire PathoLens application code into the container
COPY ./patholens/app /app

# Expose the port the app will run on
EXPOSE 8080

# Define the command to run the application using uvicorn
# The app is located in /app/services/main.py
CMD ["uvicorn", "services.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
