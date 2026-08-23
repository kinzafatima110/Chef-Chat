# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set env variable for Flask production mode
ENV FLASK_ENV=production

# Expose port (Render sets PORT env variable dynamically)
EXPOSE 5050

# Run the web application using Gunicorn (production WSGI server)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5050} app:app"]
