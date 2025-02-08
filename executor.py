import ast
import contextlib
import io
import sys
from dataclasses import dataclass
from typing import Any, Callable, List, NamedTuple, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


class PlotData(NamedTuple):
    """Container for plot data and metadata."""
    png_data: bytes
    size_inches: Tuple[float, float]  # (width, height) in inches
    size_pixels: Tuple[int, int]      # (width, height) in pixels
    dpi: float                        # dots per inch used
    is_default_size: bool

class StatementResult(NamedTuple):
    """Results from executing a single Python statement."""
    source: str                 # The source code that was executed
    output: str                # Captured stdout/stderr
    return_value: Optional[Any]  # Return value (for expressions)
    plot_data: Optional[PlotData]  # PNG data and metadata of any matplotlib plot
    error: Optional[Exception]   # Exception if one occurred

class PlotCapture(contextlib.ContextDecorator):
    """Context manager that captures matplotlib plots instead of displaying them."""
    
    def __init__(self, callback: Callable[[PlotData], None], 
                 default_size: Tuple[float, float] = (6.4, 4.8),
                 dpi: float = 100):
        self.callback = callback
        self.original_plt_show = None
        self.original_fig_show = None
        self.default_size = default_size
        self.dpi = dpi
        
        # Set the default figure size and DPI
        plt.rcParams['figure.figsize'] = default_size
        plt.rcParams['figure.dpi'] = dpi
    
    def capture_figure(self, fig: Figure) -> PlotData:
        """Capture a figure as PNG data along with its metadata."""
        buffer = io.BytesIO()
        
        # Get the figure size in inches
        size_inches = (fig.get_figwidth(), fig.get_figheight())
        
        # Calculate pixel dimensions
        dpi = fig.dpi
        size_pixels = (int(size_inches[0] * dpi), int(size_inches[1] * dpi))
        
        # Save the figure
        fig.savefig(buffer, format='png', dpi=dpi)
        
        is_default = size_inches == self.default_size
        
        plt.close(fig)
        return PlotData(
            png_data=buffer.getvalue(),
            size_inches=size_inches,
            size_pixels=size_pixels,
            dpi=dpi,
            is_default_size=is_default
        )
    
    def custom_plt_show(self, *args, **kwargs):
        """Replacement for plt.show() that captures plots."""
        for num in plt.get_fignums():
            fig = plt.figure(num)
            plot_data = self.capture_figure(fig)
            self.callback(plot_data)
    
    def custom_fig_show(self, fig, *args, **kwargs):
        """Replacement for Figure.show() that captures the plot."""
        plot_data = self.capture_figure(fig)
        self.callback(plot_data)
    
    def __enter__(self):
        """Set up the plot capture environment."""
        # Store original show functions
        self.original_plt_show = plt.show
        self.original_fig_show = Figure.show
        
        # Replace with our custom functions
        plt.show = self.custom_plt_show
        Figure.show = self.custom_fig_show
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the original plot display behavior."""
        # Restore original show functions
        plt.show = self.original_plt_show
        Figure.show = self.original_fig_show

class ExecutionContext:
    def __init__(self, default_plot_size: Tuple[float, float] = (6.4, 4.8),
                 dpi: float = 100):
        """Initialize an empty execution context with no variables.
        
        Args:
            default_plot_size: Tuple of (width, height) in inches for default figure size.
                             Defaults to matplotlib's default size of (6.4, 4.8).
            dpi: Dots per inch for the figure. Determines pixel dimensions.
                Default is 100, which means default size will be 640x480 pixels.
        """
        self.globals = {}
        self.locals = {}
        self.default_plot_size = default_plot_size
        self.dpi = dpi
        
        # Use Agg backend for consistent behavior
        matplotlib.use('Agg')
        
        # Set the default figure size and DPI
        plt.rcParams['figure.figsize'] = default_plot_size
        plt.rcParams['figure.dpi'] = dpi
    
    def _execute_statement(self, node: ast.AST, code: str) -> StatementResult:
        """Execute a single AST node and return the results."""
        # Get the source code for this node
        source = ast.get_source_segment(code, node)
        
        # Prepare for capturing plots
        captured_plot = None
        def plot_callback(plot_data: PlotData):
            nonlocal captured_plot
            captured_plot = plot_data
        
        # Capture stdout/stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        output = ""
        return_value = None
        error = None
        
        try:
            with PlotCapture(plot_callback, self.default_plot_size, self.dpi):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    if isinstance(node, ast.Expr):
                        # For expressions, we want to capture the return value
                        return_value = eval(compile(ast.Expression(node.value), '<string>', 'eval'),
                                         self.globals, self.locals)
                    else:
                        # For statements, just execute them
                        exec(compile(ast.Module([node], type_ignores=[]), '<string>', 'exec'),
                             self.globals, self.locals)
                    
                    # Get output from stdout/stderr
                    output = stdout.getvalue() + stderr.getvalue()
                    
        except Exception as e:
            error = e
            output = stdout.getvalue() + stderr.getvalue()
        
        return StatementResult(source, output, return_value, captured_plot, error)
    
    def run_code(self, code: str) -> List[StatementResult]:
        """Execute a string of Python code and return the results.
        
        Args:
            code: String containing Python code to execute
            
        Returns:
            List of StatementResult objects containing execution results for each statement
        """
        results = []
        
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Execute each top-level statement
            for node in tree.body:
                result = self._execute_statement(node, code)
                results.append(result)
                
                # If there was an error, stop execution
                if result.error is not None:
                    break
                    
        except SyntaxError as e:
            # Handle syntax errors in the entire code block
            results.append(StatementResult("", "", None, None, e))
            
        return results