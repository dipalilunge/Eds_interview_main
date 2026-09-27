document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('faq-form');
  const input = document.getElementById('faq-input');
  const log = document.getElementById('faq-log');
  if (!form || !input || !log) return;

  const addMessage = (text, who) => {
    const div = document.createElement('div');
    div.className = `faq-msg faq-msg--${who}`;
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  };

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    addMessage(question, 'user');
    input.value = '';

    try {
      const res = await fetch('/api/faq', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      addMessage(data.answer, 'bot');
    } catch (err) {
      addMessage("Something went wrong reaching the assistant — please try again.", 'bot');
    }
  });
});
