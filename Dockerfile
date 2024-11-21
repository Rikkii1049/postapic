# Use the official Python image as a base
FROM python:3.11.10-alpine3.20

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app files
COPY . .

# Expose the app's port (e.g., 5000)
EXPOSE 5000

# Command to run the app
CMD ["python", "app/app.py"]  # Update to your app's entry point
