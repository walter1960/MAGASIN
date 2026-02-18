#!/usr/bin/env python3
"""
Desktop Application Wrapper using PyWebView
Launches FastAPI server and opens native window
"""
import webview
import threading
import time
import uvicorn
from pathlib import Path

def start_server():
    """Start FastAPI server in background thread"""
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

def main():
    """Main entry point for desktop application"""
    # Start FastAPI server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    # Create and start PyWebView window
    window = webview.create_window(
        title="Magasin Intelligent IA - VisionStock",
        url="http://127.0.0.1:8000",
        width=1600,
        height=1000,
        resizable=True,
        fullscreen=False,
        min_size=(1024, 768)
    )
    
    webview.start(debug=False)

if __name__ == "__main__":
    main()
