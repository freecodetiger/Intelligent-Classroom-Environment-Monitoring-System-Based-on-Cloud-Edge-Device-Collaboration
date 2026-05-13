import * as echarts from "echarts";
import {
  Activity,
  AlertTriangle,
  Bot,
  Building2,
  RefreshCw,
  Settings,
  Thermometer,
  Users,
  Wind,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE ?? "http://localhost:8000";

type Room = { room_id: string; room_name?: string };
type Metric = {
  room_id: string;
  temperature: number;
  humidity: number;
  co2: number;
  light: number;
  people_count: number;
  timestamp: string;
};
type EventItem = {
  event_id: string;
  room_id: string;
  event_type: string;
  level: string;
  message: string;
  timestamp: string;
  metrics: Record<string, unknown>;
};
type AIAnalysis = {
  summary?: string;
  impact?: string;
  suggestions?: string[];
  energy_saving?: string;
};

export default function App() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selectedRoom, setSelectedRoom] = useState("A101");
  const [latest, setLatest] = useState<Metric | null>(null);
  const [history, setHistory] = useState<Metric[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [apiKey, setApiKey] = useState(localStorage.getItem("llm_api_key") ?? "");
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("llm_base_url") ?? "https://api.openai.com/v1");
  const [model, setModel] = useState(localStorage.getItem("llm_model") ?? "gpt-4o-mini");
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function refresh(roomId = selectedRoom) {
    setError("");
    const [roomRes, eventRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/rooms`),
      fetch(`${API_BASE}/api/v1/events`),
    ]);
    if (roomRes.ok) setRooms(await roomRes.json());
    if (eventRes.ok) setEvents(await eventRes.json());

    const latestRes = await fetch(`${API_BASE}/api/v1/rooms/${roomId}/latest`);
    setLatest(latestRes.ok ? await latestRes.json() : null);

    const historyRes = await fetch(`${API_BASE}/api/v1/rooms/${roomId}/history`);
    setHistory(historyRes.ok ? await historyRes.json() : []);
  }

  useEffect(() => {
    refresh().catch((exc) => setError(String(exc)));
    const id = window.setInterval(() => refresh().catch(() => undefined), 5000);
    return () => window.clearInterval(id);
  }, [selectedRoom]);

  const roomIds = useMemo(
    () => ["A101", "A102", "B201", ...rooms.map((room) => room.room_id)].filter((value, index, arr) => arr.indexOf(value) === index),
    [rooms],
  );
  const selectedEvents = useMemo(() => events.filter((event) => event.room_id === selectedRoom), [events, selectedRoom]);
  const status = getStatus(latest, selectedEvents);

  async function analyze(eventId: string) {
    localStorage.setItem("llm_api_key", apiKey);
    localStorage.setItem("llm_base_url", baseUrl);
    localStorage.setItem("llm_model", model);
    setError("");
    setAnalysis(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/events/${eventId}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model }),
      });
      if (!response.ok) {
        const body = await response.json();
        setError(body.detail ?? "AI analysis failed");
        return;
      }
      setAnalysis(await response.json());
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Building2 size={20} />
          <span>智慧教室监测</span>
        </div>
        <button className="nav active"><Activity size={16} />总览</button>
        <button className="nav"><AlertTriangle size={16} />异常事件</button>
        <button className="nav"><Bot size={16} />AI 建议</button>
        <button className="nav"><Settings size={16} />模型设置</button>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{selectedRoom} 实时环境</h1>
            <p>端侧模拟、边缘流处理、云端存储与大模型决策建议</p>
          </div>
          <button className="refreshButton" onClick={() => refresh()}>
            <RefreshCw size={18} />
            刷新
          </button>
        </header>

        {error && <div className="error">{error}</div>}

        <section className="roomTabs" aria-label="教室选择">
          {roomIds.map((roomId) => (
            <button
              key={roomId}
              className={selectedRoom === roomId ? "selected" : ""}
              onClick={() => setSelectedRoom(roomId)}
            >
              {roomId}
            </button>
          ))}
        </section>

        <section className="statusStrip">
          <div>
            <span className="eyebrow">当前状态</span>
            <strong className={`statusText ${status}`}>{status === "normal" ? "正常" : status === "critical" ? "严重" : "警告"}</strong>
          </div>
          <div>
            <span className="eyebrow">最新上报</span>
            <strong>{latest ? new Date(latest.timestamp).toLocaleTimeString() : "暂无数据"}</strong>
          </div>
          <div>
            <span className="eyebrow">近期事件</span>
            <strong>{selectedEvents.length}</strong>
          </div>
        </section>

        <section className="metrics">
          <MetricCard icon={<Thermometer size={18} />} label="温度" value={latest ? `${latest.temperature.toFixed(1)} C` : "--"} />
          <MetricCard icon={<Wind size={18} />} label="湿度" value={latest ? `${latest.humidity.toFixed(1)}%` : "--"} />
          <MetricCard icon={<Activity size={18} />} label="CO2" value={latest ? `${latest.co2.toFixed(0)} ppm` : "--"} />
          <MetricCard icon={<Zap size={18} />} label="光照" value={latest ? `${latest.light.toFixed(0)} lux` : "--"} />
          <MetricCard icon={<Users size={18} />} label="人数" value={latest ? String(latest.people_count) : "--"} />
        </section>

        <section className="contentGrid">
          <div className="panel chartPanel">
            <div className="panelHeader">
              <h2>历史趋势</h2>
              <span>最近 100 条边缘聚合数据</span>
            </div>
            <HistoryChart history={history} />
          </div>

          <div className="panel settingsPanel">
            <div className="panelHeader">
              <h2>模型设置</h2>
              <span>OpenAI-compatible</span>
            </div>
            <label>API Key</label>
            <input type="password" placeholder="sk-..." value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
            <label>Base URL</label>
            <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
            <label>Model</label>
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </div>
        </section>

        <section className="panel">
          <div className="panelHeader">
            <h2>异常事件</h2>
            <span>由边缘滑动窗口检测生成</span>
          </div>
          <div className="events">
            {selectedEvents.map((event) => (
              <div className="event" key={event.event_id}>
                <div>
                  <b>{event.event_type}</b>
                  <span className={`level ${event.level}`}>{event.level}</span>
                  <p>{event.message}</p>
                </div>
                <button disabled={loading} onClick={() => analyze(event.event_id)}>
                  {loading ? "分析中" : "生成 AI 建议"}
                </button>
              </div>
            ))}
            {selectedEvents.length === 0 && <p className="empty">暂无异常事件。启动 mixed 模式模拟器后会出现数据。</p>}
          </div>
        </section>

        {analysis && (
          <section className="panel analysisPanel">
            <div className="panelHeader">
              <h2>AI 建议</h2>
              <span>来自用户配置的大模型接口</span>
            </div>
            <p><b>当前问题：</b>{analysis.summary}</p>
            <p><b>可能影响：</b>{analysis.impact}</p>
            <ul>{analysis.suggestions?.map((item) => <li key={item}>{item}</li>)}</ul>
            <p><b>节能建议：</b>{analysis.energy_saving}</p>
          </section>
        )}
      </main>
    </div>
  );
}

function MetricCard(props: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      <div className="metricIcon">{props.icon}</div>
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function HistoryChart({ history }: { history: Metric[] }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      color: ["#24745d", "#b54708", "#2563eb"],
      tooltip: { trigger: "axis" },
      grid: { left: 42, right: 16, top: 20, bottom: 28 },
      xAxis: {
        type: "category",
        data: history.map((item) => new Date(item.timestamp).toLocaleTimeString()),
        axisLabel: { color: "#667085", fontSize: 11 },
      },
      yAxis: { type: "value", axisLabel: { color: "#667085", fontSize: 11 }, splitLine: { lineStyle: { color: "#e6edf3" } } },
      series: [
        { name: "温度", type: "line", smooth: true, showSymbol: false, data: history.map((item) => item.temperature) },
        { name: "CO2/100", type: "line", smooth: true, showSymbol: false, data: history.map((item) => Math.round(item.co2 / 100)) },
        { name: "人数", type: "line", smooth: true, showSymbol: false, data: history.map((item) => item.people_count) },
      ],
    });
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [history]);

  return <div ref={ref} className="chart" />;
}

function getStatus(latest: Metric | null, events: EventItem[]) {
  if (events.some((event) => event.level === "critical")) return "critical";
  if (events.some((event) => event.level === "warning")) return "warning";
  if (latest && (latest.co2 > 1000 || latest.temperature > 28 || latest.people_count > 50)) return "warning";
  return "normal";
}
