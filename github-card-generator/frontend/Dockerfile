# Use ultra-lightweight Nginx alpine image
FROM nginx:alpine

# Copy index.html into the Nginx serving directory
COPY index.html /usr/share/nginx/html/index.html

# Expose Nginx default serving port
EXPOSE 80

# At container startup, run envsubst on index.html to inject BACKEND_URL environment variable.
# Passing '$BACKEND_URL' is critical so envsubst only replaces $BACKEND_URL
# and leaves standard JS template literals (${variable}) untouched!
CMD ["/bin/sh", "-c", "envsubst '$BACKEND_URL' < /usr/share/nginx/html/index.html > /usr/share/nginx/html/index.html.tmp && mv /usr/share/nginx/html/index.html.tmp /usr/share/nginx/html/index.html && exec nginx -g 'daemon off;'"]
