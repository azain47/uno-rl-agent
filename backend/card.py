class UnoCard:
    info = {'type':  ['number', 'action', 'wild'],
            'color': ['r', 'g', 'b', 'y'],
            'trait': ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                      'skip', 'reverse', 'draw_2', 'wild', 'wild_draw_4']
            }

    def __init__(self, card_type, color, trait):
        ''' Initialize the class of UnoCard

        Args:
            card_type (str): The type of card
            color (str): The color of card
            trait (str): The trait of card
        '''
        self.type = card_type
        self.color = color
        self.trait = trait
        self.str = self.get_str()

    def is_playable_on(self, top_card, current_color):
        """
          - wild card (always playable), or
          - If card color matches the current color, or
          - Its value matches the top card's value.
        """
        if self.type == "wild":
            return True
        return (self.color == current_color) or (self.trait == top_card.trait)
    
    def get_str(self):
        ''' Get the string representation of card
        Return:
            (str): The string of card's color and trait
        '''
        return self.color + '-' + self.trait
