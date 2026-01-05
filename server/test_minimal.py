"""
Minimal test app to debug Railway deployment
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Minimal test app running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/auth/register")
async def register():
    return {"message": "Register endpoint working"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"=" * 50)
    print(f"🚀 Starting minimal test app")
    print(f"📡 PORT env var: {os.getenv('PORT', 'NOT SET')}")
    print(f"🔌 Listening on: 0.0.0.0:{port}")
    print(f"=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=port)

