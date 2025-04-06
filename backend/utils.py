import random
from termcolor import colored
from card import UnoCard
import os

COLOR_MAP = {'r': 0, 'g': 1, 'b': 2, 'y': 3}

# a map of trait to its index
TRAIT_MAP = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
             '8': 8, '9': 9, 'skip': 10, 'reverse': 11, 'draw_2': 12,
             'wild': 13, 'wild_draw_4': 14}

WILD = ['r-wild', 'g-wild', 'b-wild', 'y-wild']

WILD_DRAW_4 = ['r-wild_draw_4', 'g-wild_draw_4', 'b-wild_draw_4', 'y-wild_draw_4']

def colorize_card_strings(card_str: str) -> str:
    """
    Colors an action string using termcolor.
    Expected format: "r-5", "r-draw_2", "r-wild_draw_4", etc.
    """
    colors = {'r': 'red', 'g': 'green', 'b': 'blue', 'y': 'yellow'}
    if '-' in card_str:
        prefix, trait = card_str.split('-', 1)
        # Uppercase the trait and replace underscores with spaces
        return colored(trait.upper().replace('_', ' '), colors.get(prefix, 'white'))
    return card_str

def build_deck():
    ''' Generate uno deck of 108 cards
    '''
    deck = []
    card_info = UnoCard.info
    for color in card_info['color']:

        # init number cards
        for num in card_info['trait'][:10]:
            deck.append(UnoCard('number', color, num))
            if num != '0':
                deck.append(UnoCard('number', color, num))

        # init action cards
        for action in card_info['trait'][10:13]:
            deck.append(UnoCard('action', color, action))
            deck.append(UnoCard('action', color, action))

        # init wild cards
        for wild in card_info['trait'][-2:]:
            deck.append(UnoCard('wild', color, wild))
    return deck

def deal_initial_cards(game) -> None:
    """
    Deals 7 cards to each player in the game.
    """
    for _ in range(7):
        for player in game.players:
            player.add_card(game.deck.pop())


def card_to_str(game, card: UnoCard) -> str:
    """
    Converts a UnoCard object to a human-readable string for display.
    - For non-wild cards, returns: "<color>-<trait>", e.g., "r-5", "b-draw_2".
    - For wild cards, if the game has a current_color, uses it; otherwise "wild".
    """

    return card.get_str()

def card_to_action(card: UnoCard, chosen_color: str = None) -> str:
    """
    Converts a UnoCard into its corresponding action string for indexing in action_space.
      - For non-wild cards: "<color>-<trait>".
      - For wild cards: "<chosen_color>-<trait>" (must supply chosen_color).
    Returns None if chosen_color is not provided for a wild card.
    """
    if card.type != "wild":
        return card.get_str()

def wild_actions(card: UnoCard) -> list[str]:
    """
    For a wild card, returns all possible action strings using each color option.
    """
    return [f"{c}-{card.trait}" for c in ["r", "g", "b", "y"]]

def start_card(game) -> None:
    """
    Picks the starting card for the discard pile ensuring it is a legal starter.
    In this version, we avoid starting with a wild draw 4 card.
    """
    while True:
        card = game.deck.pop()
        if not (card.type == "wild" or card.type == 'action'):
            game.discard_pile.append(card)
            game.current_color = card.color
            break
        else:
            game.deck.insert(0, card)
            random.shuffle(game.deck)


    