"""
Board state encoding for neural network input.

Converts the board into a multi-channel 8x8 tensor that the neural network
can process. No human-defined features — the network sees raw piece positions
and learns what matters on its own.

Encoding channels (21 total):
  Channels  0-5:  White pieces (pawn, knight, bishop, rook, queen, king)
  Channels  6-11: Black pieces (pawn, knight, bishop, rook, queen, king)
  Channel  12:    Boulder position (on square)
  Channel  13:    Boulder on intersection (all 1s if true, else all 0s)
  Channel  14:    Royal pieces (1 where any royal piece stands)
  Channel  15:    Transformed pieces (1 where any transformed piece stands)
  Channel  16:    Current player is white (all 1s or all 0s)
  Channel  17:    Boulder cooldown > 0 (all 1s or all 0s)
  Channel  18:    Tiny endgame active (all 1s or all 0s)
  Channel  19:    Promoted (non-royal) queens/transformed (1 where piece is non-royal)
  Channel  20:    Turn number (normalized to 0-1, fills entire plane)
"""

import numpy as np
from piece import Pawn, Knight, Bishop, Rook, Queen, King, Boulder


# Map piece types to channel indices within their color group
PIECE_CHANNEL = {
    'pawn': 0,
    'knight': 1,
    'bishop': 2,
    'rook': 3,
    'queen': 4,
    'king': 5,
}

NUM_CHANNELS = 21


def encode_board(board, current_player, turn_number=0):
    """Encode a Board object into a numpy array of shape (NUM_CHANNELS, 8, 8).

    Args:
        board: Board object with squares[row][col].piece
        current_player: 'white' or 'black'
        turn_number: current turn number (for normalization)

    Returns:
        numpy array of shape (21, 8, 8), dtype float32
    """
    state = np.zeros((NUM_CHANNELS, 8, 8), dtype=np.float32)

    for row in range(8):
        for col in range(8):
            piece = board.squares[row][col].piece
            if not piece:
                continue

            if isinstance(piece, Boulder):
                # Channel 12: boulder on a square
                state[12, row, col] = 1.0
                continue

            # Determine piece type name for channel mapping
            # Transformed pieces use their current form's name
            piece_name = piece.name
            if piece_name not in PIECE_CHANNEL:
                continue

            channel_offset = PIECE_CHANNEL[piece_name]

            if piece.color == 'white':
                state[channel_offset, row, col] = 1.0
            elif piece.color == 'black':
                state[6 + channel_offset, row, col] = 1.0

            # Channel 14: royal pieces
            if piece.is_royal:
                state[14, row, col] = 1.0

            # Channel 15: transformed pieces
            if piece.is_transformed:
                state[15, row, col] = 1.0

            # Channel 19: promoted (non-royal) pieces
            if not piece.is_royal and (isinstance(piece, Queen) or piece.is_transformed):
                state[19, row, col] = 1.0

    # Channel 13: boulder on intersection (global flag)
    if board.boulder and board.boulder.on_intersection:
        state[13, :, :] = 1.0

    # Channel 16: current player is white
    if current_player == 'white':
        state[16, :, :] = 1.0

    # Channel 17: boulder cooldown active
    boulder_piece = board.boulder
    if boulder_piece is None:
        # Boulder might be on a square, find it
        for row in range(8):
            for col in range(8):
                p = board.squares[row][col].piece
                if p and isinstance(p, Boulder):
                    boulder_piece = p
                    break
            if boulder_piece:
                break
    if boulder_piece and boulder_piece.cooldown > 0:
        state[17, :, :] = 1.0

    # Channel 18: tiny endgame active
    if board.tiny_endgame_active:
        state[18, :, :] = 1.0

    # Channel 20: normalized turn number (0 to 1, capped at 1000)
    state[20, :, :] = min(turn_number / 1000.0, 1.0)

    return state


def encode_board_for_player(board, current_player, turn_number=0):
    """Encode from the perspective of the current player.

    If current player is black, the board is flipped vertically so the
    network always sees the position from the 'home' perspective. This
    helps the network generalize — it doesn't need to learn separate
    patterns for white and black.

    Returns:
        numpy array of shape (21, 8, 8), dtype float32
    """
    state = encode_board(board, current_player, turn_number)

    if current_player == 'black':
        # Flip the board vertically (row 0 becomes row 7)
        state = state[:, ::-1, :].copy()

        # Swap white and black piece channels (0-5 <-> 6-11)
        white_channels = state[0:6].copy()
        state[0:6] = state[6:12]
        state[6:12] = white_channels

    return state
