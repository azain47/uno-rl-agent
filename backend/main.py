import sys
import os

import random
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager

from network import DQNAgent, UnoEnvironment  # Assuming these exist
from utils import colorize_card_strings # Assuming this exists

# --- Pydantic Models ---
class GameStateResponse(BaseModel):
    player_hand: List[str]
    agent_hand_size: int
    current_player: str
    top_card: str
    current_color: str
    legal_actions: List[Dict[str, Any]]
    discard_pile_top: List[str] # Top few cards
    message: str 
    agent_actions: Optional[List[str]] = None 
    winner: Optional[str] = None

class ActionRequest(BaseModel):
    action_index: int

class ColorChoiceRequest(BaseModel):
    color: str # 'r', 'g', 'b', 'y'

# --- FastAPI Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    global game_env, agent
    print("Application startup...")
    try:
        # Initialize environment and agent on startup
        game_env = UnoEnvironment() 
        agent = load_agent_model(agent_model_path, game_env)
        print("Game environment and agent initialized successfully.")
    except Exception as e:
        print(f"FATAL ERROR during startup: Failed to initialize game environment or load agent: {e}")
        game_env = None
        agent = None

    yield # Application runs here

    # --- Shutdown logic (optional) ---
    print("Application shutdown...")
    # Add any cleanup logic if needed, e.g., saving state


