import React, { useState, useRef, useEffect } from "react";
import { api } from "../api.js";

const SUGGESTIONS = [
  "How much revenue is at risk?",
  "How much can we recover?",
  "Start recovery",
  "How much have we recovered?",
];

export default function Chat({ onRefresh }) {
  const [messages, setMessages] = useState([
    {
      role: "bot",
      text: "Ask me about revenue at risk, what's recoverable, or tell me to start recovery. I'm the same engine as the dashboard — the chat is just another door into it.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setBusy(true);
    try {
      const res = await api.chat(msg);
      setMessages((m) => [...m, { role: "bot", text: res.reply }]);
      onRefresh && onRefresh();
    } catch {
      setMessages((m) => [...m, { role: "bot", text: "Couldn't reach the backend." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <h3>Ask RecoverAI</h3>
      <div className="chat">
        <div className="chat-log" ref={logRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.text}
            </div>
          ))}
        </div>
        <div className="suggested">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => send(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
        <div className="chat-input">
          <input
            value={input}
            placeholder="Ask a question or give an instruction…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn" onClick={() => send()} disabled={busy}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
