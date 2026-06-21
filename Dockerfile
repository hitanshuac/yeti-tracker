FROM python:3.11-slim

# Hugging Face Spaces requires a non-root user
RUN useradd -m -u 1000 user
WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Switch to the non-root user
USER user

# Streamlit config (HF Spaces explicitly requires port 7860)
EXPOSE 7860
ENV PORT=7860

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
