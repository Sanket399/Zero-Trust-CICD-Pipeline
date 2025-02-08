# Use the official NGINX base image
FROM docker.io/library/nginx:alpine

# Set working directory
WORKDIR /usr/share/nginx/html

# Remove default NGINX content
RUN rm -rf ./*

# Copy static website files into the container
COPY . .

# Expose port 80
EXPOSE 80

# Add the HEALTHCHECK instruction
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:80/ || exit 1

# Start NGINX server
CMD ["nginx", "-g", "daemon off;"]
