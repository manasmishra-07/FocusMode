import { useEffect, useRef, useState } from "react";
import { api, getSession } from "./api";
export function useAgent(user) {
  const [status, setStatus] = useState("Disconnected");
  const [state, setState] = useState(null);
  const socket = useRef(null),
    pending = useRef(new Map());
  function command(type, payload = {}) {
    return new Promise((resolve, reject) => {
      if (socket.current?.readyState !== WebSocket.OPEN)
        return reject(new Error("Start your companion app, then try again."));
      const id = crypto.randomUUID();
      const timeout = setTimeout(() => {
        pending.current.delete(id);
        reject(
          new Error(
            "Agent response timed out. Check the companion before retrying.",
          ),
        );
      }, 15000);
      pending.current.set(id, { resolve, reject, timeout });
      socket.current.send(JSON.stringify({ v: 1, id, type, ...payload }));
    });
  }
  useEffect(() => {
    if (!user) return;
    let active = true,
      timer;
    const connect = () => {
      const ws = new WebSocket(
        import.meta.env.VITE_AGENT_URL || "ws://127.0.0.1:4545",
      );
      socket.current = ws;
      ws.onopen = async () => {
        if (!active) return;
        setStatus("Needs pairing");
        const credential = sessionStorage.getItem(`agent-${user.id}`);
        if (credential)
          try {
            await api("/auth/me");
            await command("authenticate", {
              credential,
              jwt: getSession()?.access,
            });
            setStatus("Connected");
          } catch {
            setStatus("Needs pairing");
          }
      };
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.state) {
          setState(message.state);
          setStatus("Connected");
        }
        const p = pending.current.get(message.id);
        if (p) {
          clearTimeout(p.timeout);
          pending.current.delete(message.id);
          message.type === "error"
            ? p.reject(new Error(message.message))
            : p.resolve(message);
        }
      };
      ws.onerror = () => setStatus("Disconnected");
      ws.onclose = () => {
        setStatus("Disconnected");
        setState(null);
        if (active) timer = setTimeout(connect, 3000);
      };
    };
    connect();
    return () => {
      active = false;
      clearTimeout(timer);
      socket.current?.close();
      pending.current.forEach((p) => {
        clearTimeout(p.timeout);
        p.reject(new Error("Connection closed"));
      });
      pending.current.clear();
    };
  }, [user?.id]);
  async function pair(code) {
    await api("/auth/me");
    const result = await command("pair", { code, jwt: getSession()?.access });
    sessionStorage.setItem(`agent-${user.id}`, result.credential);
    return result;
  }
  async function authenticatedCommand(type, payload = {}) {
    if (type === "enterFocus") {
      await api("/auth/me");
      await command("authenticate", {
        credential: sessionStorage.getItem(`agent-${user.id}`),
        jwt: getSession()?.access,
      });
    }
    return command(type, payload);
  }
  return {
    status,
    state,
    command: authenticatedCommand,
    pair,
    connected: status === "Connected",
  };
}
