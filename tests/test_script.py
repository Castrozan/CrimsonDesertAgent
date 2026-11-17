import unittest

from hypothesis import given, strategies as st

from crimson_desert_agent.script import VERBS, ScriptError, parse
from crimson_desert_agent.virtual_pad import CONTROL_NAMES

controls = st.sampled_from(CONTROL_NAMES)
durations = st.floats(min_value=0, max_value=120, allow_nan=False).map(
    lambda value: round(value, 3)
)
deflections = st.floats(min_value=-1, max_value=1, allow_nan=False).map(
    lambda value: round(value, 3)
)
coordinates = st.floats(min_value=-20000, max_value=20000, allow_nan=False).map(
    lambda value: round(value, 3)
)
control_lists = st.lists(controls, min_size=1, max_size=4)


def words(*parts) -> str:
    return " ".join(
        repr(part) if isinstance(part, float) else str(part) for part in parts
    )


valid_steps = st.one_of(
    st.builds(lambda name: (words("press", name), "press", (name,), ()), controls),
    st.builds(
        lambda name, hold, gap: (
            words("press", name, hold, gap),
            "press",
            (name, hold, gap),
            (),
        ),
        controls,
        durations,
        durations,
    ),
    st.builds(
        lambda names: (words("down", *names), "down", (), tuple(names)), control_lists
    ),
    st.builds(
        lambda names: (words("up", *names), "up", (), tuple(names)), control_lists
    ),
    st.builds(
        lambda side, right, up: (
            words("stick", side, right, up),
            "stick",
            (side, right, up),
            (),
        ),
        st.sampled_from(["left", "right"]),
        deflections,
        deflections,
    ),
    st.builds(
        lambda duration: (words("wait", duration), "wait", (duration,), ()), durations
    ),
    st.builds(
        lambda duration, names: (
            words("hold", duration, *names),
            "hold",
            (duration,),
            tuple(names),
        ),
        durations,
        control_lists,
    ),
    st.builds(
        lambda right, forward, duration, names: (
            words("move", right, forward, duration, *names),
            "move",
            (right, forward, duration),
            tuple(names),
        ),
        deflections,
        deflections,
        durations,
        st.lists(controls, max_size=3),
    ),
    st.builds(
        lambda right, up, duration: (
            words("look", right, up, duration),
            "look",
            (right, up, duration),
            (),
        ),
        deflections,
        deflections,
        durations,
    ),
    st.builds(
        lambda heading: (words("turn", heading), "turn", (heading,), ()), coordinates
    ),
    st.builds(
        lambda x, z, names: (words("goto", x, z, *names), "goto", (x, z), tuple(names)),
        coordinates,
        coordinates,
        st.lists(controls, max_size=2),
    ),
    st.sampled_from(
        [
            ("state", "state", (), ()),
            ("log", "log", (), ()),
            ("focus", "focus", (), ()),
            ("release", "release", (), ()),
            ("shot /tmp/a.jpg", "shot", ("/tmp/a.jpg",), ()),
        ]
    ),
)
invalid_steps = st.sampled_from(
    [
        "jump",
        "press",
        "press nothing",
        "press a 0.1 0.1 0.1",
        "down",
        "up",
        "stick middle 0 0",
        "stick left 2 0",
        "wait",
        "wait -1",
        "wait 121",
        "wait soon",
        "hold 1",
        "move 0 1",
        "move 0 3 1",
        "look 0 0",
        "turn",
        "turn 90 speed=2",
        "turn nan",
        "goto 1",
        "goto 1 2 sprint",
        "state now",
        "shot",
        "release a",
    ]
)


class ParseTest(unittest.TestCase):
    @given(
        st.lists(valid_steps, min_size=1, max_size=8),
        st.sampled_from([";", "\n", " ; ", ";;"]),
    )
    def test_every_valid_script_parses_to_its_steps_in_order(self, steps, separator):
        parsed = parse(separator.join(text for text, _, _, _ in steps))
        self.assertEqual(
            [(step.verb, step.values, step.rest) for step in parsed],
            [(verb, values, rest) for _, verb, values, rest in steps],
        )

    @given(
        st.lists(valid_steps, max_size=4),
        invalid_steps,
        st.lists(valid_steps, max_size=4),
    )
    def test_one_invalid_step_rejects_the_whole_script(self, before, invalid, after):
        script = ";".join(
            [*(text for text, *_ in before), invalid, *(text for text, *_ in after)]
        )
        with self.assertRaises(ScriptError):
            parse(script)

    def test_options_are_named_and_checked(self):
        step = parse("goto 10 -4 rb tolerance=0.5 timeout=12")[0]
        self.assertEqual(
            (step.values, step.rest, step.options),
            ((10.0, -4.0), ("rb",), {"tolerance": 0.5, "timeout": 12.0}),
        )

    def test_empty_script_is_rejected(self):
        for script in ("", " ; \n ;"):
            with self.assertRaises(ScriptError):
                parse(script)

    def test_every_verb_has_a_handler(self):
        from crimson_desert_agent.script_run import ScriptRun

        for verb in VERBS:
            self.assertTrue(callable(getattr(ScriptRun, f"_{verb}")), verb)


if __name__ == "__main__":
    unittest.main()
