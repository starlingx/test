# Use a minimal Node.js runtime on Alpine
FROM node:alpine
# Install curl
RUN apk add --no-cache curl
# Set working directory
WORKDIR /usr/src/app
# Copy application files
COPY server.js .
# Expose port 8080
EXPOSE 8080
# Start the server
CMD ["node", "server.js"]
