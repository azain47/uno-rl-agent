from game_logic import UNOGame
import numpy as np
from termcolor import colored
from utils import colorize_card_strings
import time

class UnoInterface:
    def __init__(self):
        print("\n" + "=" * 40)
        print()
        while True:
            self.num_players = int(input("Enter the Number of Players in the Game:"))
            try:
                assert self.num_players <= 15, "Number of players must be lesser than 15"
                break
            except AssertionError:
                print(f"Please enter a number between 2 and 15")
        self.game = UNOGame(self.num_players)
        # returns a reference to player object and not a copy
        self.game_players = self.game.get_player_list()
        self.state, self.player = self.game.init_game()
        self.colors_list = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan','dark_grey', 'light_green','light_magenta', 'light_cyan']
        self.bot_colors = np.random.choice(self.colors_list,self.num_players, replace = True if self.num_players > len(self.colors_list) else False)
        self.discard_pile = []

    def show_game_state(self, bot_id = 0):
        """
        Displays game state:
          - Bot's hand size.
          - Current player.
          - (For human) the top card, recent actions, and current hand.
        """
        mapping = {'r': "Red", 'g': "Green", 'b': "Blue", 'y': "Yellow"}
        print("\n" + "=" * 40)
        for idx, bot in enumerate(self.game_players[1:]):
            print(colored(f"Bot {idx + 1} Hand Size: {len(bot.hand)}", self.bot_colors[idx]))

        print(f"Current Player: {'You' if self.player == 0 else colored(f'Bot {bot_id}', self.bot_colors[int(bot_id) - 1])}")
        if self.player == 0:
            top_card = self.state['target']
            print(f"Last {self.num_players * 2} actions:", ','.join([colorize_card_strings(act) for act in self.discard_pile[-self.num_players*2:]]))
            print()
            print(f"Top Card: {colorize_card_strings(top_card)}")
            print()
            print(f"Top Color: {mapping[self.game.current_color]}") #for debug
            print(f"Your Hand ({len(self.state['hand'])}):", ', '.join([colorize_card_strings(card) for card in self.state['hand']]))

    def human_turn(self):
        """ 
        Prompts the human to select an action.
        Legal actions are now discrete indices which are converted to action strings for display.
        """
        while True:
            try:
                print("\nLegal actions:")
                for i, action_index in enumerate(self.state['legal_actions']):
                    action_str = self.game.index_to_action[action_index]
                    print(f"{i + 1}: {colorize_card_strings(action_str)}")
                choice = input("Action number: ")
                index = int(choice) - 1
                if 0 <= index < len(self.state['legal_actions']):
                    return self.state['legal_actions'][index]
                raise IndexError
            except (ValueError, IndexError):
                print(f"Please enter a number between 1 and {len(self.state['legal_actions'])}")

    def bot_turn(self, bot_id):
        """
        Chooses a random legal action for the Bot.
        """
        action_index = np.random.choice(self.state['legal_actions'])
        action_str = self.game.index_to_action[action_index]
        colors = ['r','g','b', 'y']
        if "wild" in action_str:
            if action_str.split('-')[0] not in colors:
                new_prefix = np.random.choice(list(colors))
                action_str = f"{new_prefix}-{action_str.split('-')[-1]}"
                action_index = self.game.action_space[action_str]
        print(f"{colored(f'Bot {bot_id} Plays:', self.bot_colors[int(bot_id) - 1])} {colorize_card_strings(action_str)}")
        return action_index

    def run(self):
        """
        Runs the game loop until a winner is determined.
        """
        print(" UNO GAME ".center(40, '='))
        while not self.game.game_over():
            if self.game.players[self.player].name == "You":
                self.show_game_state()
                action = self.human_turn()
            else:
                self.show_game_state(self.game.players[self.player].name[4:])
                action = self.bot_turn(self.game.players[self.player].name[4:])
                # random sleeping for more readable console logs
                time.sleep(np.random.random() * 2 + 1)
                
            # stack and discard pile are the same for some reason..
            self.discard_pile.append(self.game.index_to_action[action])
            if len(self.discard_pile) > self.num_players * 2:
                self.discard_pile.pop(0)
            self.state, self.player = self.game.step(action)
             
        winner = self.game.get_winner()
        print(f"\nWinner: {winner.name}!")

if __name__ == "__main__":
    UnoInterface().run()
