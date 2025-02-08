from dotenv import load_dotenv

load_dotenv()

import base64
from pathlib import Path

from chatlas import ChatAnthropic, ChatOpenAI
from shiny import App, reactive, render, req, ui

from executor import ExecutionContext

here = Path(__file__).parent

app_ui = ui.page_fluid(
    ui.tags.link(rel="stylesheet", href="style.css"),
    ui.tags.script(src="script.js"),
    ui.chat_ui("chat")
)


def server(input, output, session):

    # TODO: Move this to the top level. It's here temporarily for ease of iteration.
    with open("prompt.md", "r") as f:
        system_prompt = f.read()

    chat = ui.Chat("chat")
    chat_session = ChatAnthropic(
        system_prompt=system_prompt, model="claude-3-5-sonnet-latest"
    )
    # chat_session = ChatOpenAI(
    #     system_prompt=system_prompt, model="o3-mini"
    # )

    dpi = 100
    size_inches = (640/dpi, 480/dpi)  # (8, 6) inches
    ec = ExecutionContext(default_plot_size=size_inches, dpi=dpi)

    @chat_session.register_tool
    async def run_python_code(code: str):
        """Executes Python code in the current session"""

        stream_id = chat._current_stream_id

        async def emit(content: str) -> None:
            await chat._append_message(
                {
                    "type": "assistant",
                    "content": content,
                },
                chunk=True,
                stream_id=stream_id,
            )

        await emit(f"\n\n```python\n{code}\n```\n")

        results = []
        await emit("\n```text\n")
        try:
            for result in ec.run_code(code):
                # For human
                if result.output:
                    await emit(result.output)
                return_value_repr = result.return_value.__repr__() if result.return_value is not None else None
                if result.return_value is not None:
                    await emit(return_value_repr + "\n")
                if result.error is not None:
                    # TODO: Traceback
                    await emit("Error: " + str(result.error) + "\n")
                if result.plot_data is not None:
                    # Form data URI from result.plot_data raw bytes
                    encoded = base64.b64encode(result.plot_data.png_data).decode('utf-8')
                    data_uri = f"data:image/png;base64,{encoded}"
                    img_tag = f'<img src="{data_uri}" alt="Plot">'
                    await emit("\n```\n\n" + img_tag + "\n\n```\n")

                # For model
                results.append({
                    "source": result.source,
                    "output": result.output,
                    "return_value": return_value_repr,
                    "success": result.error is None
                })
        finally:
            await emit("```\n")

        return results

    @chat.on_user_submit
    async def on_user_submit():
        response = await chat_session.stream_async(chat.user_input(), echo="all")
        await chat.append_message_stream(response)

    @reactive.Effect
    async def kickstart():
        response = await chat_session.stream_async("Hello", echo="all")
        await chat.append_message_stream(response)

app = App(app_ui, server, static_assets=here / "www")