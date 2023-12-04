# Use an official Python runtime as a parent image
FROM python:3.10.9

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 6002 available to the world outside this container
EXPOSE 6002

# Run app.py when the container launches
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:6002", "-w", "4", "--timeout", "300"]
