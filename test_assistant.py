#!/usr/bin/env python3
"""
Unit tests for PA — Personal Assistant
Run with:  python -m pytest test_assistant.py -v
       or: python test_assistant.py
"""

import ast
import math
import operator as op
import datetime
import re
import unittest
from unittest.mock import patch, MagicMock


# ── Inline the safe calculator so tests don't depend on GUI / Tkinter ─────────
_SAFE_OPS = {
    ast.Add:  op.add,   ast.Sub:  op.sub,
    ast.Mult: op.mul,   ast.Div:  op.truediv,
    ast.Pow:  op.pow,   ast.Mod:  op.mod,
    ast.USub: op.neg,   ast.UAdd: op.pos,
    ast.FloorDiv: op.floordiv,
}
_SAFE_MATH_FNS = {
    'sqrt': math.sqrt, 'floor': math.floor, 'ceil': math.ceil,
    'log':  math.log,  'log10': math.log10,
    'sin':  math.sin,  'cos':   math.cos,   'tan': math.tan,
    'fabs': math.fabs, 'abs':   abs,        'round': round,
}

def _safe_eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval_node(node.operand))
    if isinstance(node, ast.Call):
        fn_name = (node.func.id if isinstance(node.func, ast.Name)
                   else node.func.attr if isinstance(node.func, ast.Attribute)
                   else None)
        if fn_name in _SAFE_MATH_FNS:
            return _SAFE_MATH_FNS[fn_name](*(_safe_eval_node(a) for a in node.args))
    raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

def _safe_calculate(expr: str):
    tree = ast.parse(expr, mode='eval')
    return _safe_eval_node(tree.body)


