$(document).on("click", "span.suggested-prompt", function(e) {
  e.preventDefault();
  const prompt = e.target.textContent;
    if (prompt) {
    const chat_container = $(e.target).parents("shiny-chat-container")[0];
    if (chat_container) {
      chat_container.input.setInputValue(prompt);
    }
  }
});
