import * as echarts from "echarts";
import {
  Activity,
  AlertTriangle,
  Bot,
  Building2,
  CheckCircle2,
  Gauge,
  ListFilter,
  RefreshCw,
  Settings,
  Thermometer,
  Users,
  Wind,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

const envApiBase = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE;
const API_BASE = envApiBase ?? (window.location.port === "5173" ? "http://localhost:8000" : "");

type Page = "overview" | "detail" | "events" | "ai" | "settings";
type Room = { room_id: string; room_name?: string; building?: string; capacity?: number };
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
  event_id?: string;
  room_id?: string;
  summary?: string;
  impact?: string;
  suggestions?: string[];
  energy_saving?: string;
  created_at?: string;
};

const navItems: Array<{ page: Page; label: string; icon: React.ReactNode }> = [
  { page: "overview", label: "总览", icon: <Activity size={16} /> },
  { page: "detail", label: "教室详情", icon: <Gauge size={16} /> },
  { page: "events", label: "异常事件", icon: <AlertTriangle size={16} /> },
  { page: "ai", label: "AI 建议", icon: <Bot size={16} /> },
  { page: "settings", label: "模型设置", icon: <Settings size={16} /> },
];

export default function App() {
  const [activePage, setActivePage] = useState<Page>("overview");
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selectedRoom, setSelectedRoom] = useState("A101");
  const [latest, setLatest] = useState<Metric | null>(null);
  const [latestByRoom, setLatestByRoom] = useState<Record<string, Metric | null>>({});
  const [history, setHistory] = useState<Metric[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [analysisRecords, setAnalysisRecords] = useState<AIAnalysis[]>([]);
  const [apiKey, setApiKey] = useState(localStorage.getItem("llm_api_key") ?? "");
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("llm_base_url") ?? "https://api.openai.com/v1");
  const [model, setModel] = useState(localStorage.getItem("llm_model") ?? "gpt-4o-mini");
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [eventFilter, setEventFilter] = useState<"all" | "critical" | "warning" | "info">("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const roomIds = useMemo(
    () => ["A101", "A102", "B201", ...rooms.map((room) => room.room_id)].filter((value, index, arr) => arr.indexOf(value) === index),
    [rooms],
  );

  async function refresh(roomId = selectedRoom) {
    setError("");
    const [roomRes, eventRes, analysisRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/rooms`),
      fetch(`${API_BASE}/api/v1/events`),
      fetch(`${API_BASE}/api/v1/analysis`),
    ]);
    const nextRooms: Room[] = roomRes.ok ? await roomRes.json() : [];
    const nextEvents: EventItem[] = eventRes.ok ? await eventRes.json() : [];
    setRooms(nextRooms);
    setEvents(nextEvents);
    if (analysisRes.ok) setAnalysisRecords(await analysisRes.json());

    const ids = ["A101", "A102", "B201", ...nextRooms.map((room) => room.room_id)].filter(
      (value, index, arr) => arr.indexOf(value) === index,
    );
    const latestPairs = await Promise.all(
      ids.map(async (id) => {
        const response = await fetch(`${API_BASE}/api/v1/rooms/${id}/latest`);
        return [id, response.ok ? ((await response.json()) as Metric) : null] as const;
      }),
    );
    setLatestByRoom(Object.fromEntries(latestPairs));

    const selectedLatest = latestPairs.find(([id]) => id === roomId)?.[1] ?? null;
    setLatest(selectedLatest);

    const historyRes = await fetch(`${API_BASE}/api/v1/rooms/${roomId}/history`);
    setHistory(historyRes.ok ? await historyRes.json() : []);
  }

  useEffect(() => {
    refresh().catch((exc) => setError(String(exc)));
    const id = window.setInterval(() => refresh().catch(() => undefined), 5000);
    return () => window.clearInterval(id);
  }, [selectedRoom]);

  const selectedEvents = useMemo(() => events.filter((event) => event.room_id === selectedRoom), [events, selectedRoom]);
  const filteredEvents = useMemo(
    () => (eventFilter === "all" ? events : events.filter((event) => event.level === eventFilter)),
    [events, eventFilter],
  );
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
      const result = await response.json();
      setAnalysis(result);
      setActivePage("ai");
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  function saveSettings() {
    localStorage.setItem("llm_api_key", apiKey);
    localStorage.setItem("llm_base_url", baseUrl);
    localStorage.setItem("llm_model", model);
    setError("");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Building2 size={20} />
          <span>智慧教室监测</span>
        </div>
        {navItems.map((item) => (
          <button
            key={item.page}
            className={`nav ${activePage === item.page ? "active" : ""}`}
            onClick={() => setActivePage(item.page)}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{pageTitle(activePage, selectedRoom)}</h1>
            <p>端侧模拟、边缘流处理、云端存储与大模型决策建议</p>
          </div>
          <button className="refreshButton" onClick={() => refresh()}>
            <RefreshCw size={18} />
            刷新
          </button>
        </header>

        {error && <div className="error">{error}</div>}

        {activePage === "overview" && (
          <OverviewPage
            roomIds={roomIds}
            latestByRoom={latestByRoom}
            events={events}
            onSelectRoom={(roomId) => {
              setSelectedRoom(roomId);
              setActivePage("detail");
            }}
          />
        )}

        {activePage === "detail" && (
          <DetailPage
            roomIds={roomIds}
            selectedRoom={selectedRoom}
            setSelectedRoom={setSelectedRoom}
            latest={latest}
            history={history}
            events={selectedEvents}
            status={status}
            onAnalyze={analyze}
            loading={loading}
          />
        )}

        {activePage === "events" && (
          <EventsPage
            events={filteredEvents}
            filter={eventFilter}
            setFilter={setEventFilter}
            setSelectedRoom={setSelectedRoom}
            onAnalyze={analyze}
            loading={loading}
          />
        )}

        {activePage === "ai" && (
          <AIPage
            currentAnalysis={analysis}
            records={analysisRecords}
            events={events}
            onAnalyze={analyze}
            loading={loading}
          />
        )}

        {activePage === "settings" && (
          <SettingsPage
            apiKey={apiKey}
            setApiKey={setApiKey}
            baseUrl={baseUrl}
            setBaseUrl={setBaseUrl}
            model={model}
            setModel={setModel}
            onSave={saveSettings}
          />
        )}
      </main>
    </div>
  );
}

function OverviewPage(props: {
  roomIds: string[];
  latestByRoom: Record<string, Metric | null>;
  events: EventItem[];
  onSelectRoom: (roomId: string) => void;
}) {
  const criticalCount = props.events.filter((event) => event.level === "critical").length;
  const warningCount = props.events.filter((event) => event.level === "warning").length;

  return (
    <>
      <section className="summaryGrid">
        <SummaryCard label="接入教室" value={props.roomIds.length} hint="本地模拟教室数量" />
        <SummaryCard label="严重事件" value={criticalCount} hint="critical 级别" />
        <SummaryCard label="警告事件" value={warningCount} hint="warning 级别" />
        <SummaryCard label="数据来源" value="Edge" hint="边缘聚合后入云" />
      </section>
      <section className="roomGrid">
        {props.roomIds.map((roomId) => {
          const metric = props.latestByRoom[roomId];
          const roomEvents = props.events.filter((event) => event.room_id === roomId);
          const status = getStatus(metric ?? null, roomEvents);
          return (
            <button className="roomCard" key={roomId} onClick={() => props.onSelectRoom(roomId)}>
              <div className="roomCardTop">
                <strong>{roomId}</strong>
                <span className={`pill ${status}`}>{statusLabel(status)}</span>
              </div>
              <div className="roomMetrics">
                <span>温度 {metric ? `${metric.temperature.toFixed(1)} C` : "--"}</span>
                <span>CO2 {metric ? `${metric.co2.toFixed(0)} ppm` : "--"}</span>
                <span>人数 {metric ? metric.people_count : "--"}</span>
              </div>
              <div className="roomCardFooter">{roomEvents.length} 个近期事件</div>
            </button>
          );
        })}
      </section>
    </>
  );
}

function DetailPage(props: {
  roomIds: string[];
  selectedRoom: string;
  setSelectedRoom: (roomId: string) => void;
  latest: Metric | null;
  history: Metric[];
  events: EventItem[];
  status: string;
  onAnalyze: (eventId: string) => void;
  loading: boolean;
}) {
  return (
    <>
      <section className="roomTabs" aria-label="教室选择">
        {props.roomIds.map((roomId) => (
          <button
            key={roomId}
            className={props.selectedRoom === roomId ? "selected" : ""}
            onClick={() => props.setSelectedRoom(roomId)}
          >
            {roomId}
          </button>
        ))}
      </section>

      <section className="statusStrip">
        <div>
          <span className="eyebrow">当前状态</span>
          <strong className={`statusText ${props.status}`}>{statusLabel(props.status)}</strong>
        </div>
        <div>
          <span className="eyebrow">最新上报</span>
          <strong>{props.latest ? new Date(props.latest.timestamp).toLocaleTimeString() : "暂无数据"}</strong>
        </div>
        <div>
          <span className="eyebrow">近期事件</span>
          <strong>{props.events.length}</strong>
        </div>
      </section>

      <section className="metrics">
        <MetricCard icon={<Thermometer size={18} />} label="温度" value={props.latest ? `${props.latest.temperature.toFixed(1)} C` : "--"} />
        <MetricCard icon={<Wind size={18} />} label="湿度" value={props.latest ? `${props.latest.humidity.toFixed(1)}%` : "--"} />
        <MetricCard icon={<Activity size={18} />} label="CO2" value={props.latest ? `${props.latest.co2.toFixed(0)} ppm` : "--"} />
        <MetricCard icon={<Zap size={18} />} label="光照" value={props.latest ? `${props.latest.light.toFixed(0)} lux` : "--"} />
        <MetricCard icon={<Users size={18} />} label="人数" value={props.latest ? String(props.latest.people_count) : "--"} />
      </section>

      <section className="contentGrid">
        <div className="panel chartPanel">
          <div className="panelHeader">
            <h2>历史趋势</h2>
            <span>最近 100 条边缘聚合数据</span>
          </div>
          <HistoryChart history={props.history} />
        </div>
        <div className="panel">
          <div className="panelHeader">
            <h2>本教室事件</h2>
            <span>按最新时间排序</span>
          </div>
          <EventList events={props.events.slice(0, 5)} onAnalyze={props.onAnalyze} loading={props.loading} compact />
        </div>
      </section>
    </>
  );
}

function EventsPage(props: {
  events: EventItem[];
  filter: "all" | "critical" | "warning" | "info";
  setFilter: (filter: "all" | "critical" | "warning" | "info") => void;
  setSelectedRoom: (roomId: string) => void;
  onAnalyze: (eventId: string) => void;
  loading: boolean;
}) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>异常事件列表</h2>
        <div className="filterGroup">
          <ListFilter size={16} />
          {(["all", "critical", "warning", "info"] as const).map((filter) => (
            <button key={filter} className={props.filter === filter ? "selected" : ""} onClick={() => props.setFilter(filter)}>
              {filter}
            </button>
          ))}
        </div>
      </div>
      <div className="eventTable">
        <div className="tableHeader">
          <span>时间</span>
          <span>教室</span>
          <span>类型</span>
          <span>等级</span>
          <span>说明</span>
          <span>操作</span>
        </div>
        {props.events.map((event) => (
          <div className="tableRow" key={event.event_id}>
            <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
            <button className="linkButton" onClick={() => props.setSelectedRoom(event.room_id)}>{event.room_id}</button>
            <strong>{event.event_type}</strong>
            <span className={`level ${event.level}`}>{event.level}</span>
            <span>{event.message}</span>
            <button className="tableAction" disabled={props.loading} onClick={() => props.onAnalyze(event.event_id)}>
              分析
            </button>
          </div>
        ))}
        {props.events.length === 0 && <p className="empty">没有符合当前筛选条件的事件。</p>}
      </div>
    </section>
  );
}

function AIPage(props: {
  currentAnalysis: AIAnalysis | null;
  records: AIAnalysis[];
  events: EventItem[];
  onAnalyze: (eventId: string) => void;
  loading: boolean;
}) {
  const candidates = props.events.slice(0, 5);
  return (
    <div className="aiGrid">
      <section className="panel analysisPanel">
        <div className="panelHeader">
          <h2>最新 AI 建议</h2>
          <span>由用户配置的大模型接口生成</span>
        </div>
        <AnalysisBlock analysis={props.currentAnalysis ?? props.records[0]} />
      </section>
      <section className="panel">
        <div className="panelHeader">
          <h2>待分析事件</h2>
          <span>选择一个事件生成建议</span>
        </div>
        <EventList events={candidates} onAnalyze={props.onAnalyze} loading={props.loading} compact />
      </section>
      <section className="panel analysisHistory">
        <div className="panelHeader">
          <h2>历史建议</h2>
          <span>最近 100 条</span>
        </div>
        {props.records.map((record) => (
          <div className="analysisItem" key={`${record.event_id}-${record.created_at}`}>
            <b>{record.room_id} / {record.event_id}</b>
            <p>{record.summary}</p>
          </div>
        ))}
        {props.records.length === 0 && <p className="empty">还没有 AI 建议。请先在异常事件页触发分析。</p>}
      </section>
    </div>
  );
}

function SettingsPage(props: {
  apiKey: string;
  setApiKey: (value: string) => void;
  baseUrl: string;
  setBaseUrl: (value: string) => void;
  model: string;
  setModel: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <div className="settingsGrid">
      <section className="panel settingsPanel">
        <div className="panelHeader">
          <h2>大模型连接</h2>
          <span>OpenAI-compatible</span>
        </div>
        <label>API Key</label>
        <input type="password" placeholder="sk-..." value={props.apiKey} onChange={(event) => props.setApiKey(event.target.value)} />
        <label>Base URL</label>
        <input value={props.baseUrl} onChange={(event) => props.setBaseUrl(event.target.value)} />
        <label>Model</label>
        <input value={props.model} onChange={(event) => props.setModel(event.target.value)} />
        <button className="primaryButton" onClick={props.onSave}>
          <CheckCircle2 size={16} />
          保存到本地浏览器
        </button>
      </section>
      <section className="panel">
        <div className="panelHeader">
          <h2>运行说明</h2>
          <span>本地 P0</span>
        </div>
        <div className="notes">
          <p>API Key 只保存在当前浏览器 localStorage 中，触发分析时随请求发送到云端。</p>
          <p>云端也支持通过 `.env` 配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`。</p>
          <p>迁移到云服务器时，只需要将边缘服务的 `CLOUD_BASE_URL` 指向服务器云端地址。</p>
        </div>
      </section>
    </div>
  );
}

