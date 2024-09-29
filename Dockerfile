FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install python-dotenv
ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV API_URL=$API_URL
ENV API_KEY=$API_KEY
ENV VIP_DURATION_HOURS=$VIP_DURATION_HOURS
ENV CHANNEL_ID=$CHANNEL_ID
CMD ["python", "frontline-pass.py"]
