import pytest

from mdstreamer import MarkdownStreamer, NullStreamer


def test_markdown_streamer_constructor_validates_inputs():
    # Valid callback
    MarkdownStreamer(lambda x: None)  # Should not raise
    
    # Not a function
    with pytest.raises(ValueError, match="must be a function"):
        MarkdownStreamer("not a function")
    
    # Function with wrong number of arguments
    with pytest.raises(ValueError, match="exactly one argument"):
        MarkdownStreamer(lambda: None)
    
    with pytest.raises(ValueError, match="exactly one argument"):
        MarkdownStreamer(lambda x, y: None)

def test_code_validates_inputs():
    ms = MarkdownStreamer(lambda x: None)
    with pytest.raises(ValueError, match="must be a string or list"):
        ms.code(1)

def test_md_accepts_list_of_strings():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md(["Line 1", "Line 2", "Line 3"])
    
    assert "".join(output) == "Line 1\nLine 2\nLine 3"

def test_code_accepts_list_of_strings():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.code(["def hello():", "    print('Hello')", "    return True"])
    
    assert "".join(output) == "\n``````\ndef hello():\n    print('Hello')\n    return True"

def test_empty_strings_are_no_op_regardless_of_list_length():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("")
    ms.code("")
    ms.md(["", ""])
    ms.code(["", "", ""])
    
    assert output == []

def test_md_outputs_text_correctly():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("Hello, world!")
    
    assert "".join(output) == "Hello, world!"

def test_code_formats_code_blocks_correctly():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.code("print('hello')")
    
    assert "".join(output) == "\n``````\nprint('hello')"

def test_consecutive_code_calls_result_in_one_code_block():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.code("line 1")
    ms.code("line 2")
    
    assert "".join(output) == "\n``````\nline 1line 2"

def test_code_blocks_get_closed_when_switching_to_md():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.code("code")
    ms.md("text")
    
    assert "".join(output) == "\n``````\ncode\n``````\ntext"

def test_close_closes_code_blocks():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.code("code")
    ms.close()
    
    assert "".join(output) == "\n``````\ncode\n``````\n"

def test_ensure_newline_before_adds_newlines_when_needed():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("no newline")
    ms.md("needs newline", ensure_newline_before=True)
    
    assert "".join(output) == "no newline\nneeds newline"

def test_ensure_newline_after_adds_newlines_when_needed():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("text", ensure_newline_after=True)
    
    assert "".join(output) == "text\n"

def test_text_already_ending_with_newline_doesnt_get_duplicate_newlines():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("text\n", ensure_newline_after=True)
    
    assert "".join(output) == "text\n"

def test_text_already_starting_with_newline_doesnt_get_duplicate_newlines():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("text")
    ms.md("\nmore text", ensure_newline_before=True)
    
    assert "".join(output) == "text\nmore text"

def test_chaining_works():
    output = []
    ms = MarkdownStreamer(lambda x: output.append(x))
    
    ms.md("text").code("code").md("more text")
    
    assert "".join(output) == "text\n``````\ncode\n``````\nmore text"