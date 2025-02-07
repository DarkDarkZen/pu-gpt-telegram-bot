from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Bot API is running"}

@app.get("/health")
async def health_check():
    # Check if required environment variables are set
    required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Missing required environment variables: {', '.join(missing_vars)}"
            }
        )
    
    return JSONResponse(
        content={
            "status": "healthy",
            "environment": "production" if os.getenv("RAILWAY_ENVIRONMENT") else "development"
        }
    )

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "3000"))) 