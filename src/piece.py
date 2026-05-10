import os

class Piece:

    def __init__(self, name, color, value, texture=None, texture_rect=None):
        self.name = name
        self.color = color
        value_sign = 1 if color == 'white' else -1
        self.value = value * value_sign
        self.is_royal = False
        self.is_transformed = False
        self.line_of_sight = []
        self.threat_squares = []
        self.moves = []
        self.moved = False
        self.forbidden_square = None  # (row, col) tuple — square piece cannot return to after manipulation (v0/original)
        self.forbidden_zone = None   # list of (row, col) — squares piece cannot move to (exclusion_zone variant)
        self.moved_by_queen = False  # True if piece was moved by queen manipulation and cannot make a spatial move on its immediate next turn (v2/freeze)
        self.frozen = False          # alias kept for variant infrastructure (engine.py manipulation_mode); v2 game uses moved_by_queen
        self.invulnerable = False    # True if piece cannot be captured by enemies (freeze_invulnerable variants)
        self.bastion_active = False  # v2 knight: True for one opponent turn after a knight jump where the jumped piece survives; uncapturable while True
        self.texture = texture
        self.set_texture()
        self.texture_rect = texture_rect

    def set_texture(self, size=80):
        self.texture = os.path.join(
            f'assets/images/imgs-{size}px/{self.color}_{self.name}.png')

    def add_move(self, move):
        # Skip moves to the forbidden square (set by queen manipulation — original variant)
        if self.forbidden_square:
            fr, fc = self.forbidden_square
            if move.final.row == fr and move.final.col == fc:
                return
        # Skip moves to any square in the forbidden zone (exclusion_zone variant)
        if self.forbidden_zone:
            dest = (move.final.row, move.final.col)
            if dest in self.forbidden_zone:
                return
        self.moves.append(move)

    def clear_moves(self):
        self.moves = []

class Pawn(Piece):

    def __init__(self, color):
        self.dir = -1 if color == 'white' else 1
        self.en_passant = False
        super().__init__('pawn', color, 1.0)

class Knight(Piece):

    def __init__(self, color):
        super().__init__('knight', color, 3.0)

class Bishop(Piece):

    def __init__(self, color):
        self.assassin_squares = []
        super().__init__('bishop', color, 3.001)

class Rook(Piece):

    def __init__(self, color):
        super().__init__('rook', color, 5.0)

class Queen(Piece):

    def __init__(self, color, is_royal=True):
        super().__init__('queen', color, 9.0)
        self.is_royal = is_royal

class Boulder(Piece):

    def __init__(self):
        self.cooldown = 0
        self.last_square = None
        self.first_move = True
        self.on_intersection = False
        super().__init__('boulder', 'none', 0)

    def set_texture(self, size=80):
        self.texture = os.path.join(
            f'assets/images/imgs-{size}px/boulder.png')

class King(Piece):

    def __init__(self, color):
        self.left_rook = None
        self.right_rook = None
        super().__init__('king', color, 10000.0)
        self.is_royal = True