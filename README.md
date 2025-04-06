# UNO RL Agent

This project implements a game of UNO where a human can play against an AI agent trained using Reinforcement Learning (DQN). It consists of a Python FastAPI backend and a React frontend.

## Project Structure

- `/backend`: Contains the FastAPI server, game logic, and RL agent implementation.
- `/frontend`: Contains the React user interface.

## Setup

### Backend (Python)

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Create and activate a virtual environment (optional but recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Depending on your system, you might need specific instructions to install PyTorch. Please refer to the [official PyTorch website](https://pytorch.org/get-started/locally/) for details.*

### Frontend (Node.js)

1.  **Navigate to the frontend directory (from the root):**
    ```bash
    cd frontend
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```

## Running the Application

1.  **Run the backend server:**
    *   Make sure you are in the `backend` directory with your virtual environment activated (if used).
    *   Run the FastAPI application using Uvicorn:
        ```bash
        uvicorn main:app --reload --port 8000
        ```
    *   The backend server will be available at `http://localhost:8000`.

2.  **Run the frontend development server:**
    *   Make sure you are in the `frontend` directory.
    *   Run the Vite development server:
        ```bash
        npm run dev
        ```
    *   The frontend application will likely open automatically in your browser at `http://localhost:5173`. If not, navigate to that address manually.

Now you can play UNO against the AI agent through the web interface! 