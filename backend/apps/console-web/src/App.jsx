import { useEffect, useState } from "react";

const emptyChat = { id: "", citizenId: "", countryCode: "", status: "", messages: [] };

export default function App() {
  const [events, setEvents] = useState([]);
  const [chatId, setChatId] = useState("");
  const [chat, setChat] = useState(emptyChat);
  const [status, setStatus] = useState("SSE connecting...");

  useEffect(() => {
    const source = new EventSource("/api/events/stream");

    source.onopen = () => setStatus("SSE connected");
    source.onerror = () => setStatus("SSE disconnected or retrying");

    ["CONNECTED", "CHAT_CREATED", "CHAT_MESSAGE_CREATED", "AGENT_RESULT_READY"].forEach((eventName) => {
      source.addEventListener(eventName, (event) => {
        const nextEvent = {
          name: eventName,
          data: event.data,
          receivedAt: new Date().toLocaleTimeString(),
        };
        setEvents((current) => [nextEvent, ...current].slice(0, 20));

        if (eventName !== "CONNECTED") {
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.chatSessionId) {
              setChatId(parsed.chatSessionId);
              loadChat(parsed.chatSessionId);
            }
          } catch {
            // Ignore non-JSON event payloads.
          }
        }
      });
    });

    return () => source.close();
  }, []);

  async function loadChat(targetChatId = chatId) {
    if (!targetChatId) return;
    const response = await fetch(`/api/chats/${targetChatId}`);
    if (!response.ok) {
      setStatus(`Chat lookup failed: ${response.status}`);
      return;
    }
    setChat(await response.json());
  }

  return (
    <main className="page">
      <section className="panel">
        <h1>MOFA Staff Console Test</h1>
        <p>{status}</p>
        <div className="row">
          <input
            value={chatId}
            onChange={(event) => setChatId(event.target.value)}
            placeholder="chatId"
          />
          <button onClick={() => loadChat()}>Load Chat</button>
        </div>
      </section>

      <section className="grid">
        <div className="panel">
          <h2>Realtime Events</h2>
          {events.length === 0 && <p>No events yet.</p>}
          {events.map((event, index) => (
            <article className="item" key={`${event.receivedAt}-${index}`}>
              <strong>{event.name}</strong>
              <small>{event.receivedAt}</small>
              <pre>{event.data}</pre>
            </article>
          ))}
        </div>

        <div className="panel">
          <h2>Chat Detail</h2>
          {chat.id ? (
            <>
              <p>
                {chat.citizenId} / {chat.countryCode} / {chat.status}
              </p>
              {chat.messages.map((message) => (
                <article className="item" key={message.id}>
                  <strong>{message.senderType}</strong>
                  <p>{message.content}</p>
                </article>
              ))}
            </>
          ) : (
            <p>No chat loaded.</p>
          )}
        </div>
      </section>
    </main>
  );
}
