"""
Analyze game data across manipulation variants and produce comparison tables.

Usage:
    python3 src/analyze_variants.py
"""

import json
import os
import sys
from collections import defaultdict
import statistics


def load_games(file_paths):
    """Load and merge games from multiple JSON files."""
    games = []
    for path in file_paths:
        if os.path.exists(path):
            with open(path) as f:
                games.extend(json.load(f))
    return games


def analyze_variant(games, label):
    """Compute all metrics for a list of games."""
    n = len(games)
    if n == 0:
        return None

    # Game length
    lengths = [g['total_turns'] for g in games]

    # Win rates
    white_wins = sum(1 for g in games if g['winner'] == 'white')
    black_wins = sum(1 for g in games if g['winner'] == 'black')

    # Total captures per game
    captures_per_game = [g['total_captures'] for g in games]

    # Manipulation metrics
    manip_counts = []
    transform_away_counts = []
    revert_base_counts = []

    # Frozen piece captured on next turn (turn N+1 = freeze turn for owner)
    frozen_captured_next_turn_counts = []
    # Frozen piece captured on turn N+2 (manipulator's next turn)
    frozen_captured_turn_n2_counts = []

    for g in games:
        turns = g['turns']
        manip_count = 0
        transform_away = 0
        revert_base = 0
        frozen_captured_next = 0
        frozen_captured_n2 = 0

        for i, t in enumerate(turns):
            if t['turn_type'] == 'manipulation':
                manip_count += 1
                manipulated_piece_type = t['piece_type']
                manipulated_piece_color = t['piece_color']
                manipulated_to_sq = t['to_sq']
                manipulator_color = t['player']

                # Turn N+1: owner's turn (the player whose piece was manipulated)
                # Check if the manipulated piece was captured on this turn
                if i + 1 < len(turns):
                    next_t = turns[i + 1]
                    if (next_t['is_capture'] and
                            next_t['to_sq'] == manipulated_to_sq and
                            next_t.get('captured_piece_type') == manipulated_piece_type and
                            next_t.get('captured_piece_color') == manipulated_piece_color):
                        frozen_captured_next += 1

                # Turn N+2: manipulator's next turn
                # Check if the manipulated piece was captured on this turn
                if i + 2 < len(turns):
                    next2_t = turns[i + 2]
                    if (next2_t['is_capture'] and
                            next2_t['to_sq'] == manipulated_to_sq and
                            next2_t.get('captured_piece_type') == manipulated_piece_type and
                            next2_t.get('captured_piece_color') == manipulated_piece_color):
                        frozen_captured_n2 += 1

            elif t['turn_type'] == 'transformation':
                if t.get('transform_target') != 'queen':
                    transform_away += 1
                else:
                    revert_base += 1

        manip_counts.append(manip_count)
        transform_away_counts.append(transform_away)
        revert_base_counts.append(revert_base)
        frozen_captured_next_turn_counts.append(frozen_captured_next)
        frozen_captured_turn_n2_counts.append(frozen_captured_n2)

    total_manips = sum(manip_counts)

    # Manipulation variation: coefficient of variation
    manip_cv = (statistics.stdev(manip_counts) / statistics.mean(manip_counts)
                if statistics.mean(manip_counts) > 0 else 0)

    # Pieces remaining at end
    pieces_at_end = []
    for g in games:
        last_turn = g['turns'][-1] if g['turns'] else None
        if last_turn and 'pieces_remaining' in last_turn:
            pr = last_turn['pieces_remaining']
            total = sum(pr.get('white', {}).values()) + sum(pr.get('black', {}).values())
            pieces_at_end.append(total)

    return {
        'label': label,
        'games': n,
        'avg_length': statistics.mean(lengths),
        'median_length': statistics.median(lengths),
        'std_length': statistics.stdev(lengths) if n > 1 else 0,
        'white_win_pct': white_wins / n * 100,
        'black_win_pct': black_wins / n * 100,
        'avg_captures': statistics.mean(captures_per_game),
        'avg_manips': statistics.mean(manip_counts),
        'total_manips': total_manips,
        'manip_cv': manip_cv,
        'avg_transform_away': statistics.mean(transform_away_counts),
        'avg_revert_base': statistics.mean(revert_base_counts),
        'avg_total_transforms': statistics.mean(transform_away_counts) + statistics.mean(revert_base_counts),
        'frozen_captured_n1_total': sum(frozen_captured_next_turn_counts),
        'frozen_captured_n1_pct': (sum(frozen_captured_next_turn_counts) / total_manips * 100
                                    if total_manips > 0 else 0),
        'frozen_captured_n2_total': sum(frozen_captured_turn_n2_counts),
        'frozen_captured_n2_pct': (sum(frozen_captured_turn_n2_counts) / total_manips * 100
                                    if total_manips > 0 else 0),
        'avg_pieces_at_end': statistics.mean(pieces_at_end) if pieces_at_end else 0,
    }


