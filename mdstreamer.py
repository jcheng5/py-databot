from typing import Awaitable, Callable


class MarkdownStreamer:
    """
    Used to stream Markdown text to a callback function. It coalesces multiple
    code blocks into a single block and handles newlines intelligently.
    """

    def __init__(self, callback: Callable[[str], Awaitable[None]]):
        """
        Create a new MarkdownStreamer object

        Args:
            callback: Function to process Markdown output, takes a single markdown argument
        """
        self._callback = callback
        self._in_code_block = False
        self._last_ends_with_newline = True
        self._empty = True

    async def md(
        self,
        text: str,
        ensure_newline_before: bool = False,
        ensure_newline_after: bool = False,
    ):
        """
        Process text as regular Markdown

        Args:
            text: Text to be processed as Markdown, can be a string or list of strings
            ensure_newline_before: Ensure text starts with a newline
            ensure_newline_after: Ensure text ends with a newline

        Returns:
            self for method chaining
        """
        # Validate inputs
        if not isinstance(text, (str, list)):
            raise ValueError("'text' must be a string or list of strings")

        # Skip empty text
        if not text or (isinstance(text, list) and all(t == "" for t in text)):
            return self

        # Collapse multi-line text
        if isinstance(text, list):
            text = "\n".join(text)

        # Close code block if needed
        if self._in_code_block:
            await self._close_code_block()

        # Send the text with newline control
        await self._send(text, ensure_newline_before, ensure_newline_after)

        return self

    async def code(
        self,
        text: str | list[str],
        ensure_newline_before: bool = False,
        ensure_newline_after: bool = False,
    ):
        """
        Process text as code block

        Args:
            text: Text to be formatted as a code block, can be a string or list of strings
            ensure_newline_before: Ensure a newline before the code block
            ensure_newline_after: Ensure a newline after the code block

        Returns:
            self for method chaining
        """
        # Validate inputs
        if not isinstance(text, (str, list)):
            raise ValueError("'text' must be a string or list of strings")

        # Skip empty text
        if not text or (isinstance(text, list) and all(t == "" for t in text)):
            return self

        # Collapse multi-line text
        if isinstance(text, list):
            text = "\n".join(text)

        # Start code block if needed with proper spacing
        if not self._in_code_block:
            await self._send("\n``````\n", True, False)
            self._in_code_block = True

        # Add the text without additional markers
        await self._send(text, ensure_newline_before, ensure_newline_after)

        return self

    async def close(self):
        """
        Close any open code blocks

        Returns:
            self for method chaining
        """
        if self._in_code_block:
            await self._close_code_block()

        return self

    async def _send(
        self,
        text: str,
        ensure_newline_before: bool = False,
        ensure_newline_after: bool = False,
    ):
        """
        Send text to the callback and update state

        Args:
            text: Text to send
            ensure_newline_before: Ensure text starts with a newline
            ensure_newline_after: Ensure text ends with a newline
        """
        # Check if text begins with a newline
        text_begins_with_newline = text.startswith("\n")

        # Add leading newline if needed and text doesn't already start with one
        if (
            ensure_newline_before
            and not self._last_ends_with_newline
            and not text_begins_with_newline
        ):
            await self._callback("\n")
            self._last_ends_with_newline = True

        # Send the main text
        await self._callback(text)
        self._last_ends_with_newline = text.endswith("\n")

        # Add trailing newline if needed
        if ensure_newline_after and not self._last_ends_with_newline:
            await self._callback("\n")
            self._last_ends_with_newline = True

        if self._empty:
            self._empty = False

    async def _close_code_block(self):
        """Close a code block with proper formatting"""
        await self._send("``````\n", True, False)
        self._in_code_block = False


class NullStreamer:
    """
    Null object pattern implementation of MarkdownStreamer
    that does nothing with inputs
    """

    async def md(self, text, **kwargs):
        """Do nothing with markdown text"""
        return self

    async def code(self, text, **kwargs):
        """Do nothing with code text"""
        return self

    async def close(self):
        """Do nothing on close"""
        pass
