class Player:
    def __init__(self, name):
        """
        Initialize a player with a name and an empty hand.
        """
        self.name = name
        self.hand = []

    def add_card(self, card):
        """
        Adds a card to the player's hand.
        """
        self.hand.append(card)

    def remove_card(self, card):
        """
        Removes a card from the player's hand.
        """
        self.hand.remove(card)

    def has_won(self):
        """
        Checks if the player has emptied their hand.
        """
        return len(self.hand) == 0

    def __str__(self):
        return f"{self.name}: {self.hand}"
