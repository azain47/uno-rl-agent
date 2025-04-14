import { useState, useEffect, useRef } from 'react'
import axios from 'axios';
import { Button } from './components/ui/button';
import { ThemeToggle } from './components/ui/theme-toggle';
import UnoCard from './components/UnoCard';
import './App.css';

// Helper function to format card strings for display
function formatCardName(cardString) {
  if (!cardString || typeof cardString !== 'string') return 'Unknown Card';
  if (cardString === 'draw_card') return 'Draw Card';

  const parts = cardString.split('-');
  let colorCode = parts[0];
  let value = parts.length > 1 ? parts.slice(1).join('-') : colorCode;

  const colorMap = {
    'r': 'Red',
    'g': 'Green',
    'b': 'Blue',
    'y': 'Yellow',
  };

  let formattedColor = colorMap[colorCode] || ''; // Empty if wild or unknown
  let formattedValue = '';

  // Format value
  switch (value) {
    case 'skip': formattedValue = 'Skip'; break;
    case 'reverse': formattedValue = 'Reverse'; break;
    case 'draw_2': formattedValue = 'Draw 2'; break;
    case 'wild': formattedValue = 'Wild'; formattedColor = ''; break;
    case 'wild_draw_4': formattedValue = 'Wild Draw 4'; formattedColor = ''; break;
    default: formattedValue = value.toUpperCase(); // Assumes number cards
  }
  
  return (formattedColor ? formattedColor + ' ' : '') + formattedValue;
}

// Helper to format the whole action message
function formatActionMessage(rawMessage) {
  if (!rawMessage || !rawMessage.includes(': ')) return rawMessage;
  
  const parts = rawMessage.split(': ');
  const prefix = parts[0];
  const cardString = parts[1];
  
  return `${prefix}: ${formatCardName(cardString)}`;
}

