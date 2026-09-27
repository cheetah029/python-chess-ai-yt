
class Square:
    """One board square.

    CONSTRUCTED CONSTANTLY, which is why this is written the way it is.
    A single legal-move generation builds about 900 of these -- the
    threat map and the lines of sight allocate one per square they
    cover -- and compares them about four thousand times. At roughly a
    millisecond per generation, and a Monte-Carlo rollout being a few
    hundred generations, that cost is what decides whether a search
    whose objective is the win condition is affordable at all (#231).

    `__slots__` removes the per-instance dict. `alphacol` was computed
    and stored on every construction and is read by nothing outside
    this file -- the board labels use the `get_alphacol` classmethod --
    so it is a property now and costs nothing until someone asks.
    """

    __slots__ = ('row', 'col', 'piece')

    ALPHACOLS = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}

    def __init__(self, row, col, piece=None):
        self.row = row
        self.col = col
        self.piece = piece

    @property
    def alphacol(self):
        return self.ALPHACOLS.get(self.col, '?')

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __hash__(self):
        return self.row * 8 + self.col

    # THE FOUR HOTTEST PREDICATES IN THE ENGINE, written flat on
    # purpose. One legal-move generation asks these several thousand
    # times, and each used to cost two or three nested Python calls:
    # `has_enemy_piece` called `has_boulder`, which called `has_piece`,
    # which compared `self.piece != None` -- a full rich-comparison
    # protocol where `is not None` is a pointer test. None of the
    # meanings change; the boulder is still friendly to both sides and
    # still never an enemy (#231).

    def has_piece(self):
        return self.piece is not None

    def isempty(self):
        return self.piece is None

    def has_boulder(self):
        piece = self.piece
        return piece is not None and piece.name == 'boulder'

    def has_team_piece(self, color):
        """Boulder is treated as friendly by both sides."""
        piece = self.piece
        if piece is None:
            return False
        return piece.name == 'boulder' or piece.color == color

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
        piece = self.piece
        if piece is None or piece.name == 'boulder':
            return False
        return piece.color != color

    def has_capturable_enemy_piece(self, color):
        """Return True if this square holds a piece of the opposite color
        that can actually be captured right now.

        Like `has_enemy_piece`, but additionally returns False when the
        enemy piece is marked invulnerable (the invulnerable-manipulation
        variants, or a v2 knight that just gained invulnerability after a
        non-capture jump). Use this when generating capture moves or
        deciding whether a square is a valid attack target.
        """
        piece = self.piece
        if piece is None or piece.name == 'boulder' or piece.invulnerable:
            return False
        return piece.color != color

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