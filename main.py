import React, { useState, useEffect, useRef } from "react";
import Layout from "../../../layout";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function UserTutorChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [userId, setUserId] = useState(null);
  const [userName, setUserName] = useState("");
  const [yearGroup, setYearGroup] = useState("");
  const scrollRef = useRef(null);

  // Generate userId on mount
  useEffect(() => {
    const id = `user_${Math.random().toString(36).substr(2, 9)}`;
    setUserId(id);

    // Kick off chat by sending first message to /ask
    const initChat = async () => {
      try {
        const res = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            agentId: "asst_TPio94mmgxvIfBBOJGrV51z5",
            message: "Hi! I'm your personal AI tutor. What’s your name?",
            threadId: null, // ❗ Let backend create the thread
            userId: id,
            userName: "",
            yearGroup: ""
          }),
        });

        const data = await res.json();
        setThreadId(data.threadId); // 🧠 Capture returned threadId
        setMessages([{ role: "assistant", content: data.response || "⚠️ No reply" }]);
      } catch (err) {
        console.error("Init chat error:", err);
        setMessages([{ role: "assistant", content: "⚠️ Failed to start chat." }]);
      }
    };

    initChat();
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    // Extract name/yearGroup heuristics
    if (!userName && userMessage.toLowerCase().includes("my name is")) {
      const name = userMessage.split("my name is")[1]?.trim().split(" ")[0];
      if (name) setUserName(name);
    }
    if (!yearGroup && userMessage.toLowerCase().includes("year")) {
      const match = userMessage.match(/year\s*(\d+)/i);
      if (match) setYearGroup("Year " + match[1]);
    }

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: "asst_TPio94mmgxvIfBBOJGrV51z5",
          message: userMessage,
          threadId,
          userId,
          userName,
          yearGroup,
        }),
      });

      const data = await res.json();
      const reply = data.response || "🤖 (No reply)";
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);

      // Update threadId in case backend created it just now
      if (!threadId && data.threadId) setThreadId(data.threadId);
    } catch (err) {
      console.error("Send error:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Error sending message." },
      ]);
    }

    setLoading(false);
    setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, 100);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Layout>
      <div className="flex flex-col h-screen bg-gray-50 font-avenir">
        <div className="bg-white shadow-sm px-6 h-20 flex items-center sticky top-0 z-20">
          <h1 className="text-xl font-bold text-[var(--trust-green)]">
            Your Personal Tutor
          </h1>
        </div>

        <div
          className="flex-1 overflow-y-auto px-6 py-6 space-y-4 custom-scrollbar"
          ref={scrollRef}
        >
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`max-w-[70%] rounded-lg px-4 py-2 whitespace-pre-wrap text-sm ${
                msg.role === "user"
                  ? "ml-auto bg-green-600 text-white"
                  : "bg-white text-gray-800 shadow"
              }`}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          ))}
          {loading && (
            <div className="text-sm italic text-gray-400">Your tutor is typing...</div>
          )}
        </div>

        <div className="bg-white border-t px-6 py-4 flex gap-2 sticky bottom-0">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message here..."
            className="flex-1 resize-none rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-[var(--trust-green)] text-white px-4 py-2 rounded-md text-sm font-semibold hover:bg-green-800"
          >
            Send
          </button>
        </div>

        <style>{`
          .custom-scrollbar {
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
          }
          .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: transparent;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background-color: #cbd5e1;
            border-radius: 3px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background-color: #94a3b8;
          }
        `}</style>
      </div>
    </Layout>
  );
}