function App() {
  
  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [needsColorChoice, setNeedsColorChoice] = useState(false);
  const [difficulty, setDifficulty] = useState(2); // Default medium
  const [gameStarted, setGameStarted] = useState(false);
  const [showMessageTimeout, setShowMessageTimeout] = useState(null);
  const [actionMessage, setActionMessage] = useState("");
  const [animatingCard, setAnimatingCard] = useState(null);
  const [animatingAgentCards, setAnimatingAgentCards] = useState([]);
  const [agentActionsQueue, setAgentActionsQueue] = useState([]);
  const [agentTurnLog, setAgentTurnLog] = useState([]);
  const prevGameStateRef = useRef(null);
  const [isLogVisible, setIsLogVisible] = useState(false); // State for log visibility

  // Change this to point directly to the backend server
  const API_BASE_URL = 'http://localhost:8000'; // Point directly to backend

  // Display temporary action messages with auto-fade
  useEffect(() => {
    if (actionMessage) {
      if (showMessageTimeout) clearTimeout(showMessageTimeout);
      const timeout = setTimeout(() => {
        setActionMessage("");
      }, 3000);
      setShowMessageTimeout(timeout);
      return () => clearTimeout(timeout);
    }
  }, [actionMessage]);

  // Process agent actions queue 
  useEffect(() => {
    if (agentActionsQueue.length === 0 || animatingAgentCards.length > 0) {
      return;
    }

    const nextAction = agentActionsQueue[0];
    const newQueue = [...agentActionsQueue.slice(1)];

    const formattedMsg = formatActionMessage(nextAction);
    setActionMessage(formattedMsg);

    let needsAnimation = false;
    let playedCard = null;
    if (nextAction && nextAction.includes("Agent played: ")) {
      playedCard = nextAction.replace("Agent played: ", "");
      if (playedCard !== "draw_card") {
        needsAnimation = true;
      }
    }

    if (needsAnimation && playedCard) {
      handleAgentCardPlay(playedCard, () => {
        const delayBetweenAnimations = 500; // ms pause
        const timeoutId = setTimeout(() => {
           setAgentActionsQueue(newQueue);
        }, delayBetweenAnimations);
      });

    } else {
      const readDelay = 1000;
      const timeoutId = setTimeout(() => {
        setAgentActionsQueue(newQueue);
      }, readDelay);
      return () => clearTimeout(timeoutId);
    }
    
  }, [agentActionsQueue, animatingAgentCards]);

  // Track changes to agent's actions and update queue
  useEffect(() => {
    if (gameState?.agent_actions?.length > 0) {
      if (JSON.stringify(gameState.agent_actions) !== JSON.stringify(agentActionsQueue)) {
        setAgentActionsQueue(gameState.agent_actions);
      }
    }
  }, [gameState?.agent_actions]);

  // Track changes to agent's actions and update log
  useEffect(() => {
    if (gameState?.agent_actions && gameState.agent_actions.length > 0) {
      const prevActions = prevGameStateRef.current?.agent_actions;
      if (JSON.stringify(gameState.agent_actions) !== JSON.stringify(prevActions)) {
        const formattedLog = gameState.agent_actions.map(action => {
          if (action.includes(': ')) {
            return formatCardName(action.split(': ')[1]);
          }
          return action;
        });
        setAgentTurnLog(formattedLog);
      }
    } 
    else if (prevGameStateRef.current?.agent_actions?.length > 0 && !gameState?.agent_actions) {
    }

    prevGameStateRef.current = gameState;

  }, [gameState]);

  // Function to handle agent card play animation
  const handleAgentCardPlay = (cardString, onComplete) => {
    const randomRotation = Math.floor(Math.random() * 20 - 10);
    const animCard = { cardString, rotation: randomRotation };
    setAnimatingAgentCards([animCard]);
    
    const animationDuration = 700; // Duration of the CSS animation
    const timeoutId = setTimeout(() => {
      setAnimatingAgentCards([]); // Clear animation state
      if (onComplete) {
        onComplete(); // Trigger callback (which will then delay and dequeue)
      }
    }, animationDuration);
    
    // Cleanup timeout for this specific animation instance
    return () => clearTimeout(timeoutId);
  };

  // Function to handle human card play animation
  const handleHumanCardPlay = (cardString) => {
    if (animatingCard) return;
    const randomRotation = Math.floor(Math.random() * 20 - 10);
    setAnimatingCard({ cardString, rotation: randomRotation });
    setTimeout(() => {
      setAnimatingCard(null);
    }, 600);
  };

  // Function to start a new game
  const startGame = async () => {
    setLoading(true);
    setError(null);
    setNeedsColorChoice(false);
    setGameState(null);
    setGameStarted(false);
    setActionMessage("");
    setAnimatingCard(null);
    setAnimatingAgentCards([]);
    setAgentActionsQueue([]);
    setAgentTurnLog([]);
    try {
      const response = await axios.post(`${API_BASE_URL}/start_game?difficulty=${difficulty}`);
      setGameState(response.data);
      setGameStarted(true);
      setActionMessage("Game started! Your turn first.");
    } catch (err) {
      console.error("Start game error:", err);
      setError(err.response?.data?.detail || 'Failed to start game');
    } finally {
      setLoading(false);
    }
  };

  // Function to handle playing a card or drawing
  const playAction = async (actionIndex, chosenCard) => {
    if (loading || gameState?.current_player !== 'human' || gameState?.winner) return;

    const isWildCard = chosenCard?.includes('wild');
    const isDrawCard = chosenCard === "draw_card";
    
    if (!isDrawCard && !isWildCard && chosenCard) {
      handleHumanCardPlay(chosenCard);
    }

    setLoading(true);
    setError(null);
    setNeedsColorChoice(false);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/play_action`, { action_index: actionIndex });
      console.log("📬 Play Action Response Received:", response.data);
      
      const formattedMsg = formatActionMessage(response.data.message);

      if (isWildCard) {
        setGameState(response.data);
        setActionMessage(formattedMsg);
        setNeedsColorChoice(true);
      } else {
        setActionMessage(formattedMsg);
        setGameState(response.data);
        
        // Save previous gameState for compare if needed
        prevGameStateRef.current = gameState;
      }

    } catch (err) {
      console.error("Play action error:", err);
      setError(err.response?.data?.detail || 'Failed to play action');
      // Attempt to fetch fresh state to recover
      fetchGameState();
    } finally {
      setLoading(false);
    }
  };

  // Function to choose color for wild card
  const chooseColor = async (color) => {
    if (loading || !needsColorChoice || gameState?.winner) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const colorCode = color.charAt(0).toLowerCase();
      if (!['r', 'g', 'b', 'y'].includes(colorCode)) {
        throw new Error(`Invalid color code: ${colorCode}`);
      }
      
      const response = await axios.post(`${API_BASE_URL}/choose_color`, { color: colorCode });
      console.log("📬 Choose Color Response Received:", response.data);
      
      const formattedMsg = formatActionMessage(response.data.message);
      
      let playedWildCard = null;
      if (response.data.message && response.data.message.startsWith("You played: ")) {
        playedWildCard = response.data.message.replace("You played: ", "");
      }
      
      if (playedWildCard && playedWildCard.includes('wild')) {
        handleHumanCardPlay(playedWildCard); 
      }
      
      setActionMessage(formattedMsg);
      setGameState(response.data);
      setNeedsColorChoice(false);
      
    } catch (err) {
      console.error("Choose color error:", err);
      if (err.response?.data?.detail) {
        setError(`Color choice error: ${err.response.data.detail}`);
      } else {
        setError(`Failed to choose color: ${err.message || 'Unknown error'}`);
      }
      fetchGameState();
      setNeedsColorChoice(false);
    } finally {
      setLoading(false);
    }
  };

  // Function to fetch the current game state (useful for recovery)
  const fetchGameState = async () => {
    if (!gameStarted) {
      console.log("Game not started, skipping fetchGameState");
      return;
    }
    
    console.log("🔄 Fetching current game state...");
    setLoading(true);
    setError(null);
    
    try {
      console.log("📡 Sending GET request to /game_state");
      const response = await axios.get(`${API_BASE_URL}/game_state`, {
        timeout: 5000,
        headers: { 
          'Content-Type': 'application/json',
          'X-Client-Version': '1.0'
        }
      });
      
      console.log("✅ Game state received:", response.data);
      
      console.log("Debug player hand:", response.data.player_hand);
      
      setGameState(response.data);
      
      if (response.data.message?.includes('Choose a color')) {
        setNeedsColorChoice(true);
      } else {
        setNeedsColorChoice(false);
      }
      
      return response.data;
    } catch (err) {
      console.error("❌ Fetch state error:", err);
      
      // Generate detailed error message
      let errorDetail = 'Unknown error';
      if (err.response) {
        if (err.response.status === 404) {
          console.log("Game not found, need to start a new game");
          setGameStarted(false);
          return null;
        }
        errorDetail = `Server error ${err.response.status}: ${err.response.data?.detail || err.response.statusText}`;
      } else if (err.request) {
        errorDetail = 'No response from server (timeout or network issue)';
      } else {
        errorDetail = err.message || 'Request setup failed';
      }
      
      setError(`Failed to fetch game state: ${errorDetail}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Determine current turn indicator
  const getTurnIndicator = () => {
    if (gameState?.winner) return "Game Over";
    if (needsColorChoice) return "Choose a color";
    return gameState?.current_player === 'human' ? "Your Turn" : "Agent's Turn";
  }

  // Function to handle a card click from the player's hand
  const handleCardClick = (card) => {
    // Combine all disabling conditions
    const isHumanInteractionDisabled = 
      loading || 
      gameState.current_player !== 'human' || 
      needsColorChoice || 
      !!gameState.winner || 
      agentActionsQueue.length > 0 || 
      animatingAgentCards.length > 0;

    if (isHumanInteractionDisabled) {
      return; // Prevent action if interaction is disabled
    }
    
    const actionObj = gameState.legal_actions.find(action => action.action_str === card);
    if (actionObj) {
      playAction(actionObj.action_index, card);
    }
  };

  // Simple loading indicator
  if (loading && !gameState) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl font-medium">Loading...</div>
      </div>
    );
  }

  // --- Render Logic --- 
  const legalActionIndices = gameState?.legal_actions?.map(a => a.action_index) || [];

  // Determine if human interaction should be disabled
  const isHumanInteractionDisabled = 
    loading || 
    gameState?.current_player !== 'human' || 
    needsColorChoice || 
    !!gameState?.winner || 
    agentActionsQueue.length > 0 || 
    animatingAgentCards.length > 0;

  return (
    <div className="uno-game-container gap-1">
      <ThemeToggle />
      
      <header className="game-header">
        <h1 className="text-center">UNO AI Game</h1>
      </header>

      <div className="game-controls flex justify-center">
          {gameStarted ? (
            <div className="ingame-buttons flex gap-4 m-2">
              <Button onClick={startGame} disabled={loading} 
              variant="outline" 
              size="sm">
                New Game
              </Button>
              <Button 
                onClick={fetchGameState} 
                disabled={loading} 
                variant="outline" 
                size="sm"
                title="Force refresh game state"
              >
                🔄
              </Button>
            </div>
          ) : (
            <div className="start-game-container mt-4">
              <div className="start-game-controls">
                <div className="difficulty-selector">
                  <Button 
                    onClick={() => setDifficulty(1)}
                    variant={difficulty === 1 ? 'secondary' : 'outline'}
                    size="xl"
                    className="text-xl"
                  >
                    EASY
                  </Button>
                  <Button 
                    onClick={() => setDifficulty(2)}
                    variant={difficulty === 2 ? 'secondary' : 'outline'}
                    size="xl"
                    className="text-xl"                    
                  >
                    MEDIUM
                  </Button>
                  <Button 
                    onClick={() => setDifficulty(3)}
                    variant={difficulty === 3 ? 'secondary' : 'outline'}
                    size="xl"
                    className="text-xl"
                  >
                    HARD
                  </Button>
                </div>
              </div>
              <Button onClick={startGame} disabled={loading} className="start-game-button font-extrabold uppercase text-xl mt-6 text-justify" size="xl">
                  Start New Game
                </Button>
            </div>
          )}
        </div>
      {error && <div className="text-red-500 font-medium mt-2 text-center p-2">{error}</div>}
      
      {actionMessage && (
        <div className="action-message">
          {actionMessage}
        </div>
      )}

      {/* Game Area (now takes full width again) */} 
      {gameState && (
        <div className="game-table">
          {/* Winner Display */} 
          {gameState.winner && (
              <div className={`winner-message ${gameState.winner}`}>
                Game Over! Winner: {gameState.winner.toUpperCase()}
              </div>
          )}

          {/* Agent's Area (top) */}
          <div className="opponent-area">
            {/* Container now holds both info and cards */}
            <div className="opponent-cards-container">
              {/* Info moved inside */}
              <div className="opponent-info">
                <h2>Agent</h2>
                <span className="card-count">{gameState.agent_hand_size} cards</span>
              </div>
              {/* Card display area */}
              <div className="opponent-cards">
                {(() => {
                  const numCards = Math.min(gameState.agent_hand_size, 12);
                  const cardWidthRem = 5.5; // Must match CSS .opponent-card width
                  const overlapRem = 3; // How much cards overlap (increase for more overlap)
                  const visiblePartRem = cardWidthRem - overlapRem;
                  
                  const totalStackWidthRem = cardWidthRem + Math.max(0, numCards - 1) * visiblePartRem;
                  const startOffsetRem = -totalStackWidthRem / 2;

                  return Array.from({ length: numCards }).map((_, i) => {
                    const cardLeftRem = startOffsetRem + i * visiblePartRem;
                    const cardStyle = {
                      left: `calc(50% + ${cardLeftRem}rem)`,
                      zIndex: i
                    };
                    return (
                      <div 
                        key={`agent-card-${i}`} 
                        className="opponent-card"
                        style={cardStyle}
                      >
                        <div className="card-back"></div>
                      </div>
                    );
                  });
                })()}
              </div>
              {/* Card count indicator moved slightly */}
              {gameState.agent_hand_size > 12 && (
                <div className="opponent-card-count-indicator">
                  +{gameState.agent_hand_size - 12} more cards
                </div>
              )}
            </div>
          </div>

          {/* Game Board (center) */}
          <div className="game-board">
            {/* Turn Indicator moved to game board */}
            <div className="turn-indicator">
              <span className={gameState.current_player === 'human' ? 'text-primary' : 'text-uno-red'}>
                {getTurnIndicator()}
              </span>
            </div>
            
            {/* Current Color Indicator */}
            <div className={`color-indicator color-${gameState.current_color.toLowerCase()}`}>
              {gameState.current_color}
            </div>

            {/* Show processing indicator when loading state is true AFTER game has started */}
            {loading && gameStarted && (
              <div className="processing-indicator">
                Processing...
              </div>
            )}
            
            {/* Cards being played animations */}
            {animatingCard && (
              <div 
                className="card-playing-from-hand" 
                style={{ '--random-rotation': `${animatingCard.rotation}deg` }}
              >
                <UnoCard 
                  cardString={animatingCard.cardString} 
                  isPlayable={false}
                />
              </div>
            )}
            
            {animatingAgentCards.map((card, index) => (
              <div 
                key={`agent-playing-${index}-${card.cardString}`}
                className="card-playing-from-agent" 
                style={{ '--random-rotation': `${card.rotation}deg` }}
              >
                <UnoCard 
                  cardString={card.cardString} 
                  isPlayable={false}
                />
              </div>
            ))}
            
            {/* Discard Pile - Only show top card */}
            <div className="discard-pile-area">
              {gameState.discard_pile_top?.length > 0 && (
                <UnoCard 
                  key={`top-card-${gameState.top_card}`}
                  cardString={gameState.top_card || gameState.discard_pile_top[gameState.discard_pile_top.length - 1]} 
                  isPlayable={false}
                  className={animatingCard || animatingAgentCards.length > 0 ? "card-appearing-in-pile" : ""}
                  style={animatingCard || animatingAgentCards.length > 0 ? 
                    { '--random-rotation': `${animatingCard?.rotation || animatingAgentCards[0]?.rotation || 0}deg` } : {}}
                />
              )}
            </div>
            
            {/* Color Selection (shows when needed) */}
            {needsColorChoice && (
              <div className="color-chooser">
                <p>Choose a color for the Wild card:</p>
                <div className="color-chooser-buttons">
                  <Button onClick={() => chooseColor('r')} disabled={loading} variant="uno-red">Red</Button>
                  <Button onClick={() => chooseColor('g')} disabled={loading} variant="uno-green">Green</Button>
                  <Button onClick={() => chooseColor('b')} disabled={loading} variant="uno-blue">Blue</Button>
                  <Button onClick={() => chooseColor('y')} disabled={loading} variant="uno-yellow">Yellow</Button>
                </div>
              </div>
            )}
          </div>

          {/* Player's Hand */}
          <div className="player-area">
            <h3 className="mb-2">
              Your hand: {gameState?.player_hand?.length > 0 
                ? `${gameState.player_hand.length} card${gameState.player_hand.length > 1 ? 's' : ''}` 
                : '(0 cards)'}
            </h3>
            
            <div className="hand-container">
              {loading && !gameState.player_hand ? (
                <div className="loading-message">Loading...</div>
              ) : gameState?.player_hand?.length > 0 ? (
                <div className="hand player-hand">
                  {gameState.player_hand.map((card, index) => {
                    // isPlayable is purely about game rules now
                    const isPlayable = gameState.legal_actions.some(action => action.action_str === card);
                    
                    return (
                      <UnoCard 
                        key={`${card}-${index}`} 
                        cardString={card} 
                        // Pass both rule-based playability and overall interaction state
                        isPlayable={!isHumanInteractionDisabled && isPlayable} 
                        disabled={isHumanInteractionDisabled} // Pass the combined disabled flag
                        onClick={() => handleCardClick(card)}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="empty-hand-message">No cards in hand</div>
              )}
              
              {/* Draw Card Button */}
              {gameState?.current_player === 'human' && 
               gameState?.legal_actions?.some(action => action.action_str === 'draw_card') && 
               !needsColorChoice && // Keep this check specific to draw button visibility 
               !gameState.winner && (
                <div className="draw-card-button">
                  <Button 
                    onClick={() => playAction(gameState.legal_actions.find(a => a.action_str === 'draw_card').action_index, "draw_card")}
                    // Disable based on the combined flag
                    disabled={isHumanInteractionDisabled}
                    className="draw-button"
                  >
                    Draw Card
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )} {/* End of gameState check for game-table */}

      {/* Floating Log Panel (conditionally rendered) */}
      {gameStarted && isLogVisible && ( 
        <div className="agent-log-panel floating">
          <h3 className="log-title">Agent's Last Turn Actions</h3>
          <div className="log-entries">
            {agentTurnLog.length > 0 ? (
              agentTurnLog.map((entry, index) => (
                <div key={index} className="log-entry">
                  {entry}
                </div>
              ))
            ) : (
              <div className="log-entry placeholder">No actions logged yet.</div>
            )}
          </div>
        </div>
      )}

      {/* Floating Log Toggle Button */}
      {gameStarted && (
        <Button
          variant="outline"
          size="icon"
          className="log-toggle-button"
          onClick={() => setIsLogVisible(!isLogVisible)}
          title={isLogVisible ? "Hide Agent Log" : "Show Agent Log"}
        >
          {/* Replace with an actual icon later if possible (e.g., from lucide-react) */}
          {isLogVisible ? '📜' : '📄'} 
        </Button>
      )}

    </div> // End of uno-game-container
  );
}

export default App;