
class Square:

    ALPHACOLS = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}

    def __init__(self, row, col, piece=None):
        self.row = row
        self.col = col
        self.piece = piece
        self.alphacol = self.ALPHACOLS.get(col, '?')

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def has_piece(self):
        return self.piece != None

    def isempty(self):
        return not self.has_piece()

    def has_boulder(self):
        return self.has_piece() and self.piece.name == 'boulder'

    def has_team_piece(self, color):
        """Boulder is treated as friendly by both sides."""
        if self.has_boulder():
            return True
        return self.has_piece() and self.piece.color == color

    def has_enemy_piece(self, color):
        """Return True if this square holds a piece of the opposite color
        (and is not the boulder, which is neutral).

        This is the broad "is there an enemy here" test — it does NOT
        consult capturability. An invulnerable enemy still counts as an
        enemy here, because it still occupies the square and can still
        threaten / move from it. Use this for queries about presence and
        threat (e.g. the bishop's teleport safety check needs to see
        invulnerable enemies' threats even though it can't capture them).

        Use `has_capturable_enemy_piece` instead when the question is
        "can I capture the piece on this square right now?".
        """
        if self.has_boulder():
            return False
        return self.has_piece() and self.piece.color != color

    def has_capturable_enemy_piece(self, color):
        """Return True if this square holds a piece of the opposite color
        that can actually be captured right now.

        Like `has_enemy_piece`, but additionally returns False when the
        enemy piece is marked invulnerable (the invulnerable-manipulation
        variants, or a v2 knight that just gained invulnerability after a
        non-capture jump). Use this when generating capture moves or
        deciding whether a square is a valid attack target.
        """
        if self.has_boulder():
            return False
        if self.has_piece() and self.piece.invulnerable:
            return False
        return self.has_piece() and self.piece.color != color

    def isempty_or_enemy(self, color):
        """True if the square is empty OR holds a capturable enemy piece.

        Used by move generators (rook, queen, knight, etc.) to decide
        "can I move here?" — the answer must be yes only when the square
        is either vacant or contains an enemy we can take. Invulnerable
        enemies are excluded for this purpose.
        """
        return self.isempty() or self.has_capturable_enemy_piece(color)

    @staticmethod
    def in_range(*args):
        for arg in args:
            if arg < 0 or arg > 7:
                return False
        
        return True

    @staticmethod
    def get_alphacol(col):
        ALPHACOLS = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
        return ALPHACOLS[col]