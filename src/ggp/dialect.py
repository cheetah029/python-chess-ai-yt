"""Which GDL a description is written in: GDL-I, GDL-II or GDL-III.

Issue #280. The three are nested, each adding keywords to the last:

  GDL-I    role, init, true, legal, does, next, terminal, goal,
           distinct, not  -- perfect information
  GDL-II   + sees(R, P)   R is told P after the joint move
           + random       the role of nature, playing uniformly
           (Schiffel & Thielscher 2014)
  GDL-III  + knows(R, P)  R knows P in the current position
           + knows(P)     P is common knowledge
           (Thielscher, IJCAI 2017)

The dialect is the HIGHEST one whose keywords appear, read from the
description itself. Nothing is declared and no file name is consulted.

WHY THE CALLER CARES. GDL-III is the only dialect whose meaning is not a
function of the current state: `knows` is defined over every play
sequence a role cannot tell apart from the actual one. So `GGPGame`
keeps the play history and installs the epistemic evaluator for a
GDL-III description and does neither otherwise. A GDL-I or GDL-II game
goes down exactly the code path it went down before #280.
"""

GDL_I = 'GDL-I'
GDL_II = 'GDL-II'
GDL_III = 'GDL-III'

#: The role GDL-II reserves for nature.
RANDOM_ROLE = 'random'


def _literals(goal):
    """Every literal inside a body goal, looking through not/or/and."""
    if isinstance(goal, tuple) and goal and goal[0] in ('not', 'or',
                                                        'and'):
        for sub in goal[1:]:
            yield from _literals(sub)
    else:
        yield goal


def _predicate(term):
    if isinstance(term, tuple) and term:
        return term[0]
    return term


def detect(forms):
    """GDL_I, GDL_II or GDL_III for a list of parsed forms."""
    has_sees = has_random = has_knows = False
    for form in forms:
        if isinstance(form, tuple) and form and form[0] == '<=':
            head, body = form[1], form[2:]
        else:
            head, body = form, ()
        if _predicate(head) == 'sees':
            has_sees = True
        if head == ('role', RANDOM_ROLE):
            has_random = True
        for goal in body:
            for literal in _literals(goal):
                if _predicate(literal) == 'knows':
                    has_knows = True
    if has_knows:
        return GDL_III
    if has_sees or has_random:
        return GDL_II
    return GDL_I
