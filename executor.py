import ast
import contextlib
import io
import sys
from dataclasses import dataclass
from typing import Any, Generator, NamedTuple, Optional

import matplotlib.pyplot as plt


class StatementResult(NamedTuple):
    """Results from executing a single Python statement."""
    source: str                 # The source code that was executed
    output: str                # Captured stdout/stderr
    return_value: Optional[Any]  # Return value (for expressions)
    plot_data: Optional[bytes]   # PNG data of any matplotlib plot
    error: Optional[Exception]   # Exception if one occurred

class ExecutionContext:
    def __init__(self):
        """Initialize an empty execution context with no variables."""
        self.globals = {}
        self.locals = {}
    
    def _capture_plot(self) -> Optional[bytes]:
        """Capture the current matplotlib plot if one exists."""
        if plt.get_fignums():
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            return buffer.getvalue()
        return None
    
    def _execute_statement(self, node: ast.AST, code: str) -> StatementResult:
        """Execute a single AST node and return the results."""
        # Get the source code for this node
        source = ast.get_source_segment(code, node)
        
        # Capture stdout/stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        output = ""
        return_value = None
        plot_data = None
        error = None
        
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                if isinstance(node, ast.Expr):
                    # For expressions, we want to capture the return value
                    return_value = eval(compile(ast.Expression(node.value), '<string>', 'eval'),
                                     self.globals, self.locals)
                else:
                    # For statements, just execute them
                    exec(compile(ast.Module([node], type_ignores=[]), '<string>', 'exec'),
                         self.globals, self.locals)
                
                # Capture any plot that was created
                plot_data = self._capture_plot()
                
                # Get output from stdout/stderr
                output = stdout.getvalue() + stderr.getvalue()
                
        except Exception as e:
            error = e
            output = stdout.getvalue() + stderr.getvalue()
        
        return StatementResult(source, output, return_value, plot_data, error)
    
    def run_code(self, code: str) -> Generator[StatementResult, None, None]:
        """Execute a string of Python code and return the results.
        
        Args:
            code: String containing Python code to execute
            
        Returns:
            Generator of StatementResult objects containing execution results for each statement
        """
        
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Execute each top-level statement
            for node in tree.body:
                result = self._execute_statement(node, code)
                yield result
                
                # If there was an error, stop execution
                if result.error is not None:
                    break
                    
        except SyntaxError as e:
            # Handle syntax errors in the entire code block
            yield StatementResult("", "", None, None, e)
