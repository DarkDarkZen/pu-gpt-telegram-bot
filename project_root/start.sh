#!/bin/bash

# Print environment variables (excluding sensitive data)
echo "Available environment variables:"
env | grep -v 'TOKEN\|KEY'

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ] && [ -z "$TELEGRAM_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN must be set"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY must be set"
    exit 1
fi

# Create necessary directories
mkdir -p data logs

# Start the FastAPI server
python api.py &
API_PID=$!

# Wait a bit for the API to start
sleep 5

# Start the bot
python bot.py &
BOT_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down services..."
    kill $API_PID
    kill $BOT_PID
    exit 0
}

# Set up signal handling
trap cleanup SIGTERM SIGINT

# Wait for both processes
wait 