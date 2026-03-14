---
name: dockerfile-creation
description: >
  Technical reference for creating Dockerfiles, including best practices and common instructions. Use when the user asks about Dockerfile creation, image building, or containerization.
metadata:
  version: '1.0'
  author: dev-assistant
---

## 1. Executive Summary
A Dockerfile is a text file that contains all the commands a user could call on the command line to assemble an image. It serves as a blueprint for building Docker images, automating the process of creating a consistent and reproducible environment for applications. Dockerfiles are essential for containerizing applications, allowing developers to define the exact environment, dependencies, and commands needed to run their software within a Docker container. They solve the problem of "it works on my machine" by ensuring that the application runs identically across different environments.

## 2. Technical Concepts & Architecture
A Dockerfile consists of a series of instructions, each representing a command that Docker will execute during the image build process. These instructions are processed sequentially, with each instruction creating a new layer in the Docker image.

Key concepts include:
*   **Base Image**: Defined by the `FROM` instruction, it's the starting point for your image (e.g., `ubuntu`, `alpine`, `node`).
*   **Layers**: Each instruction in a Dockerfile creates a read-only layer. When an image is built, these layers are stacked on top of each other.
*   **Multi-stage Builds**: A powerful feature that allows you to use multiple `FROM` statements in a single Dockerfile. This helps to create smaller, more secure final images by separating build-time dependencies from runtime dependencies. For example, one stage can compile the application, and a subsequent stage can copy only the compiled artifacts into a much smaller base image.
*   **Instructions**: Keywords like `FROM`, `RUN`, `COPY`, `CMD`, `EXPOSE`, `WORKDIR`, `LABEL`, `ENV`, `ARG`, `VOLUME`, `USER`, `ENTRYPOINT` define specific actions during the image build.

## 3. Implementation & Quick Reference
Here's a quick reference for common Dockerfile instructions:

| Instruction | Description | Example |
|-------------|-------------|---------|
| `FROM`      | Sets the base image for subsequent instructions. | `FROM node:18-alpine` |
| `WORKDIR`   | Sets the working directory for any `RUN`, `CMD`, `ENTRYPOINT`, `COPY`, or `ADD` instruction that follows it. | `WORKDIR /app` |
| `COPY`      | Copies new files or directories from `<src>` and adds them to the filesystem of the container at path `<dest>`. | `COPY . .` |
| `RUN`       | Executes any commands in a new layer on top of the current image and commits the results. | `RUN npm install` |
| `EXPOSE`    | Informs Docker that the container listens on the specified network ports at runtime. | `EXPOSE 3000` |
| `CMD`       | Provides defaults for an executing container. There can only be one `CMD` instruction in a Dockerfile. | `CMD ["npm", "start"]` |
| `ENTRYPOINT`| Configures a container that will run as an executable. | `ENTRYPOINT ["/usr/bin/cowsay"]` |
| `ENV`       | Sets environment variables. | `ENV NODE_ENV=production` |
| `ARG`       | Defines a build-time variable. | `ARG VERSION=1.0` |
| `LABEL`     | Adds metadata to an image. | `LABEL maintainer="dev-assistant"` |
| `USER`      | Sets the user name or UID to use when running the image. | `USER node` |

**`docker init`**: This command can analyze your project and quickly create a Dockerfile, a `compose.yaml`, and a `.dockerignore`, helping you get started with containerization.

## 4. Practical Examples

### Example 1: Simple Node.js Application

This Dockerfile builds a simple Node.js application.

```dockerfile
# Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install application dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 3000

# Define the command to run the application
CMD ["npm", "start"]
```

### Example 2: Multi-stage Build for a Go Application

This example demonstrates a multi-stage build to create a small final image for a Go application.

```dockerfile
# Stage 1: Build the application
FROM golang:1.20-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o myapp .

# Stage 2: Create the final lightweight image
FROM alpine:latest

WORKDIR /root/

COPY --from=builder /app/myapp .

CMD ["./myapp"]
```

### Example 3: Python Flask Application

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Define the command to run the application
CMD ["flask", "run", "--host=0.0.0.0"]
```

## 5. Performance & Best Practices
*   **Use Multi-stage Builds**: This is crucial for creating smaller, more secure images by separating build-time tools and dependencies from the runtime environment.
*   **Choose the Right Base Image**:
    *   Prioritize official images from trusted sources.
    *   Opt for smaller base images like Alpine (`alpine:latest`, `node:18-alpine`, `python:3.9-slim-buster`) to reduce image size and attack surface.
*   **Minimize Layers**: Each `RUN` instruction creates a new layer. Combine multiple commands into a single `RUN` instruction using `&&` to reduce the number of layers.
*   **Leverage Build Cache**: Order your instructions from least to most frequently changing. Docker caches layers, so if a layer hasn't changed, it will reuse the cached version, speeding up builds.
*   **Use `.dockerignore`**: Exclude unnecessary files and directories (e.g., `node_modules`, `.git`, `__pycache__`) from the build context to reduce image size and build time.
*   **Run as a Non-Root User**: For security, avoid running your application as the `root` user inside the container. Use the `USER` instruction to switch to a less privileged user.
*   **Specific Tags for Base Images**: Instead of `latest`, use specific version tags (e.g., `node:18-alpine`) to ensure reproducible builds.
*   **Clean Up After `RUN` Commands**: Remove unnecessary files and caches created during `RUN` instructions to keep the image lean (e.g., `apt-get clean`, `rm -rf /var/lib/apt/lists/*`).

## 6. Diagnosis & Troubleshooting
*   **Check Build Logs**: Carefully examine the output of `docker build` for any errors or warnings. Docker provides detailed information about each step.
*   **Inspect Intermediate Containers**: If a build fails, Docker often leaves intermediate containers. You can inspect these to understand the state at the point of failure.
*   **Simplify the Dockerfile**: If you're facing complex issues, try to comment out sections of your Dockerfile and build it incrementally to isolate the problem.
*   **Consult Dockerfile Reference**: Refer to the official Dockerfile reference documentation for detailed explanations of each instruction and their behavior.
*   **Verify Paths**: Ensure that file paths in `COPY` and `ADD` instructions are correct relative to the build context.
*   **Network Issues**: If your `RUN` commands involve downloading packages, ensure the container has network access and that proxy settings (if any) are correctly configured.
*   **Permissions**: Check file and directory permissions within the container, especially if your application is failing to read or write files. Use `USER` and `chmod` as needed.
