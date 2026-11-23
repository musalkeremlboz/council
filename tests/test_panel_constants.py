import inspect
from council import context

def test_budgets_are_named_and_are_the_defaults():
    assert (context.START_BUDGET, context.START_CARDS, context.MESSAGE_BUDGET, context.MESSAGE_LIMIT) == (9000, 2, 3500, 5)
    assert (context.SECTION_CLIP, context.MIN_ROOM, context.START_RELEVANT_LIMIT, context.START_RELEVANT_CLIP) == (800, 200, 6, 900)
    rel = inspect.signature(context.relevant).parameters
    assert rel["budget"].default == context.MESSAGE_BUDGET and rel["limit"].default == context.MESSAGE_LIMIT
    boot = inspect.signature(context.bootstrap).parameters
    assert boot["budget"].default == context.START_BUDGET and boot["cards"].default == context.START_CARDS
