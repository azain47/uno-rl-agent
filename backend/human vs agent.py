import time
import random
from termcolor import colored

from game_logic import UNOGame
from network import DQNAgent, UnoEnvironment
from utils import colorize_card_strings

class HumanVsAgentInterface:
    def __init__(self, agent_model_path="./checkpoints/uno_model_16000.pt"):
        print("\n\n")
        print("=" * 60)
        print("WELCOME TO UNO: HUMAN VS AI".center(60))
        time.sleep(3)
        print("=" * 60 + "\n")
        print("Select Agent difficulty:")
        print("  1: Easy")
        print("  2: Medium")
        print("  3: Hard")
        
        self.difficulty = 2

        while True:
            diffNumber = input("Enter difficulty (1-3): ")
            if diffNumber.isnumeric():
                diffNumber = int(diffNumber)
                if diffNumber > 0 and diffNumber < 4:
                    self.difficulty = diffNumber
                break
            else:
                print("select a valid difficulty")
        
        self.num_players = 2
        self.game = UnoEnvironment()
        self.game_players = self.game.game.players
        
        self.colors_list = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan']
        self.agent_color = random.choice(self.colors_list)
        
        self.state = self.game.reset()
        self.player = 0
        self.discard_pile = []
        
        self.agent = self.load_agent(agent_model_path)
        self.difficulty_scaler = None

        self.game_players[0].name = "You"
        self.game_players[1].name = "Agent"
        
        self.color_mappings = {'r': "Red", 'g': "Green", 'b': "Blue", 'y': "Yellow"}
    
    def load_agent(self, model_path):
        print("Loading AI agent...")
        agent = DQNAgent(19 + 4 + (19 * 7) + 3 + 1 + 1, 61, self.game)
        agent.load_model(model_path)
        print(f"Successfully loaded agent from {model_path}")
        agent.epsilon = 0.05
        exec(agent.difficulty_scaler,globals())
        return agent

    def show_game_state(self):
        print("\n" + "=" * 60)
        print(colored(f"Agent Hand Size: {len(self.game.game.players[1].hand)}", self.agent_color))
        current_player_name = "You" if self.player == 0 else colored("Agent", self.agent_color)
        print(f"Current Player: {current_player_name}")
        
        if self.player == 0:
            top_card = self.state['target']
            if self.discard_pile:
                print(f"\nLast {min(4, len(self.discard_pile))} actions:")
                for i in range(min(4, len(self.discard_pile))):
                    print(f"  - {colorize_card_strings(self.discard_pile[-i-1])}")

            print(f"\nTop Card: {colorize_card_strings(top_card)}")
            print(f"Current Color: {self.color_mappings.get(self.game.game.current_color, 'Wild')}")
            print(f"\nYour Hand ({len(self.state['hand'])}):")
            for i, card in enumerate(sorted(self.state['hand'])):
                print(f"  {i+1}: {colorize_card_strings(card)}")

    def update_hand_sizes(self):
        agent_hand_size = len(self.game.game.players[1].hand)
        your_hand_size = len(self.game.game.players[0].hand)
        
        print("\nCurrent hand sizes:")
        print(f"  You: {your_hand_size}")
        print(colored(f"  Agent: {agent_hand_size}", self.agent_color))
        print()

    def handle_wild_card_selection(self, is_draw_4=False):
        colors = {'1': 'r', '2': 'g', '3': 'b', '4': 'y'}
        print("\nChoose a color:")
        print("  1: Red")
        print("  2: Green")
        print("  3: Blue")
        print("  4: Yellow")
        
        while True:
            color_choice = input("Color number: ")
            if color_choice in colors:
                new_color = colors[color_choice]
                card_type = "wild_draw_4" if is_draw_4 else "wild"
                new_action_str = f"{new_color}-{card_type}"
                return self.game.game.action_space[new_action_str]
            else:
                print("Invalid color choice. Please choose 1-4.")

    def human_turn(self):
        while True:
            try:
                print("\nLegal actions:")
                for i, action_index in enumerate(self.state['legal_actions']):
                    action_str = self.game.game.index_to_action[action_index]
                    print(f"  {i + 1}: {colorize_card_strings(action_str)}")
                
                choice = input("\nChoose action number: ")
                index = int(choice) - 1
                
                if 0 <= index < len(self.state['legal_actions']):
                    selected_action = self.state['legal_actions'][index]
                    action_str = self.game.game.index_to_action[selected_action]
                    
                    if action_str == "draw_card":
                        return self.handle_draw_card(selected_action)
                    
                    if "wild" in action_str:
                        is_draw_4 = "draw_4" in action_str
                        return self.handle_wild_card_selection(is_draw_4)
                    
                    return selected_action
                
                raise IndexError
            except (ValueError, IndexError):
                print(f"Please enter a number between 1 and {len(self.state['legal_actions'])}")

    def handle_draw_card(self, selected_action):
        next_state, _, _, next_player = self.game.step(selected_action, return_drawn_card=True)
        drawn_card = next_state.get('drawn_card')
        
        if drawn_card:
            print(f"\nYou drew: {colorize_card_strings(drawn_card)}")
            
            if self.game.game.is_card_playable(drawn_card):
                play_choice = input("Would you like to play this card? (y/n): ").lower()
                if play_choice == 'y':
                    if "wild" in drawn_card:
                        is_draw_4 = "draw_4" in drawn_card
                        play_action = self.handle_wild_card_selection(is_draw_4)
                    else:
                        play_action = self.game.game.action_space[drawn_card]
                        time.sleep(1)
    
                    self.discard_pile.append("draw_card")
                    play_action_str = self.game.game.index_to_action[play_action]
                    self.discard_pile.append(play_action_str)
                    
                    self.state, _, _, self.player = self.game.step(play_action)
                    return play_action
                else:
                    print("You chose not to play the drawn card. Turn passes to the agent.")
            else:
                print("The drawn card cannot be played. Turn passes to the agent.")
        else:
            print("No cards left to draw. Turn passes to the agent.")
        
        self.state = next_state
        self.player = next_player
        return selected_action

    def agent_turn(self):
        print(colored("Agent is thinking", self.agent_color), end="")
        for _ in range(random.randrange(3,6)):
            time.sleep(0.3)
            print(".", end="", flush=True)
        print()
        ac = difficulty_scaler(self.state, self.discard_pile, self.game.game.index_to_action, self.difficulty)
        if ac is None:
            legal_actions = self.state['legal_actions']
            action = self.agent.select_action(self.state, legal_actions)
            action_str = self.game.game.index_to_action[action]         
        else:
            action_str = ac['selected_card']
            action = self.game.game.action_space[action_str]
        if action_str == "draw_card":
            if self.game.game.deck:
                drawn_card_obj = self.game.game.deck[-1]
                drawn_card = drawn_card_obj.color + "-" + drawn_card_obj.trait
                print(colored(f"Agent will draw a card", self.agent_color))
                if self.game.game.is_card_playable(drawn_card):
                    if random.random() > 0.5:
                        print(colored(f"Agent might play the drawn card", self.agent_color))
        
        print(colored(f"Agent plays: {colorize_card_strings(action_str)}", self.agent_color))
        time.sleep(2)
        
        return action

    def handle_special_card(self, action_str):
        if "draw_2" in action_str:
            if self.player == 0:
                print(colored(f"\nYou played Draw 2! Agent draws 2 cards.", "yellow"))
            else:
                print(colored(f"\nAgent played Draw 2! You draw 2 cards.", self.agent_color))
            time.sleep(1)
            self.update_hand_sizes()
        elif "wild_draw_4" in action_str:
            if self.player == 0:
                print(colored(f"\nYou played Wild Draw 4! Agent draws 4 cards.", "yellow"))
            else:
                print(colored(f"\nAgent played Wild Draw 4! You draw 4 cards.", self.agent_color))
            time.sleep(1)
            self.update_hand_sizes()

    def run(self):
        print("\nGame starting - You go first!")
        
        while not self.game.game.game_over():
            your_hand_size_before = len(self.game.game.players[0].hand)
            agent_hand_size_before = len(self.game.game.players[1].hand)
            
            if self.player == 0: 
                self.show_game_state()
                action = self.human_turn()
                action_str = self.game.game.index_to_action[action]
                
                if action_str != "draw_card":
                    self.state, _, _, self.player = self.game.step(action)
                
                self.handle_special_card(action_str)
                
                if action_str != "draw_card" and "drawn_card" not in self.state:
                    self.discard_pile.append(action_str)
            else:  
                self.show_game_state()
                action = self.agent_turn()
                
                self.state, _, _, self.player = self.game.step(action)
                
                action_str = self.game.game.index_to_action[action]
                
                self.handle_special_card(action_str)
                
                if action_str != "draw_card" or "drawn_card" not in self.state:
                    self.discard_pile.append(action_str)
        
            # if len(self.discard_pile) > 8:
            #     self.discard_pile.pop(0)
            
            self.show_hand_size_changes(your_hand_size_before, agent_hand_size_before)
        
        self.show_game_result()

    def show_hand_size_changes(self, your_hand_size_before, agent_hand_size_before):
        your_hand_size_after = len(self.game.game.players[0].hand)
        agent_hand_size_after = len(self.game.game.players[1].hand)
        
        if ((your_hand_size_before != your_hand_size_after and abs(your_hand_size_after - your_hand_size_before) > 1) or 
            (agent_hand_size_before != agent_hand_size_after and abs(agent_hand_size_after - agent_hand_size_before) > 1)):
            print("\nHand size changes:")
            if your_hand_size_before != your_hand_size_after and abs(your_hand_size_after - your_hand_size_before) > 1:
                print(f"  Your hand: {your_hand_size_before} → {your_hand_size_after}")
            if agent_hand_size_before != agent_hand_size_after and abs(agent_hand_size_after - agent_hand_size_before) > 1:
                print(colored(f"  Agent's hand: {agent_hand_size_before} → {agent_hand_size_after}", self.agent_color))
            print()

    def show_game_result(self):
        winner = self.game.game.get_winner()
        print("\n" + "=" * 60)
        if winner.name == "You":
            print("CONGRATULATIONS! YOU WIN!".center(60))
        else:
            print(colored("THE AI AGENT WINS!", self.agent_color).center(60))
        print("=" * 60)
        
        print(f"\nFinal hand sizes:")
        print(f"  You: {len(self.game.game.players[0].hand)}")
        print(colored(f"  Agent: {len(self.game.game.players[1].hand)}", self.agent_color))
        
        play_again = input("\nWould you like to play again? (y/n): ").lower()
        if play_again == 'y':
            self.__init__()
            self.run()
        else:
            print("\nThank you for playing UNO against the AI!")

if __name__ == "__main__":
    HumanVsAgentInterface().run()