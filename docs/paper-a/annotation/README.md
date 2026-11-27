# Labelling the statements of a game into rules

You are asked to group the statements of a game description into the
RULES of the game, as a reader who knows the rules would. Your sheet is
compared with other annotators' and with a computer method's, so please
label independently: do not discuss your labels with anyone until you
have finished, and do not open the `.gdl` files in the repository --
their comments group the statements for you.

For each game folder:

1. Read `statements.md`: the rules of play in plain words, then the
   statements of the description, numbered.
2. Fill in `sheet.csv` (any spreadsheet program opens it). Put your
   name, the date and roughly how long it took in the `#` lines at the
   top.
3. For each statement, write in the `rules` column the rule or rules it
   belongs to. Choose your own short names (`capture`, `scoring`, ...);
   only which statements you group together is compared, never the
   names. Use the SAME name for the same rule throughout one game.
   - A statement that serves several rules gets several names,
     separated by `;` -- for example `capture;ending`.
   - A statement that belongs to no rule (a role declaration, say)
     stays blank.
   - Put `y` in `ambiguous` when you hesitated, and a few words in
     `note` saying between what.
4. A RULE here is something a player would name when explaining the
   game: how a piece moves, how a capture works, when the game ends, who
   wins. Group statements by what they DO in the game, not by where they
   appear in the list or what they are called.

There are no trick questions and no single right answer: disagreement
between careful annotators is exactly what is being measured.
