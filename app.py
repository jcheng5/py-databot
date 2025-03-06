import base64
import json
import os
from pathlib import Path

import pystache
from chatlas import ChatAnthropic
from chatlas.types import ContentImageInline, ContentText, ContentToolResult
from dotenv import load_dotenv
from shiny import App, reactive, ui

from executor import ExecutionContext, render_value

load_dotenv()

here = Path(__file__).parent

app_ui = ui.page_fluid(
    ui.tags.link(rel="stylesheet", href="style.css"),
    ui.tags.script(src="script.js"),
    ui.chat_ui("chat"),
)


def server(input, output, session):

    # TODO: Move this to the top level. It's here temporarily for ease of iteration.
    has_llms_txt = os.path.exists("llms.txt")
    if has_llms_txt:
        with open("llms.txt", "r") as f:
            llms_txt = f.read()
    else:
        llms_txt = None
    with open("prompt.md", "r") as f:
        system_prompt_template = f.read()
        system_prompt = pystache.render(
            system_prompt_template,
            {
                "has_llms_txt": has_llms_txt,
                "llms_txt": llms_txt,
            },
        )

    chat = ui.Chat("chat")
    chat_session = ChatAnthropic(
        system_prompt=system_prompt, model="claude-3-5-sonnet-latest"
    )
    # chat_session = ChatOpenAI(
    #     system_prompt=system_prompt, model="o3-mini"
    # )

    dpi = 100
    size_inches = (640 / dpi, 480 / dpi)
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
        last_error = None
        await emit("\n```text\n")
        try:
            for result in ec.run_code(code):
                return_value_repr = None

                # For human
                if result.output:
                    await emit(result.output)
                if result.return_value is not None:
                    user_value, model_value = render_value(result.return_value)
                    await emit(user_value + "\n")
                    return_value_repr = model_value
                if result.error is not None:
                    # TODO: Traceback
                    last_error = result.error
                    await emit("Error: " + str(result.error) + "\n")
                if result.plot_data is not None:
                    # Form data URI from result.plot_data raw bytes
                    encoded = base64.b64encode(result.plot_data.png_data).decode(
                        "utf-8"
                    )
                    data_uri = f"data:image/png;base64,{encoded}"
                    img_tag = f'<img class="result-plot" src="{data_uri}" alt="Plot">'
                    await emit("\n```\n\n" + img_tag + "\n\n```\n")

                # For model
                results.append(
                    ContentText(
                        json.dumps(
                            {
                                k: v
                                for k, v in {
                                    "source": result.source,
                                    "output": result.output,
                                    "return_value": return_value_repr,
                                    "success": result.error is None,
                                    "error": (
                                        str(result.error) if result.error else None
                                    ),
                                }.items()
                                if v is not None
                            }
                        )
                    )
                )
                if result.plot_data is not None:
                    results.append(ContentImageInline("image/png", encoded))
        finally:
            await emit("```\n")
        
        if last_error is not None:
            # Anthropic doesn't accept images if there's an error. Need to strip
            # them out, which is unfortunate.
            # TODO: At least let the model know an image was redacted
            results = [r for r in results if not isinstance(r, ContentImageInline)]

        return ContentToolResult("", results, last_error)

    @chat.on_user_submit
    async def on_user_submit():
        response = await chat_session.stream_async(chat.user_input())
        await chat.append_message_stream(response)

    @reactive.Effect
    async def kickstart():
        response = await chat_session.stream_async("Hello")
        await chat.append_message_stream(response)


app = App(app_ui, server, static_assets=here / "www")