def print_comparison_table(results):
    """Print a formatted comparison table."""
    if not results:
        print("No data to display.")
        return

    # Define metrics and their formatting
    metrics = [
        ('Games', 'games', '{:d}'),
        ('Avg game length (turns)', 'avg_length', '{:.1f}'),
        ('Median game length', 'median_length', '{:.0f}'),
        ('Std dev game length', 'std_length', '{:.1f}'),
        ('White win %', 'white_win_pct', '{:.0f}%'),
        ('Black win %', 'black_win_pct', '{:.0f}%'),
        ('Avg captures/game', 'avg_captures', '{:.1f}'),
        ('Avg manipulations/game', 'avg_manips', '{:.1f}'),
        ('Manipulation CV¹', 'manip_cv', '{:.2f}'),
        ('Avg transforms away/game²', 'avg_transform_away', '{:.2f}'),
        ('Avg reverts to base/game²', 'avg_revert_base', '{:.2f}'),
        ('Avg total transforms/game', 'avg_total_transforms', '{:.2f}'),
        ('Frozen captured on N+1³', 'frozen_captured_n1_total', '{:d}'),
        ('  % of all manipulations', 'frozen_captured_n1_pct', '{:.1f}%'),
        ('Captured on N+2⁴', 'frozen_captured_n2_total', '{:d}'),
        ('  % of all manipulations', 'frozen_captured_n2_pct', '{:.1f}%'),
        ('Avg pieces remaining', 'avg_pieces_at_end', '{:.1f}'),
    ]

    # Column widths
    label_width = max(len(m[0]) for m in metrics) + 2
    col_width = max(len(r['label']) for r in results) + 2
    col_width = max(col_width, 12)

    # Header
    header = f"{'Metric':<{label_width}}"
    for r in results:
        header += f"{r['label']:>{col_width}}"
    print(header)
    print('-' * len(header))

    # Rows
    for name, key, fmt in metrics:
        row = f"{name:<{label_width}}"
        for r in results:
            val = r.get(key, 0)
            if '%' in fmt:
                formatted = fmt.format(val).rstrip('%') + '%'
            else:
                formatted = fmt.format(val)
            row += f"{formatted:>{col_width}}"
        print(row)

    # Footnotes
    print()
    print("¹ Coefficient of variation of manipulations per game (higher = more varied strategy)")
    print("² Transform away = queen→rook/bishop/knight; Revert = back to queen form")
    print("³ Frozen piece captured by the owner on their turn (N+1), while piece is frozen")
    print("⁴ Piece captured by manipulator on their next turn (N+2); blocked by invulnerability")


def main():
    # Define all variants and their data files
    variant_configs = {
        'Original': [
            'data/variant_original_50_games.json',
            'data/variant_original_50_games_batch2.json',
        ],
        'Freeze': [
            'data/variant_freeze_v2_50_games.json',
            'data/variant_freeze_v2_50_games_batch2.json',
        ],
        'Freeze+NR': [
            'data/variant_freeze_no_repeat_50_games.json',
            'data/variant_freeze_no_repeat_50_games_batch2.json',
        ],
        'Freeze+Invuln': [
            'data/variant_freeze_invulnerable_v2_50_games.json',
            'data/variant_freeze_invulnerable_v2_50_games_batch2.json',
        ],
        'Freeze+Invuln+NR': [
            'data/variant_freeze_invulnerable_no_repeat_v2_50_games.json',
            'data/variant_freeze_invulnerable_no_repeat_v2_50_games_batch2.json',
        ],
        'Freeze+Invuln+CD': [
            'data/variant_freeze_invulnerable_cooldown_v2_50_games.json',
            'data/variant_freeze_invulnerable_cooldown_v2_50_games_batch2.json',
        ],
    }

    results = []
    for label, paths in variant_configs.items():
        games = load_games(paths)
        if games:
            result = analyze_variant(games, label)
            if result:
                results.append(result)
                print(f"Loaded {len(games)} games for {label}")

    print()
    print_comparison_table(results)


if __name__ == '__main__':
    main()