# ── Inline the wake-phrase detector ───────────────────────────────────────────
def _is_wake_phrase(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    strict_wake_words = [
        "hey pa", "hey p a", "heypa",
        "okay pa", "ok pa", "hey pee ay",
        "hay pa", "aye pa", "hey par",
        "a pa",   "hey pea",
    ]
    return any(w in t for w in strict_wake_words)


# ── Helpers that mirror assistant.py logic (no GUI dependency) ─────────────────
def _get_time_string() -> str:
    return datetime.datetime.now().strftime("%I:%M %p")

def _get_date_string() -> str:
    return datetime.datetime.now().strftime("%A, %B %d, %Y")

def _build_google_url(query: str) -> str:
    return f"https://www.google.com/search?q={query.replace(' ', '+')}"

def _build_youtube_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"


# ══════════════════════════════════════════════════════════════════════════════
class TestSafeCalculator(unittest.TestCase):
    """Tests for the AST-based safe math evaluator."""

    def test_addition(self):
        self.assertEqual(_safe_calculate("2 + 3"), 5)

    def test_subtraction(self):
        self.assertEqual(_safe_calculate("10 - 4"), 6)

    def test_multiplication(self):
        self.assertEqual(_safe_calculate("6 * 7"), 42)

    def test_division(self):
        self.assertAlmostEqual(_safe_calculate("10 / 4"), 2.5)

    def test_floor_division(self):
        self.assertEqual(_safe_calculate("10 // 3"), 3)

    def test_modulo(self):
        self.assertEqual(_safe_calculate("10 % 3"), 1)

    def test_power(self):
        self.assertEqual(_safe_calculate("2 ** 10"), 1024)

    def test_unary_negation(self):
        self.assertEqual(_safe_calculate("-5"), -5)

    def test_complex_expression(self):
        self.assertEqual(_safe_calculate("(2 + 3) * 4 - 1"), 19)

    def test_sqrt(self):
        self.assertAlmostEqual(_safe_calculate("sqrt(16)"), 4.0)

    def test_floor(self):
        self.assertEqual(_safe_calculate("floor(3.7)"), 3)

    def test_ceil(self):
        self.assertEqual(_safe_calculate("ceil(3.2)"), 4)

    def test_abs(self):
        self.assertEqual(_safe_calculate("abs(-9)"), 9)

    def test_zero_division_raises(self):
        with self.assertRaises(ZeroDivisionError):
            _safe_calculate("5 / 0")

    def test_rejects_import(self):
        """Ensure arbitrary code like __import__ is rejected."""
        with self.assertRaises((ValueError, AttributeError, TypeError)):
            _safe_calculate("__import__('os').system('echo hi')")

    def test_rejects_string_literals(self):
        with self.assertRaises((ValueError, AttributeError, TypeError)):
            _safe_calculate("'hello'")

    def test_rejects_name_lookup(self):
        """Bare variable names not in safe functions must be rejected."""
        with self.assertRaises((ValueError, AttributeError, TypeError)):
            _safe_calculate("os")

    def test_float_result(self):
        self.assertAlmostEqual(_safe_calculate("1 / 3"), 0.3333333333333333)

    def test_nested_functions(self):
        self.assertAlmostEqual(_safe_calculate("sqrt(abs(-25))"), 5.0)


# ══════════════════════════════════════════════════════════════════════════════
class TestWakePhrase(unittest.TestCase):
    """Tests for the wake-word phrase detector."""

    def test_exact_hey_pa(self):
        self.assertTrue(_is_wake_phrase("hey pa"))

    def test_case_insensitive(self):
        self.assertTrue(_is_wake_phrase("HEY PA"))
        self.assertTrue(_is_wake_phrase("Hey Pa"))

    def test_okay_pa(self):
        self.assertTrue(_is_wake_phrase("okay pa"))

    def test_ok_pa(self):
        self.assertTrue(_is_wake_phrase("ok pa"))

    def test_embedded_phrase(self):
        self.assertTrue(_is_wake_phrase("I said hey pa please"))

    def test_false_single_pa(self):
        """Single 'pa' must not trigger."""
        self.assertFalse(_is_wake_phrase("pa"))

    def test_false_single_hey(self):
        self.assertFalse(_is_wake_phrase("hey"))

    def test_false_empty(self):
        self.assertFalse(_is_wake_phrase(""))

    def test_false_none(self):
        self.assertFalse(_is_wake_phrase(None))

    def test_false_random_words(self):
        self.assertFalse(_is_wake_phrase("hello world"))

    def test_false_partial_match(self):
        self.assertFalse(_is_wake_phrase("heyy pa"))

    def test_whitespace_only(self):
        self.assertFalse(_is_wake_phrase("   "))


# ══════════════════════════════════════════════════════════════════════════════
class TestTimeDate(unittest.TestCase):
    """Tests for time/date formatting helpers."""

    def test_time_format(self):
        t = _get_time_string()
        # Must match HH:MM AM/PM
        self.assertRegex(t, r'^\d{1,2}:\d{2} (AM|PM)$')

    def test_date_format(self):
        d = _get_date_string()
        # Must contain full weekday name and a 4-digit year
        self.assertRegex(d, r'\d{4}')
        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        self.assertTrue(any(day in d for day in days))

    def test_time_is_current(self):
        before = datetime.datetime.now()
        t = _get_time_string()
        after = datetime.datetime.now()
        # Hour in the result must match current hour
        hour_str = before.strftime("%I").lstrip("0") or "12"
        self.assertIn(hour_str, t)


# ══════════════════════════════════════════════════════════════════════════════
class TestUrlBuilders(unittest.TestCase):
    """Tests for URL construction helpers."""

    def test_google_url_simple(self):
        url = _build_google_url("python tutorials")
        self.assertIn("google.com/search", url)
        self.assertIn("python", url)
        self.assertIn("tutorials", url)
        self.assertNotIn(" ", url)

    def test_google_url_spaces_replaced(self):
        url = _build_google_url("hello world")
        self.assertIn("+", url)
        self.assertNotIn(" ", url)

    def test_youtube_url(self):
        url = _build_youtube_url("lo-fi music")
        self.assertIn("youtube.com/results", url)
        self.assertIn("search_query", url)
        self.assertNotIn(" ", url)


# ══════════════════════════════════════════════════════════════════════════════
class TestCommandDispatchPatterns(unittest.TestCase):
    """Tests that the regex patterns used in dispatch() work correctly."""

    def _match(self, pattern, text):
        return bool(re.search(pattern, text.lower()))

    def test_time_pattern(self):
        self.assertTrue(self._match(r'\b(time|clock)\b', 'what time is it'))
        self.assertFalse(self._match(r'\b(time|clock)\b', 'set a timer'))  # timer≠time (timer has word boundary)

    def test_date_pattern(self):
        self.assertTrue(self._match(r'\bdate\b', 'what is the date'))
        self.assertFalse(self._match(r'\bdate\b', 'update my calendar'))

    def test_search_pattern(self):
        self.assertTrue(self._match(r'\b(search|google|look up|find)\b', 'search python'))
        self.assertTrue(self._match(r'\b(search|google|look up|find)\b', 'google something'))
        self.assertTrue(self._match(r'\b(search|google|look up|find)\b', 'look up einstein'))

    def test_calculate_pattern(self):
        self.assertTrue(self._match(r'\b(calculate|compute|evaluate|solve)\b', 'calculate 5+3'))
        self.assertTrue(self._match(r'\b(calculate|compute|evaluate|solve)\b', 'solve this equation'))
        self.assertFalse(self._match(r'\b(calculate|compute|evaluate|solve)\b', 'set timer'))

    def test_shutdown_pattern(self):
        self.assertTrue(self._match(r'\b(shutdown|shut down)\b', 'shutdown now'))
        self.assertTrue(self._match(r'\b(shutdown|shut down)\b', 'shut down the pc'))

    def test_wikipedia_pattern(self):
        self.assertTrue(self._match(r'\b(wikipedia|wiki)\b', 'wikipedia python'))
        self.assertTrue(self._match(r'\b(wikipedia|wiki)\b', 'wiki albert einstein'))

    def test_joke_pattern(self):
        self.assertTrue(self._match(r'\bjoke\b', 'tell me a joke'))
        self.assertFalse(self._match(r'\bjoke\b', 'invoke'))

    def test_timer_vs_time(self):
        """'timer' should NOT match the time pattern (word boundary check)."""
        time_pattern   = r'\b(time|clock)\b'
        timer_pattern  = r'\b(timer|remind me|countdown)\b'
        cmd = 'set a timer for 5 minutes'
        self.assertFalse(self._match(time_pattern, cmd))
        self.assertTrue(self._match(timer_pattern, cmd))


# ══════════════════════════════════════════════════════════════════════════════
class TestInputSanitisation(unittest.TestCase):
    """Tests that dangerous inputs are rejected by the safe calculator."""

    INJECTION_PAYLOADS = [
        "__import__('os').system('id')",
        "open('/etc/passwd').read()",
        "exec('import os')",
        "(lambda: None)()",
        "globals()['x']",
    ]

    def test_injection_payloads_rejected(self):
        for payload in self.INJECTION_PAYLOADS:
            with self.subTest(payload=payload):
                with self.assertRaises((ValueError, AttributeError, TypeError, KeyError)):
                    _safe_calculate(payload)


# ══════════════════════════════════════════════════════════════════════════════
class TestThreadingConstants(unittest.TestCase):
    """Tests that audio constants are self-consistent."""

    SAMPLE_RATE   = 16000
    CHUNK_MS      = 30
    CHUNK_SAMPLES = int(16000 * 30 / 1000)

    def test_chunk_samples(self):
        expected = int(self.SAMPLE_RATE * self.CHUNK_MS / 1000)
        self.assertEqual(self.CHUNK_SAMPLES, expected)

    def test_chunk_samples_positive(self):
        self.assertGreater(self.CHUNK_SAMPLES, 0)

    def test_sample_rate_reasonable(self):
        self.assertGreaterEqual(self.SAMPLE_RATE, 8000)
        self.assertLessEqual(self.SAMPLE_RATE, 48000)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
