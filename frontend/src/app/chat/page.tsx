"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Bot, Send, Loader2, GraduationCap, User, Trash2, Globe, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ScholarshipMiniCard } from "@/components/scholarship/ScholarshipMiniCard";
import { useSendMessage } from "@/hooks/useChat";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  language?: string;
  scholarships?: any[];
  timestamp: Date;
  isLoading?: boolean;
}

const QUICK_PROMPTS = [
  { label: "BC Community", query: "BC community scholarships for engineering students Tamil Nadu" },
  { label: "MBC Girl Support", query: "MBC scholarship for girl students undergraduate" },
  { label: "SC/ST Assistance", query: "SC ST government scholarships" },
  { label: "Deadlines", query: "scholarships with deadlines within 30 days Tamil Nadu" },
];

const WELCOME = "Welcome! I am your scholarship guide. Tell me about your community, income, and course to find matching scholarships in Tamil Nadu.";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", role: "assistant", content: WELCOME, language: "en", scholarships: [], timestamp: new Date() }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { mutateAsync: sendMessage, isPending } = useSendMessage();

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg || isPending) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: msg, timestamp: new Date() };
    const loadingMsg: Message = { id: "loading", role: "assistant", content: "", timestamp: new Date(), isLoading: true };
    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setInput("");
    try {
      const result = await sendMessage({ message: msg, session_id: sessionId });
      setSessionId(result.session_id);
      const aiMsg: Message = { id: Date.now() + "-ai", role: "assistant", content: result.response, language: result.language, scholarships: result.scholarships || [], timestamp: new Date() };
      setMessages(prev => [...prev.filter(m => m.id !== "loading"), aiMsg]);
    } catch {
      setMessages(prev => [...prev.filter(m => m.id !== "loading"), { id: "err-" + Date.now(), role: "assistant", content: "Error occurred. Please try again.", timestamp: new Date() }]);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="gov-stripe" />
      <header className="bg-white border-b shadow-sm flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-muted-foreground hover:text-foreground p-1.5 rounded-md hover:bg-muted">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="w-8 h-8 bg-blue-800 rounded-lg flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="font-display font-semibold text-blue-900 text-sm">TamilScholar AI</p>
              <p className="text-xs text-green-600 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block" />Online · Llama 3 70B
              </p>
            </div>
          </div>
          <button onClick={() => { setMessages([]); setSessionId(null); }} className="text-muted-foreground hover:text-destructive p-1.5 rounded-md hover:bg-muted">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          {messages.map(msg => (
            <div key={msg.id} className={"flex gap-3 animate-slide-up " + (msg.role === "user" ? "flex-row-reverse" : "flex-row")}>
              <div className={"w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center " + (msg.role === "user" ? "bg-blue-700" : "bg-orange-100 border border-orange-200")}>
                {msg.role === "user" ? <User className="w-4 h-4 text-white" /> : <GraduationCap className="w-4 h-4 text-orange-700" />}
              </div>
              <div className={"flex flex-col gap-2 max-w-[80%] " + (msg.role === "user" ? "items-end" : "items-start")}>
                {msg.isLoading ? (
                  <div className="chat-bubble-ai"><div className="flex gap-1.5 py-1"><div className="typing-dot"/><div className="typing-dot"/><div className="typing-dot"/></div></div>
                ) : (
                  <div className={msg.role === "user" ? "chat-bubble-user" : "chat-bubble-ai"}>
                    <p className={"text-sm whitespace-pre-wrap " + (msg.language === "ta" ? "font-tamil" : "")}>{msg.content}</p>
                  </div>
                )}
                {msg.scholarships && msg.scholarships.length > 0 && (
                  <div className="w-full space-y-2 mt-1">
                    {msg.scholarships.slice(0,4).map((s:any) => <ScholarshipMiniCard key={s.id} scholarship={s} />)}
                  </div>
                )}
                <span className="text-xs text-muted-foreground px-1">{msg.timestamp.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}</span>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {messages.length <= 1 && (
        <div className="max-w-4xl mx-auto px-4 pb-3 w-full">
          <p className="text-xs text-muted-foreground mb-2 text-center">Quick start:</p>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_PROMPTS.map(p => (
              <button key={p.label} onClick={() => handleSend(p.query)} className="text-left p-3 bg-card border border-border rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-all text-xs">
                <p className="font-medium">{p.label}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-shrink-0 bg-white border-t">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex gap-2 items-end">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();handleSend();} }}
              placeholder="Ask about scholarships in English..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-border bg-muted/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-muted-foreground"
              disabled={isPending}
            />
            <button onClick={() => handleSend()} disabled={!input.trim()||isPending}
              className="w-12 h-12 rounded-xl bg-blue-700 hover:bg-blue-800 disabled:bg-muted text-white flex items-center justify-center transition-colors flex-shrink-0">
              {isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2">Powered by Llama 3 70B · BGE-M3 · Pinecone</p>
        </div>
      </div>
    </div>
  );
}
