import random, json
from player import Player
from utils import card_to_action, build_deck, deal_initial_cards, start_card, card_to_str

WILD = ['r-wild', 'g-wild', 'b-wild', 'y-wild']

WILD_DRAW_4 = ['r-wild_draw_4', 'g-wild_draw_4', 'b-wild_draw_4', 'y-wild_draw_4']
class UNOGame:
    def __init__(self, num_players=2):
        with open("./action_space.json") as f:
            self.action_space = json.load(f)

        self.index_to_action = {v: k for k, v in self.action_space.items()}
        self.players = [Player("You")] + [Player(f"Bot {idx + 1}") for idx in range(num_players - 1)]
        self.deck = build_deck()
        random.shuffle(self.deck)
        self.discard_pile = []
        self.current_color = None
        self.direction = 1  
        self.current_player_index = 0
        self.skip_next = False 
        deal_initial_cards(self)
        start_card(self)

    def get_actionSpace(self):
        return self.action_space
    
    def get_player_list(self):
        return list(self.players)
        
    def draw_cards(self, player, num=1):
        for _ in range(num):
            if not self.deck:
                if len(self.discard_pile) > 1:  # Keep at least 1 card for gameplay
                    top_card = self.discard_pile.pop()
                    self.deck = self.discard_pile
                    random.shuffle(self.deck)
                    self.discard_pile = [top_card]
                else:
                    #print("No cards")
                    return
            player.add_card(self.deck.pop())


    def apply_card_effect(self, card):
        """
        Applies special effects:
            - Skip: next player loses their turn.
            - Reverse: reverses turn order (or acts as skip in 2-player game).
            - Draw Two: next player draws 2 cards and loses turn.
            - Wild Draw Four: next player draws 4 cards and loses turn.
        """
        card_val = card.trait.lower()
        if card_val == "skip":
            self.skip_next = True
        elif card_val == "reverse":
            self.direction *= -1
            if len(self.players) == 2:
                self.skip_next = True
        elif card_val == "draw_2":
            next_index = (self.current_player_index + self.direction) % len(self.players)
            self.draw_cards(self.players[next_index], 2)
            self.skip_next = True
        elif card_val == "wild_draw_4":
            next_index = (self.current_player_index + self.direction) % len(self.players)
            self.draw_cards(self.players[next_index], 4)
            self.skip_next = True

    def play_card(self, player, card, chosen_color=None):
        """
        Processes playing a card:
          - Removes it from hand.
          - Updates discard pile and current color.
          - Applies any special effects.
        """
        player.remove_card(card)
        self.discard_pile.append(card)
        if card.type == "wild":
            self.current_color = chosen_color
        else:
            self.current_color = card.color
        self.apply_card_effect(card)

    def is_valid_move(self, card):
        """
        Checks if a card is playable given the top card and current active color.
        """
        top_card = self.discard_pile[-1]
        if card.type == "wild":
            return True
        return card.color == self.current_color or card.trait == top_card.trait

    def game_over(self):
        """
        Checks if any player has won.
        """
        return any(player.has_won() for player in self.players)

    def get_winner(self):
        """
        Returns the winning player.
        """
        for player in self.players:
            if player.has_won():
                return player
        return None

    def get_state_for_player(self, index):
        """
        Returns the state for the player as a dictionary:
          - 'target': top card's action string.
          - 'hand': list of action strings representing player's hand (for human).
          - 'legal_actions': list of legal action indices (from action_space mapping).
        """
        state = {}
        state['target'] = card_to_str(self, self.discard_pile[-1])
        # if index == 0:
        state['hand'] = [card_to_str(self, card) for card in self.players[index].hand]
        # else:
        #     state['hand'] = []

        state['opponent_hand_sizes'] = []
        for i, player in enumerate(self.players):
            if i != index:  # Skip the current player
                state['opponent_hand_sizes'].append(len(player.hand))

        # Always include draw_card as a legal action
        legal = [self.action_space["draw_card"]]

        current_player = self.players[index]
        for card in current_player.hand:
            if card.is_playable_on(self.discard_pile[-1], self.current_color):
                if card.type != "wild":
                    act = card_to_action(card)
                    if act in self.action_space:
                        legal.append(self.action_space[act])
                elif card.trait == 'wild_draw_4':
                    for card in WILD_DRAW_4:
                        legal.append(self.action_space[card])
                else:
                    for card in WILD:
                        legal.append(self.action_space[card])
                        
        state['legal_actions'] = legal
        return state

    def init_game(self):
        """
        Returns the initial state and current player index.
        """
        return self.get_state_for_player(self.current_player_index), self.current_player_index

    def step(self, action, return_drawn_card=False):
        """
        Processes an action given as an integer.
        Converts the index to its corresponding action string.
        - If the action corresponds to "draw", the player draws one card.
        - Otherwise, maps the action string to a card in hand.
        Advances turn taking into account special effects.
        Returns the updated state and new current player index.
        """
        current_player = self.players[self.current_player_index]
        action_str = self.index_to_action[action]
        drawn_card = None
        
        if action_str == "draw_card":
            if not self.deck:
                if len(self.discard_pile) > 1:  # Keep at least 1 card for gameplay
                    top_card = self.discard_pile.pop()
                    self.deck = self.discard_pile
                    random.shuffle(self.deck)
                    self.discard_pile = [top_card]
            
            if self.deck:  # If there are still cards in the deck
                drawn_card = self.deck.pop()
                current_player.add_card(drawn_card)
                
        else:
            selected_card = None
            chosen_color = None
            for card in current_player.hand:
                if card.type != "wild":
                    if card_to_action(card) == action_str:
                        selected_card = card
                        break
                elif card.trait == 'wild':
                    if action_str in WILD:
                        selected_card = card
                        chosen_color = action_str[0]
                        break
                else:  # wild_draw_4
                    if action_str in WILD_DRAW_4:
                        selected_card = card
                        chosen_color = action_str[0]
                        break
            
            if selected_card and self.is_valid_move(selected_card):
                self.play_card(current_player, selected_card, chosen_color)
            else:
                # If selected card is invalid, default to drawing a card
                if self.deck:
                    drawn_card = self.deck.pop()
                    current_player.add_card(drawn_card)

        # Advance turn
        if self.skip_next:
            self.current_player_index = (self.current_player_index + 2 * self.direction) % len(self.players)
            self.skip_next = False
        else:
            self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
        
        state = self.get_state_for_player(self.current_player_index)
        
        # Add drawn card to state if requested
        if return_drawn_card and drawn_card:
            state['drawn_card'] = card_to_str(self, drawn_card)
        
        return state, self.current_player_index

    def is_card_playable(self, card_str):
        """
        Checks if a card string is playable on the current discard pile.
        Used to determine if a drawn card can be immediately played.
        """
        top_card = self.discard_pile[-1]
        
        # Handle wild cards
        if "wild" in card_str:
            return True
        
        card_parts = card_str.split('-')
        card_color = card_parts[0]
        card_value = card_parts[1] if len(card_parts) > 1 else None
        
        # Check if color or value matches
        return (card_color == self.current_color or 
                (card_value and card_value == top_card.trait))