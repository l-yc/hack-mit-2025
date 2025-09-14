from typing import Any, Mapping

from jinja2 import Environment, BaseLoader, Template, Undefined

class PreserveUndefined(Undefined):
    """
    A Jinja2 Undefined that renders back to its original {{ ... }} expression.

    - Unknown variables become "{{ name }}".
    - Attribute access extends the path: "{{ name.attr }}".
    - Item access extends the path: "{{ name['key'] }}" or "{{ name[0] }}".
    - Calls and operations on unknowns keep them unknown and printable.

    Notes & limitations:
      * Control-flow that depends on unknowns ({% if unknown %}, loops over
        unknowns, etc.) will still execute. If you want to fully *preserve*
        control structures, you need a parser/transformer rather than rendering.
      * Filters/tests called on unknowns will keep the expression unknown.
    """

    # --- Helpers -------------------------------------------------------------

    def _expr(self) -> str:
        # Prefer the composed name path we’ve been building up
        name = getattr(self, "_undefined_name", None)
        if not name:
            # Fallbacks (rare)
            hint = getattr(self, "_undefined_hint", None)
            if hint:
                return hint
            return "undefined"
        return str(name)

    def _fmt(self) -> str:
        return "{{ " + self._expr() + " }}"

    # --- Core conversions ----------------------------------------------------

    def __str__(self) -> str:  # When coerced to string, show the Jinja placeholder
        return self._fmt()

    def __repr__(self) -> str:
        return self._fmt()

    def __html__(self) -> str:  # For autoescape environments
        return self._fmt()

    def __bool__(self) -> bool:  # Truthiness of unknown stays False-ish
        # Returning False is pragmatic for typical templates; change to raise
        # if you’d rather catch these cases.
        return False

    def __len__(self) -> int:
        # Treat as empty sequence for len()
        return 0

    def __iter__(self):
        # Iterating unknown yields nothing (avoids crashes in for-loops)
        if False:
            yield None

    # --- Attribute / item access --------------------------------------------

    def _with_path(self, suffix: str) -> "PreserveUndefined":
        # Create a new instance of our class with an extended dotted/bracketed path
        cls = type(self)
        base = self._expr()
        return cls(name=f"{base}{suffix}")

    def __getattr__(self, name: str) -> "PreserveUndefined":
        # Extend path with .name
        if name.startswith("_"):
            # Internal/private attributes: fall back to base behavior
            return super().__getattr__(name)  # type: ignore[misc]
        return self._with_path(f".{name}")

    def __getitem__(self, key: Any) -> "PreserveUndefined":
        # Extend path with [key] (quote strings)
        if isinstance(key, str):
            return self._with_path(f"['{key}']")
        return self._with_path(f"[{key}]")

    # --- Calls & operations --------------------------------------------------

    def __call__(self, *args, **kwargs) -> "PreserveUndefined":
        # Keep as unknown call expression; we don’t attempt to serialize args
        return self._with_path("(…)")

    # Return self for most ops so nested expressions still stringify to the placeholder
    def _op(self, *_: Any) -> "PreserveUndefined":
        return self

    __add__ = __radd__ = _op
    __sub__ = __rsub__ = _op
    __mul__ = __rmul__ = _op
    __truediv__ = __rtruediv__ = _op
    __floordiv__ = __rfloordiv__ = _op
    __mod__ = __rmod__ = _op
    __pow__ = __rpow__ = _op
    __and__ = __rand__ = _op
    __or__ = __ror__ = _op
    __xor__ = __rxor__ = _op
    __lt__ = __le__ = __gt__ = __ge__ = __eq__ = __ne__ = _op


def _default_env() -> Environment:
    # BaseLoader since we render strings; keep_trailing_newline for pleasant diffs
    return Environment(
        loader=BaseLoader(),
        undefined=PreserveUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def partial_render(template_str: str, context: Optional[Mapping[str, Any]] = None) -> str:
    """
    Partially render a Jinja template string.

    Any variables found in `context` are rendered. Any missing variables
    are preserved as their original Jinja placeholders, e.g., "{{ missing }}".

    Parameters
    ----------
    template_str : str
        The Jinja template source (as a string).
    context : Mapping[str, Any] | None
        Keys/values to substitute. (Defaults to empty.)

    Returns
    -------
    str
        The partially-rendered template.
    """
    env = _default_env()
    tmpl = env.from_string(template_str)
    return tmpl.render(**(context or {}))


if __name__ == "__main__":
    print(partial_render(
        open('./prompts/template.jinja').read(),
        {
            'personality': open('./prompts/alex.md').read()
        }
    ))