# --- FastAPI App ---
# Pass the lifespan manager to the FastAPI app
app = FastAPI(title="UNO RL Agent Game", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

game_env: Optional[UnoEnvironment] = None
agent: Optional[DQNAgent] = None
game_state: Dict[str, Any] = {} # Stores the current state from env.step()
current_player_turn: str = "human"
discard_pile_history: List[str] = []
human_needs_to_choose_color: bool = False
agent_model_path = "./checkpoints/uno_model_16000.pt" 
color_mappings = {'r': "Red", 'g': "Green", 'b': "Blue", 'y': "Yellow"}
current_difficulty: int = 2 # Default to Medium
DIFFICULTY_SCALER_FUNC: Optional[callable] = None 

# --- Helper Functions ---
def load_agent_model(model_path: str, env: UnoEnvironment):
    """Loads the DQN agent model and the difficulty scaler function via exec."""
    global DIFFICULTY_SCALER_FUNC 
    print("Loading AI agent...")
    # Ensure input/output sizes match the agent's definition in network.py
    # Example size: state_size = 19 + 4 + (19 * 7) + 3 + 1 + 1 = 160? action_size=61
    # Verify these numbers against your DQNAgent class definition
    state_size = 161 
    action_size = 61 
    loaded_agent = DQNAgent(state_size, action_size, env)
    try:
        loaded_agent.load_model(model_path)
        print(f"Successfully loaded agent from {model_path}")
        loaded_agent.epsilon = 0.05 # Set agent to evaluation mode

        # --- Load difficulty_scaler function via exec (USE WITH CAUTION) ---
        if hasattr(loaded_agent, 'difficulty_scaler'):
            scaler_code = loaded_agent.difficulty_scaler
            exec(scaler_code, globals())
            DIFFICULTY_SCALER_FUNC = difficulty_scaler
        else:
            print("Warning: Agent object does not have a valid 'difficulty_scaler' string attribute.")
            DIFFICULTY_SCALER_FUNC = None
        # --------------------------------------------------------------------

    except FileNotFoundError:
         print(f"Error: Agent model file not found at {model_path}")
         raise HTTPException(status_code=500, detail=f"Agent model file not found: {model_path}")
    except Exception as e:
        print(f"Error loading agent model or scaler: {e}")
        # Handle error appropriately
        raise HTTPException(status_code=500, detail=f"Failed to load AI agent model or scaler from {model_path}: {e}")
    return loaded_agent

def format_legal_actions(state: Dict[str, Any], env: UnoEnvironment) -> List[Dict[str, Any]]:
    """Formats legal actions for the API response."""
    formatted_actions = []
    if 'legal_actions' in state:
        for index in state['legal_actions']:
            action_str = env.game.index_to_action.get(index, f"Unknown Action ({index})")
            formatted_actions.append({"action_str": action_str, "action_index": index})
    return formatted_actions

def get_current_game_state_response(human_action_message: Optional[str] = None, agent_action_messages: Optional[List[str]] = None) -> GameStateResponse:
    """Constructs the API response for the current game state, including action messages."""
    global game_env, game_state, current_player_turn, discard_pile_history

    if not game_env or not game_state:
        raise HTTPException(status_code=404, detail="Game not started")

    human_player = game_env.game.players[0]
    agent_player = game_env.game.players[1]

    # Simplify message to just include played cards
    final_message = ""
    filtered_agent_messages = []
    
    if human_action_message:
        final_message = human_action_message
    
    if agent_action_messages:
        # Filter only card-related messages
        filtered_agent_messages = [msg for msg in agent_action_messages if msg and "Agent played" in msg]
            
    # Add winner status if game is over
    winner = game_env.game.get_winner().name if game_env.game.game_over() else None
    if winner:
        final_message = f"Game Over! Winner: {winner}"
    
    return GameStateResponse(
        player_hand=sorted(game_state.get('hand', [])),
        agent_hand_size=len(agent_player.hand),
        current_player=current_player_turn,
        top_card=game_state.get('target', 'N/A'),
        current_color=color_mappings.get(game_env.game.current_color, 'Wild'),
        legal_actions=format_legal_actions(game_state, game_env) if current_player_turn == "human" else [],
        discard_pile_top=discard_pile_history[-5:],
        message=final_message,
        agent_actions=filtered_agent_messages, # Only pass card play messages
        winner=winner
    )

def _trigger_agent_turn() -> Tuple[Dict[str, Any], List[str]]:
    """Handles the logic for the agent's turn, returning the final state and a list of agent messages."""
    global game_env, agent, game_state, current_player_turn, discard_pile_history

    agent_messages = [] # Changed to list
 
    while current_player_turn == "agent":
        if not game_env or not agent or not game_state:
            print("Error: Game/Agent not initialized during agent turn.")
            current_player_turn = "human"
            agent_messages.append("Error during agent turn.") 
            return game_state, agent_messages

        if game_env.game.game_over():
            print("Agent turn skipped: Game already over.")
            break

        print("Agent's turn starting inside loop...")
        legal_actions = game_state.get('legal_actions', [])
        if not legal_actions:
            print("Agent has no legal actions. Passing turn to human.")
            current_player_turn = "human"
            break

        # Agent selects action
        action_index = None
        action_str = None
        scaled_action_applied = False
        
        if DIFFICULTY_SCALER_FUNC is not None:
            try:
                if hasattr(game_env, 'game') and hasattr(game_env.game, 'index_to_action') and hasattr(game_env.game, 'action_space'):
                    index_to_action_map = game_env.game.index_to_action
                    action_space_map = game_env.game.action_space
                    scaled_action_info = DIFFICULTY_SCALER_FUNC(
                        game_state, discard_pile_history, index_to_action_map, current_difficulty
                    )
                    if isinstance(scaled_action_info, dict) and 'selected_card' in scaled_action_info:
                        action_str = scaled_action_info['selected_card']
                        if action_str in action_space_map:
                             action_index = action_space_map[action_str]
                             if action_index in legal_actions:
                                 print(f"Agent using action from difficulty scaler: {action_str} ({action_index})")
                                 scaled_action_applied = True
                             else:
                                 print(f"Warning: Scaler chose illegal action '{action_str}'. Falling back to agent policy.")
                                 action_index = None
                                 action_str = None
                        else:
                             print(f"Warning: Scaler chose unknown action string '{action_str}'. Falling back to agent policy.")
                else:
                     print("Warning: game_env.game missing required attributes for scaler.")
            except Exception as scaler_e:
                print(f"Error during difficulty_scaler execution: {scaler_e}. Falling back.")
                action_index = None
                action_str = None

        # Fallback
        if not scaled_action_applied:
            print("Agent using default DQN policy.")
            action_index = agent.select_action(game_state, legal_actions)
            action_str = game_env.game.index_to_action[action_index]

        # Ensure valid action
        if action_index is None or action_str is None:
             print("Error: Agent failed to select a valid action. Passing turn.")
             current_player_turn = "human"
             break

        print(f"Agent action determined: {action_str} ({action_index})")
        
        # Handle agent drawing card 
        if action_str == "draw_card":
            next_state, _, game_over, next_player_idx = game_env.step(action_index, return_drawn_card=True)
            drawn_card = next_state.get('drawn_card')
            agent_messages.append(f"Agent played: draw_card")
            
            discard_pile_history.append("draw_card") 
            game_state = next_state 
            
            if game_over:
                print("Game over after agent draw!")
                current_player_turn = "game_over"
                break 
            else:
                current_player_turn = "human" 
                print(f"Agent drew card. Turn passes to human.")
                break 
        
        else:
            agent_messages.append(f"Agent played: {action_str}") # Simplified message
            next_state, _, game_over, next_player_idx = game_env.step(action_index)
            discard_pile_history.append(action_str) 
            game_state = next_state 

            if game_over:
                print("Game over! Agent wins!")
                current_player_turn = "game_over"
                break 
            elif next_player_idx == 1: 
                print("Agent plays again (Skip/Reverse).")
                current_player_turn = "agent" 
                # No additional message for "plays again"
            else:
                current_player_turn = "human"
                print(f"Agent played {action_str}. Turn passes to human.")
                break 

    return game_state, agent_messages

# --- API Endpoints ---
@app.get("/", include_in_schema=False)
async def root():
    """Redirects the root path to the API documentation."""
    return RedirectResponse(url="/docs")

@app.post("/start_game", response_model=GameStateResponse, summary="Start a new game with optional difficulty")
async def start_game(difficulty: Optional[int] = None):
    """Initializes a new UNO game session.

    - **difficulty**: Optional difficulty level (1=Easy, 2=Medium, 3=Hard). Defaults to 2.
    """
    global game_env, agent, game_state, current_player_turn, discard_pile_history, human_needs_to_choose_color, current_difficulty
    if not agent or not game_env:
         raise HTTPException(status_code=500, detail="Agent or game environment not loaded properly.")

    # Set difficulty
    if difficulty is not None and 1 <= difficulty <= 3:
        current_difficulty = difficulty
        print(f"Setting game difficulty to: {current_difficulty}")
    else:
        current_difficulty = 2 # Default to medium if invalid or not provided
        print(f"Using default difficulty: {current_difficulty}")

    print("Starting a new game...")
    game_state = game_env.reset()
    game_env.game.players[0].name = "human"
    game_env.game.players[1].name = "agent"
    current_player_turn = "human" # Human starts
    discard_pile_history = [game_state.get('target', 'N/A')] # Initial card
    human_needs_to_choose_color = False
    print("New game started. Human turn.")
    return get_current_game_state_response()

@app.get("/game_state", response_model=GameStateResponse, summary="Get the current game state")
async def get_state():
    """Returns the current state of the game."""
    if not game_env:
        raise HTTPException(status_code=404, detail="Game not started. Call /start_game first.")
    return get_current_game_state_response()

@app.post("/play_action", response_model=GameStateResponse, summary="Human plays an action")
async def play_action(action: ActionRequest):
    """Allows the human player to play a card or draw, then triggers agent turn if needed."""
    global game_env, game_state, current_player_turn, discard_pile_history, human_needs_to_choose_color

    if not game_env or not game_state:
        raise HTTPException(status_code=404, detail="Game not started")
    if current_player_turn != "human":
        raise HTTPException(status_code=400, detail="Not human's turn")
    if human_needs_to_choose_color:
         raise HTTPException(status_code=400, detail="Human must choose a color first via /choose_color")

    action_index = action.action_index
    if action_index not in game_state.get('legal_actions', []):
        raise HTTPException(status_code=400, detail="Invalid action index")

    action_str = game_env.game.index_to_action[action_index]
    print(f"Human chose action: {action_str} ({action_index})")
    human_action_message = f"You played: {action_str}"
    agent_action_messages = []

    # --- Handle Wild Card Color Selection ---
    if "wild" in action_str:
        game_state["pending_wild_action"] = action_index
        human_needs_to_choose_color = True
        print("Human played wild card. Waiting for color choice.")
        # Construct response *without* triggering agent turn yet
        response = get_current_game_state_response(
            human_action_message="You played: Wild card (pending color choice)"
        )
        return response

    # --- Handle Draw Card ---
    elif action_str == "draw_card":
        next_state, _, game_over, next_player_idx = game_env.step(action_index, return_drawn_card=True)
        drawn_card = next_state.get('drawn_card')
        human_action_message = f"You played: draw_card"

        game_state = next_state
        discard_pile_history.append("draw_card")

        if game_over:
            print("Game potentially over after human draw")
            current_player_turn = "game_over"
        else:
            # Turn ALWAYS passes after drawing 
            current_player_turn = "agent"
            print("Human drew card. Turn passes to agent.")
            # Now trigger agent turn
            game_state, agent_action_messages = _trigger_agent_turn()

    # --- Handle Regular Card Play ---
    else:
        next_state, _, game_over, next_player_idx = game_env.step(action_index)
        game_state = next_state
        discard_pile_history.append(action_str)

        if game_over:
            print("Game over! Human wins!")
            current_player_turn = "game_over"
        elif next_player_idx == 0: # Human plays again
             print("Human plays again (Skip/Reverse).")
             current_player_turn = "human"
        else: # Turn passes to agent
             print("Human played. Turn passes to agent.")
             current_player_turn = "agent"
             # Trigger agent turn
             game_state, agent_action_messages = _trigger_agent_turn()

    # --- Construct Final Response --- 
    response = get_current_game_state_response(
        human_action_message=human_action_message,
        agent_action_messages=agent_action_messages
    )
    return response

@app.post("/choose_color", response_model=GameStateResponse, summary="Human chooses color after playing Wild")
async def choose_color(choice: ColorChoiceRequest):
    """Allows the human player to choose a color, then triggers agent turn."""
    global game_env, game_state, current_player_turn, discard_pile_history, human_needs_to_choose_color

    if not game_env or not game_state:
        raise HTTPException(status_code=404, detail="Game not started")
    if current_player_turn != "human":
        raise HTTPException(status_code=400, detail="Not human's turn")
    if not human_needs_to_choose_color or "pending_wild_action" not in game_state:
         raise HTTPException(status_code=400, detail="No pending Wild card color choice")

    chosen_color = choice.color
    if chosen_color not in ['r', 'g', 'b', 'y']:
        raise HTTPException(status_code=400, detail="Invalid color choice. Use 'r', 'g', 'b', or 'y'.")

    pending_action_index = game_state.pop("pending_wild_action")
    base_action_str = game_env.game.index_to_action[pending_action_index]
    wild_type = "wild_draw_4" if "draw_4" in base_action_str else "wild"
    action_str = f"{chosen_color}-{wild_type}"
    action_index = game_env.game.action_space.get(action_str)

    if action_index is None:
        # Debug output to help identify the issue
        wild_actions = [action for action in game_env.game.action_space.keys() if "wild" in action.lower()]
        colored_wilds = [action for action in game_env.game.action_space.keys() 
                        if chosen_color in action and ("wild" in action.lower())]
        print(f"Wild actions available: {wild_actions}")
        print(f"Colored wild actions with {chosen_color}: {colored_wilds}")
        print(f"Attempted wild action string: {action_str}")
        print(f"Base action string: {base_action_str}")
        print(f"Action space keys: {list(game_env.game.action_space.keys())}")
        
        human_needs_to_choose_color = False # Reset flag
        raise HTTPException(status_code=500, detail=f"Could not map chosen color {chosen_color} to action.")

    print(f"Human chose color: {color_mappings[chosen_color]}. Final action: {action_str} ({action_index})")
    human_needs_to_choose_color = False
    human_action_message = f"You played: {action_str}"
    agent_action_messages = []

    # --- Execute the step with the full wild card action ---
    next_state, _, game_over, next_player_idx = game_env.step(action_index)
    game_state = next_state
    discard_pile_history.append(action_str)

    if game_over:
        print("Game over! Human wins!")
        current_player_turn = "game_over"
    elif next_player_idx == 0: 
         print("Turn remains with human after wild? (Unexpected)")
         current_player_turn = "human" 
    else: # Turn passes to agent
         print("Human played Wild+Color. Turn passes to agent.")
         current_player_turn = "agent"
         # Trigger agent turn
         game_state, agent_action_messages = _trigger_agent_turn()

    # --- Construct Final Response --- 
    response = get_current_game_state_response(
        human_action_message=human_action_message,
        agent_action_messages=agent_action_messages
    )
    return response

# --- Optional: Add endpoint to get static game info ---
@app.get("/game_info", summary="Get static game information")
async def game_info():
    """Returns information about the game setup (e.g., colors)."""
    return {"colors": color_mappings}

# --- Run with Uvicorn ---
# You would typically run this using: uvicorn main:app --reload
# Example of how to run programmatically (less common for dev)
if __name__ == "__main__":
    import uvicorn
    print("Starting server with uvicorn...")
    uvicorn.run(app, host="127.0.0.1", port=8000) 