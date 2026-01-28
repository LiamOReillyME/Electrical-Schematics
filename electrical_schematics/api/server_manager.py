"""Server manager for running FastAPI in background thread."""

import threading
import time
import socket
from typing import Optional
import uvicorn


class ServerManager:
    """Manages the FastAPI server lifecycle."""

    _instance: Optional['ServerManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one server instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize server manager."""
        if self._initialized:
            return

        self._server_thread: Optional[threading.Thread] = None
        self._server: Optional[uvicorn.Server] = None
        self._running = False
        self._host = "127.0.0.1"
        self._port = 8765  # Use non-standard port to avoid conflicts
        self._initialized = True

    @property
    def base_url(self) -> str:
        """Get the base URL for the local API server."""
        return f"http://{self._host}:{self._port}"

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running and self._server_thread is not None and self._server_thread.is_alive()

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self._host, port))
                return True
            except OSError:
                return False

    def _find_available_port(self, start_port: int = 8765, max_attempts: int = 10) -> int:
        """Find an available port starting from start_port."""
        for i in range(max_attempts):
            port = start_port + i
            if self._is_port_available(port):
                return port
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts}")

    def start(self) -> bool:
        """Start the FastAPI server in a background thread.

        Returns:
            True if server started successfully
        """
        if self.is_running:
            print(f"API server already running at {self.base_url}")
            return True

        try:
            # Find available port
            self._port = self._find_available_port()

            # Import app here to avoid circular imports
            from electrical_schematics.api.server import app

            # Configure uvicorn
            config = uvicorn.Config(
                app=app,
                host=self._host,
                port=self._port,
                log_level="warning",
                access_log=False
            )
            self._server = uvicorn.Server(config)

            # Run in background thread
            self._server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name="APIServer"
            )
            self._server_thread.start()

            # Wait for server to start
            max_wait = 5.0
            wait_interval = 0.1
            waited = 0.0

            while waited < max_wait:
                if self._check_server_ready():
                    self._running = True
                    print(f"API server started at {self.base_url}")
                    return True
                time.sleep(wait_interval)
                waited += wait_interval

            print("Warning: API server may not have started correctly")
            return False

        except Exception as e:
            print(f"Failed to start API server: {e}")
            return False

    def _run_server(self):
        """Run the uvicorn server (called in background thread)."""
        try:
            self._server.run()
        except Exception as e:
            print(f"API server error: {e}")
        finally:
            self._running = False

    def _check_server_ready(self) -> bool:
        """Check if server is ready to accept connections."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex((self._host, self._port))
                return result == 0
        except:
            return False

    def stop(self):
        """Stop the FastAPI server."""
        if self._server:
            self._server.should_exit = True
            self._running = False
            print("API server stopped")


# Global instance
_server_manager: Optional[ServerManager] = None


def get_server_manager() -> ServerManager:
    """Get the global server manager instance."""
    global _server_manager
    if _server_manager is None:
        _server_manager = ServerManager()
    return _server_manager


def ensure_server_running() -> str:
    """Ensure the API server is running and return base URL.

    Returns:
        Base URL of the running server
    """
    manager = get_server_manager()
    if not manager.is_running:
        manager.start()
    return manager.base_url
