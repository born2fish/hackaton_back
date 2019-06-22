# Use an official Python runtime as a parent image
FROM python:3.7

# Set the working directory to /app
WORKDIR /application

# Copy the current directory contents into the container at /app
ADD . /application

# Install any needed packages
RUN python setup.py develop

# Make port 8080 available to the world outside this container
EXPOSE 8080