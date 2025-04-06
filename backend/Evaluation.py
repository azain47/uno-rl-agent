import tqdm
def evaluate_agent(game_class, agent, d_agent, num_episodes=100):
    wins = 0
    total_steps = 0
    total_cards_drawn = 0
    
    for episode in tqdm(range(num_episodes)):
        game = game_class()
        state, player_idx = game.init_game()
        cards_drawn = 0
        steps = 0
        
        while not game.game_over():
            if player_idx == 0:
                legal_actions = state['legal_actions']
                action = agent.select_action(state, legal_actions)
                if action == 60:
                    cards_drawn += 1
                next_state, next_player_idx = game.step(action)
                state = next_state
                player_idx = next_player_idx
                steps += 1
            else:
                legal_actions = state['legal_actions']
                ac = d_agent.select_action(state, legal_actions)
                next_state, next_player_idx = game.step(ac)
                state = next_state
                player_idx = next_player_idx
        
        if game.get_winner() and game.get_winner().name == "You":
            wins += 1
        
        total_steps += steps
        total_cards_drawn += cards_drawn
    
    win_rate = wins / num_episodes
    avg_steps = total_steps / num_episodes
    avg_cards_drawn = total_cards_drawn / num_episodes
    
    print("Evaluation Results:")
    print(f"Win Rate: {win_rate:.2f}")
    print(f"Average Steps: {avg_steps:.2f}")
    print(f"Average Cards Drawn: {avg_cards_drawn:.2f}")
    
    return win_rate, avg_steps, avg_cards_drawn
