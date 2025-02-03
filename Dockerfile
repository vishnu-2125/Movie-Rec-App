# syntax=docker/dockerfile:1

# Use a specific Python version for the base image
ARG PYTHON_VERSION=3.12.2
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files and ensures unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install dependencies and add pymysql package
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt \
    && python -m pip install pymysql

# Switch to the non-privileged user to run the application
USER appuser

# Copy the source code into the container
COPY . .

# Set environment variables
ENV DATABASE_URL='mysql+pymysql://root:Karthik%4017@host.docker.internal/user_datas2'
ENV SECRET_KEY='your_secret_key'

# Expose the port that the application listens on
EXPOSE 8000

# Run the application
CMD python app.py
