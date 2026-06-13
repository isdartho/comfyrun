# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create output directory
RUN mkdir -p output

# Expose port (if needed for MCP server or other services)
# Adjust based on your actual port usage
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - run the MCP server
CMD ["python", "comfy_mcp.py"]