function EventList(props: {
  events: EventItem[];
  onAnalyze: (eventId: string) => void;
  loading: boolean;
  compact?: boolean;
}) {
  return (
    <div className={props.compact ? "events compact" : "events"}>
      {props.events.map((event) => (
        <div className="event" key={event.event_id}>
          <div>
            <b>{event.event_type}</b>
            <span className={`level ${event.level}`}>{event.level}</span>
            <p>{event.room_id} / {event.message}</p>
          </div>
          <button disabled={props.loading} onClick={() => props.onAnalyze(event.event_id)}>
            {props.loading ? "分析中" : "生成 AI 建议"}
          </button>
        </div>
      ))}
      {props.events.length === 0 && <p className="empty">暂无异常事件。</p>}
    </div>
  );
}

function AnalysisBlock({ analysis }: { analysis?: AIAnalysis | null }) {
  if (!analysis) return <p className="empty">还没有 AI 建议。请先在异常事件页触发分析。</p>;
  return (
    <>
      <p><b>当前问题：</b>{analysis.summary}</p>
      <p><b>可能影响：</b>{analysis.impact}</p>
      <ul>{analysis.suggestions?.map((item) => <li key={item}>{item}</li>)}</ul>
      <p><b>节能建议：</b>{analysis.energy_saving}</p>
    </>
  );
}

function SummaryCard(props: { label: string; value: number | string; hint: string }) {
  return (
    <div className="summaryCard">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
      <p>{props.hint}</p>
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
      color: ["#24745d", "#b54708", "#2563eb", "#6b7280"],
      tooltip: { trigger: "axis" },
      legend: { top: 0, right: 8, textStyle: { color: "#667085" } },
      grid: { left: 42, right: 16, top: 42, bottom: 28 },
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
        { name: "光照/10", type: "line", smooth: true, showSymbol: false, data: history.map((item) => Math.round(item.light / 10)) },
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

function statusLabel(status: string) {
  if (status === "critical") return "严重";
  if (status === "warning") return "警告";
  return "正常";
}

function pageTitle(page: Page, roomId: string) {
  if (page === "overview") return "教室总览";
  if (page === "detail") return `${roomId} 教室详情`;
  if (page === "events") return "异常事件";
  if (page === "ai") return "AI 建议";
  return "模型设置";
}
