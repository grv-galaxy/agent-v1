import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ComposerInput from '../components/ComposerInput.jsx';
import ConnectionToast from '../components/ConnectionToast.jsx';
import MemoryCompressionBadge from '../components/MemoryCompressionBadge.jsx';
import MessageFormatter from '../components/MessageFormatter.jsx';
import SettingsPage from './SettingsPage.jsx';

const CHAT_ENDPOINT =
  import.meta.env.VITE_CHAT_URL ||
  `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/chat`;
const CONFIG_ENDPOINT = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/config`;

const PROJECT_NAME = 'agent';
const USER_NAME = 'local';
const BRANCH_NAME = 'master';
const MESSAGE_COLUMN_WIDTH = 'max-w-[804px]';
const CONTENT_OFFSET = 'ml-[44px]';

const NAV_ITEMS = [
  { label: 'New chat', icon: 'plus' },
  { label: 'Search', icon: 'search' },
  { label: 'Plugins', icon: 'plugin' },
  { label: 'Automations', icon: 'bolt' },
  { label: 'Phone Connect', icon: 'phone', tooltip: 'Connect to phone to control remotely' },
];

const CONTEXT_PILLS = [
  { label: PROJECT_NAME },
  { label: 'Work locally', icon: 'monitor' },
  { label: BRANCH_NAME, icon: 'git' },
];

function createSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function createEmptySession() {
  const sessionId = createSessionId();
  return {
    id: sessionId,
    session_id: sessionId,
    title: 'New Chat',
    startedAt: new Date(),
    displayMessages: [], // <-- NEW: full history, rendered in UI, never pruned
    contextMessages: [], // <-- NEW: rolling window, sent to LLM, pruned on compact
    rolling_summary: "", // <-- NEW CHANGE DONE HERE
    compression_epoch: 0,
    summary_history: [],
    hasUserTitle: false,
    pinned: false,
    archived: false,
  };
}

function formatSessionTimestamp(dateValue) {
  const date = new Date(dateValue);
  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  return new Intl.DateTimeFormat(
    undefined,
    isToday ? { hour: 'numeric', minute: '2-digit' } : { month: 'short', day: 'numeric' },
  ).format(date);
}

function createSessionTitleFromContent(content) {
  const title = content.trim();
  return title.length > 40 ? `${title.slice(0, 40)}...` : title;
}

function parseSseFrames(buffer) {
  const frames = buffer.split('\n\n');
  return {
    completeFrames: frames.slice(0, -1),
    remainder: frames.at(-1) || '',
  };
}

function isNetworkError(error) {
  return (
    error?.name === 'TypeError' ||
    error?.name === 'AbortError' ||
    /failed to fetch|networkerror|load failed/i.test(error?.message || '')
  );
}

// ADD THIS NEW FUNCTION:
function getActiveMemoryConfig() {
  const defaults = { preset: 'balanced', t: 30, r: 10, cap: 800, interval: 5 };
  const saved = sessionStorage.getItem('agent_memory_config');
  
  if (!saved) return defaults;
  
  try {
    const { preset, config } = JSON.parse(saved);
    if (preset === 'custom' && config) return { preset, ...config };
    
    const PRESETS = {
      precise:  { t: 40, r: 15, cap: 1200, interval: 3 },
      balanced: { t: 30, r: 10, cap: 800,  interval: 5 },
      turbo:    { t: 15, r: 4,  cap: 500,  interval: 7 }
    };
    return { preset, ...(PRESETS[preset] || PRESETS.balanced) };
  } catch (e) {
    return defaults;
  }
}

function Icon({ name, className = 'h-4 w-4' }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    strokeWidth: '1.6',
  };

  const paths = {
    plus: (
      <>
        <path d="M8 3.5v9" {...common} />
        <path d="M3.5 8h9" {...common} />
      </>
    ),
    search: (
      <>
        <circle cx="7" cy="7" r="3.8" {...common} />
        <path d="m10 10 2.8 2.8" {...common} />
      </>
    ),
    plugin: (
      <path
        d="M6 2.8v3.1M10 2.8v3.1M4.5 6h7v2.5a3.5 3.5 0 0 1-7 0V6Zm3.5 6v1.7"
        {...common}
      />
    ),
    bolt: <path d="m8.8 1.8-5 7h3.5l-.1 5.4 5-7H8.7Z" {...common} />,
    phone: (
      <>
        <rect x="4.6" y="1.9" width="6.8" height="12.2" rx="1.5" {...common} />
        <path d="M7.2 11.8h1.6" {...common} />
      </>
    ),
    gear: (
      <>
        <circle cx="8" cy="8" r="2.1" {...common} />
        <path d="M8 1.8v1.5M8 12.7v1.5M2.6 4.9l1.3.8M12.1 10.3l1.3.8M2.6 11.1l1.3-.8M12.1 5.7l1.3-.8" {...common} />
      </>
    ),
    code: (
      <>
        <path d="m6.2 4.6-3.1 3.1 3.1 3.1" {...common} />
        <path d="m9.8 4.6 3.1 3.1-3.1 3.1" {...common} />
      </>
    ),
    layout: (
      <>
        <rect x="2.4" y="3" width="11.2" height="10" rx="1.2" {...common} />
        <path d="M6.4 3v10M2.4 6.7h11.2" {...common} />
      </>
    ),
    split: (
      <>
        <rect x="2.5" y="3" width="4.5" height="10" rx="1" {...common} />
        <rect x="9" y="3" width="4.5" height="10" rx="1" {...common} />
      </>
    ),
    panelExpand: (
      <>
        <rect x="2.4" y="3" width="11.2" height="10" rx="1.4" {...common} />
        <path d="M5.5 3v10" {...common} />
        <path d="m8.2 6.2 1.8 1.8-1.8 1.8" {...common} />
      </>
    ),
    panelCollapse: (
      <>
        <rect x="2.4" y="3" width="11.2" height="10" rx="1.4" {...common} />
        <path d="M10.5 3v10" {...common} />
        <path d="M7.8 6.2 6 8l1.8 1.8" {...common} />
      </>
    ),
    dots: (
      <>
        <circle cx="4" cy="8" r="0.9" fill="currentColor" stroke="none" />
        <circle cx="8" cy="8" r="0.9" fill="currentColor" stroke="none" />
        <circle cx="12" cy="8" r="0.9" fill="currentColor" stroke="none" />
      </>
    ),
    pin: (
      <>
        <path d="m5.4 2.8 7.8 7.8" {...common} />
        <path d="M9.8 2.8 6.6 6 5.3 9.8l.9.9L10 9.4l3.2-3.2" {...common} />
        <path d="m6.6 9.4-3.2 3.2" {...common} />
      </>
    ),
    pencil: (
      <>
        <path d="M3.5 11.8 4 9.2 10.6 2.6a1.4 1.4 0 0 1 2 2L6 11.2l-2.5.6Z" {...common} />
        <path d="m9.5 3.7 2.8 2.8" {...common} />
      </>
    ),
    chevron: <path d="m6 4 4 4-4 4" {...common} />,
    minimize: <path d="M4 8h8" {...common} />,
    maximize: <path d="M4.3 4.3h7.4v7.4H4.3z" {...common} />,
    close: (
      <>
        <path d="m4.6 4.6 6.8 6.8" {...common} />
        <path d="m11.4 4.6-6.8 6.8" {...common} />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function SidebarToggleButton({ collapsed, onClick }) {
  const label = collapsed ? 'Expand sidebar' : 'Collapse sidebar';

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="no-drag grid h-7 w-7 shrink-0 place-items-center rounded-[6px] border-0 bg-transparent text-[#666666] transition-colors duration-150 hover:bg-[#1A1A1A] hover:text-[#E8E8E8]"
    >
      <Icon name={collapsed ? 'panelExpand' : 'panelCollapse'} className="h-4 w-4" />
    </button>
  );
}

function IconButton({ label, icon, onClick, tone = 'default' }) {
  const closeTone = tone === 'danger' ? 'hover:bg-red-500/20 hover:text-red-200' : '';

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`no-drag grid h-8 w-8 place-items-center rounded-[6px] text-[#666666] transition duration-150 hover:bg-[#1A1A1A] hover:text-[#E8E8E8] ${closeTone}`}
    >
      <Icon name={icon} />
    </button>
  );
}

function SidebarNavItem({ item, onClick }) {
  const isPhoneConnect = item.label === 'Phone Connect';

  return (
    <div className="group/nav relative">
      <button
        type="button"
        aria-label={item.label}
        title={item.label}
        onClick={item.label === 'New chat' ? onClick : undefined}
        className="flex h-8 w-full items-center gap-3 rounded-[6px] px-2 text-left text-[14px] font-normal text-[#A0A0A0] transition duration-150 hover:bg-[#141414] hover:text-[#E8E8E8]"
      >
        <Icon name={item.icon} className="h-4 w-4 shrink-0 text-[#666666]" />
        <span className="truncate">{item.label}</span>
      </button>
      {isPhoneConnect ? (
        <div className="pointer-events-none absolute left-[calc(100%+8px)] top-1/2 z-50 max-w-[calc(100vw-320px)] -translate-y-1/2 overflow-hidden text-ellipsis whitespace-nowrap rounded-[6px] border border-[#2A2A2A] bg-[#1A1A1A] px-[10px] py-[6px] text-[12px] text-[#E8E8E8] opacity-0 transition-opacity delay-[400ms] duration-150 group-hover/nav:opacity-100 group-hover/nav:delay-[400ms]">
          {item.tooltip}
        </div>
      ) : null}
    </div>
  );
}

function MenuOption({ children, onClick, tone = 'default' }) {
  const dangerClass = tone === 'danger' ? 'hover:text-[#FF4444]' : '';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-8 w-full items-center rounded-[6px] px-2 text-left text-[14px] text-[#E8E8E8] transition duration-150 hover:bg-[#2A2A2A] ${dangerClass}`}
    >
      {children}
    </button>
  );
}

function SidebarSectionHeader({ children }) {
  return (
    <p className="px-2 pt-2 text-[11px] font-medium uppercase tracking-wide text-[#555555]">
      {children}
    </p>
  );
}

function SidebarSessionRow({
  session,
  active,
  menuOpen,
  pendingDelete,
  renaming,
  renameDraft,
  onArchive,
  onCancelRename,
  onCommitRename,
  onDelete,
  onMenuToggle,
  onPin,
  onRename,
  onRenameDraftChange,
  onSelect,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (renaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [renaming]);

  function handleRenameKeyDown(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      onCommitRename(session.id);
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      event.currentTarget.dataset.cancelRename = 'true';
      onCancelRename();
    }
  }

  return (
    <div
      data-session-menu-root={menuOpen ? true : undefined}
      className={`group relative flex min-h-8 items-center rounded-[5px] border-l-2 transition duration-150 ${
        active
          ? 'border-[#6366F1] bg-[#181818]'
          : 'border-transparent hover:bg-[#141414]'
      }`}
    >
      {renaming ? (
        <input
          ref={inputRef}
          value={renameDraft}
          onChange={(event) => onRenameDraftChange(event.target.value)}
          onBlur={(event) => {
            if (event.currentTarget.dataset.cancelRename === 'true') {
              return;
            }
            onCommitRename(session.id);
          }}
          onKeyDown={handleRenameKeyDown}
          className="h-8 min-w-0 flex-1 rounded-[5px] border border-[#2A2A2A] bg-[#12141C] px-2 text-[13px] text-[#E8E8E8] outline-none"
        />
      ) : (
        <button
          type="button"
          onClick={() => onSelect(session.id)}
          className="flex h-8 min-w-0 flex-1 items-center gap-1.5 rounded-[5px] py-0 pl-2 pr-8 text-left"
        >
          {session.pinned ? <Icon name="pin" className="h-3 w-3 shrink-0 text-[#6366F1]" /> : null}
          <span
            className={`min-w-0 flex-1 truncate text-[13px] transition duration-150 ${
              active ? 'text-[#E8E8E8]' : 'text-[#A0A0A0] group-hover:text-[#E8E8E8]'
            }`}
          >
            {session.title}
          </span>
          <span className="shrink-0 text-[11px] text-[#555555] transition duration-150 group-hover:opacity-0">
            {session.time}
          </span>
        </button>
      )}

      {!renaming ? (
        <button
          type="button"
          aria-label={`Open menu for ${session.title}`}
          title="Session menu"
          onClick={(event) => {
            event.stopPropagation();
            onMenuToggle(session.id);
          }}
          className="absolute right-1 hidden h-6 w-6 place-items-center rounded-[5px] text-[#666666] transition duration-150 hover:bg-[#242424] hover:text-[#E8E8E8] group-hover:grid"
        >
          <Icon name="dots" className="h-4 w-4" />
        </button>
      ) : null}

      {menuOpen ? (
        <div className="absolute right-0 top-8 z-50 flex w-40 flex-col gap-1 rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-1 shadow-[0_8px_24px_rgba(0,0,0,0.4)]">
          <MenuOption onClick={() => onPin(session.id)}>Pin chat</MenuOption>
          <MenuOption onClick={() => onRename(session)}>Rename chat</MenuOption>
          <MenuOption onClick={() => onArchive(session.id)}>Archive chat</MenuOption>
          <div className="relative">
            {pendingDelete ? (
              <div className="absolute bottom-[calc(100%+6px)] right-0 whitespace-nowrap rounded-[6px] border border-[#2A2A2A] bg-[#1A1A1A] px-2 py-1 text-[12px] text-[#E8E8E8] shadow-[0_8px_24px_rgba(0,0,0,0.4)]">
                Delete? Click again to confirm
              </div>
            ) : null}
            <MenuOption tone="danger" onClick={() => onDelete(session.id)}>
              Delete chat
            </MenuOption>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function HeaderTitle({
  editing,
  title,
  value,
  onCancel,
  onChange,
  onCommit,
  onStart,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={(event) => {
          if (event.currentTarget.dataset.cancelRename === 'true') {
            return;
          }
          onCommit();
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault();
            onCommit();
          }

          if (event.key === 'Escape') {
            event.preventDefault();
            event.currentTarget.dataset.cancelRename = 'true';
            onCancel();
          }
        }}
        className="no-drag h-7 min-w-0 max-w-sm rounded-[6px] border border-[#2A2A2A] bg-[#12141C] px-2 text-[14px] text-[#E8E8E8] outline-none"
      />
    );
  }

  return (
    <div className="group/title flex min-w-0 items-center gap-2">
      <p className="min-w-0 truncate text-[14px] font-normal text-[#CFCFCF]">{title}</p>
      <button
        type="button"
        aria-label="Rename chat"
        title="Rename chat"
        onClick={onStart}
        className="no-drag grid h-6 w-6 shrink-0 place-items-center rounded-[5px] text-[#666666] opacity-0 transition duration-150 hover:bg-[#1A1A1A] hover:text-[#E8E8E8] group-hover/title:opacity-100"
      >
        <Icon name="pencil" className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function BackendOfflineBanner({ onRetry }) {
  return (
    <div className="rounded-[12px] border border-[#EF4444] bg-[#1A1A1A] px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[14px] font-medium text-[#E8E8E8]">
          Backend offline - start the server to continue chatting
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="h-9 rounded-[8px] bg-[#6366F1] px-4 text-[13px] text-white transition duration-150 hover:bg-[#4F46E5]"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

function ToolThinkingBadge({ tool }) {
  return (
    <div className="mt-3 inline-flex items-center gap-2 rounded-[20px] border border-[#2A2A2A] bg-[#1A1A1A] px-3 py-1 text-[13px] text-[#666666]">
      <span className="h-2 w-2 rounded-full bg-[#6366F1] animate-pulse" />
      <span>Using {tool || 'tool'}...</span>
    </div>
  );
}

export default function ChatPage({
  provider,
  onProviderUpdate,
  isOnline = true,
  onlineRestoredAt = null,
}) {
  const initialSessionRef = useRef(null);
  if (!initialSessionRef.current) {
    initialSessionRef.current = createEmptySession();
  }

  const [sessions, setSessions] = useState(() => [initialSessionRef.current]);
  const [activeSessionId, setActiveSessionId] = useState(initialSessionRef.current.id);
  const [composerResetKey, setComposerResetKey] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [openMenuId, setOpenMenuId] = useState(null);
  const [renamingSessionId, setRenamingSessionId] = useState(null);
  const [renameDraft, setRenameDraft] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [archivedExpanded, setArchivedExpanded] = useState(false);
  const [headerEditing, setHeaderEditing] = useState(false);
  const [headerDraft, setHeaderDraft] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState('chat');
  const [backendConnectionState, setBackendConnectionState] = useState('connected');
  const [showBackendOfflineBanner, setShowBackendOfflineBanner] = useState(false);
  const [memoryBadgeSessionId, setMemoryBadgeSessionId] = useState(null);
  const [toolThinking, setToolThinking] = useState(null);
  const assistantMessageIdRef = useRef(0);
  const activeAssistantMessageIdRef = useRef(null);
  const interruptedMessageIdRef = useRef(null);
  const isOnlineRef = useRef(isOnline);
  const messageEndRef = useRef(null);
  const streamAbortControllerRef = useRef(null);
  const toolThinkingTimeoutRef = useRef(null);
  const toolTimeoutAbortRef = useRef(false);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ||
    sessions.find((session) => !session.archived) ||
    sessions[0];
  const displayMessages = activeSession?.displayMessages || []; // for UI rendering
  const contextMessages = activeSession?.contextMessages || []; // for API payload
  const providerLabel = provider.providerLabel || provider.provider;
  const providerInitial = (providerLabel || 'A').trim().charAt(0).toUpperCase();
  const currentChatTitle = activeSession?.title || 'New chat';
  const activeMemorySessionId = activeSession?.session_id || activeSession?.id || 'default';
  const hasMessages = displayMessages.length > 0;

  const sessionItems = useMemo(
    () =>
      sessions.map((session) => ({
        ...session,
        time: formatSessionTimestamp(session.startedAt),
      })),
    [sessions],
  );
  const pinnedSessions = sessionItems.filter((session) => session.pinned && !session.archived);
  const regularSessions = sessionItems.filter((session) => !session.pinned && !session.archived);
  const archivedSessions = sessionItems.filter((session) => session.archived);
  const isBackendLost = backendConnectionState === 'lost';
  const shouldDisableComposer = isStreaming || !isOnline || showBackendOfflineBanner;
  const composerDisabledReason = !isOnline ? 'No internet connection' : '';

  const markBackendLost = useCallback(() => {
    if (!isOnlineRef.current) {
      return;
    }

    setBackendConnectionState('lost');
  }, []);

  const checkBackendConnection = useCallback(async () => {
    if (!isOnlineRef.current) {
      return false;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch(CONFIG_ENDPOINT, { signal: controller.signal });
      if (!response.ok) {
        throw new Error('Backend check failed.');
      }

      setBackendConnectionState('reconnected');
      setShowBackendOfflineBanner(false);
      window.setTimeout(() => {
        setBackendConnectionState((current) =>
          current === 'reconnected' ? 'connected' : current,
        );
      }, 2000);
      return true;
    } catch {
      setBackendConnectionState('lost');
      return false;
    } finally {
      window.clearTimeout(timeout);
    }
  }, []);

  useEffect(() => {
    if (displayMessages.length > 0) {
      messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [displayMessages, isStreaming]);

  useEffect(() => {
    if (!memoryBadgeSessionId) {
      return undefined;
    }

    const timeout = window.setTimeout(() => setMemoryBadgeSessionId(null), 2000);
    return () => window.clearTimeout(timeout);
  }, [memoryBadgeSessionId]);

  useEffect(
    () => () => {
      if (toolThinkingTimeoutRef.current) {
        window.clearTimeout(toolThinkingTimeoutRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    isOnlineRef.current = isOnline;
  }, [isOnline]);

  useEffect(() => {
    if (!isOnline) {
      setShowBackendOfflineBanner(false);
    }
  }, [isOnline]);

  useEffect(() => {
    if (!isBackendLost || !isOnline) {
      return undefined;
    }

    const retryInterval = window.setInterval(checkBackendConnection, 5000);
    const offlineTimer = window.setTimeout(() => {
      setShowBackendOfflineBanner(true);
    }, 30000);

    return () => {
      window.clearInterval(retryInterval);
      window.clearTimeout(offlineTimer);
    };
  }, [checkBackendConnection, isBackendLost, isOnline]);

  useEffect(() => {
    if (isOnline && onlineRestoredAt) {
      checkBackendConnection();
    }
  }, [checkBackendConnection, isOnline, onlineRestoredAt]);

  useEffect(() => {
    if (isOnline || !isStreaming) {
      return;
    }

    streamAbortControllerRef.current?.abort();
    const activeAssistantId = activeAssistantMessageIdRef.current;

    if (activeAssistantId && interruptedMessageIdRef.current !== activeAssistantId) {
      interruptedMessageIdRef.current = activeAssistantId;
      updateAssistantMessage(activeAssistantId, '\n\n*-- response interrupted, connection lost*');
    }

    setIsStreaming(false);
  }, [isOnline, isStreaming]);

  useEffect(() => {
    function handlePointerDown(event) {
      if (openMenuId && !event.target.closest('[data-session-menu-root]')) {
        setOpenMenuId(null);
        setDeleteConfirmId(null);
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setOpenMenuId(null);
        setDeleteConfirmId(null);
        setRenamingSessionId(null);
        setHeaderEditing(false);
      }
    }

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [openMenuId]);

  function getFallbackSession(currentSessions) {
    return currentSessions.find((session) => !session.archived) || null;
  }

  function ensureFallbackSession(currentSessions) {
    const fallback = getFallbackSession(currentSessions);
    if (fallback) {
      return { sessions: currentSessions, activeId: fallback.id };
    }

    const emptySession = createEmptySession();
    return { sessions: [emptySession, ...currentSessions], activeId: emptySession.id };
  }

  function renameSession(sessionId, title) {
    const nextTitle = title.trim();
    if (!nextTitle) {
      return;
    }

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === sessionId
          ? { ...session, title: nextTitle, hasUserTitle: true }
          : session,
      ),
    );
  }

  function pinSession(sessionId) {
    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === sessionId ? { ...session, pinned: true, archived: false } : session,
      ),
    );
    setOpenMenuId(null);
    setDeleteConfirmId(null);
  }

  function archiveSession(sessionId) {
    const nextSessions = sessions.map((session) =>
      session.id === sessionId ? { ...session, archived: true, pinned: false } : session,
    );
    const nextState =
      sessionId === activeSessionId ? ensureFallbackSession(nextSessions) : { sessions: nextSessions, activeId: activeSessionId };

    setSessions(nextState.sessions);
    setActiveSessionId(nextState.activeId);
    setOpenMenuId(null);
    setDeleteConfirmId(null);
    resetComposerDraft();
    setErrorMessage('');
  }

  function permanentlyDeleteSession(sessionId) {
    const remainingSessions = sessions.filter((session) => session.id !== sessionId);
    const nextState =
      sessionId === activeSessionId
        ? ensureFallbackSession(remainingSessions)
        : { sessions: remainingSessions, activeId: activeSessionId };

    setSessions(nextState.sessions);
    setActiveSessionId(nextState.activeId);
    setOpenMenuId(null);
    setDeleteConfirmId(null);
    resetComposerDraft();
    setErrorMessage('');
  }

  function requestDeleteSession(sessionId) {
    if (deleteConfirmId === sessionId) {
      permanentlyDeleteSession(sessionId);
      return;
    }

    setDeleteConfirmId(sessionId);
  }

  function startSidebarRename(session) {
    setRenamingSessionId(session.id);
    setRenameDraft(session.title);
    setOpenMenuId(null);
    setDeleteConfirmId(null);
  }

  function commitSidebarRename(sessionId) {
    renameSession(sessionId, renameDraft);
    setRenamingSessionId(null);
    setRenameDraft('');
  }

  function cancelSidebarRename() {
    setRenamingSessionId(null);
    setRenameDraft('');
  }

  function startHeaderRename() {
    if (!activeSession) {
      return;
    }

    setHeaderDraft(activeSession.title);
    setHeaderEditing(true);
  }

  function commitHeaderRename() {
    if (activeSession) {
      renameSession(activeSession.id, headerDraft);
    }
    setHeaderEditing(false);
  }

  function cancelHeaderRename() {
    setHeaderDraft('');
    setHeaderEditing(false);
  }

  function resetComposerDraft() {
    setComposerResetKey((currentKey) => currentKey + 1);
  }

  function startNewChat() {
    setViewMode('chat');

    if (activeSession && (activeSession.displayMessages || []).length === 0 && !activeSession.archived) { // ✓ Fixed
      resetComposerDraft();
      setErrorMessage('');
      return;
    }

    const session = createEmptySession();
    setSessions((currentSessions) => [session, ...currentSessions]);
    setActiveSessionId(session.id);
    resetComposerDraft();
    setErrorMessage('');
  }

  function selectSession(sessionId) {
    setViewMode('chat');
    setActiveSessionId(sessionId);
    resetComposerDraft();
    setErrorMessage('');
  }

  function updateAssistantMessage(id, chunk) {
    setSessions((currentSessions) =>
      currentSessions.map((session) => ({
        ...session,
        displayMessages: (session.displayMessages || []).map((message) =>
          message.id === id
            ? { ...message, content: `${message.content}${chunk}` }
            : message,
        ),
        contextMessages: (session.contextMessages || []).map((message) =>
          message.id === id
            ? { ...message, content: `${message.content}${chunk}` }
            : message,
        ),
      })),
    );
  }

  function clearToolThinking() {
    if (toolThinkingTimeoutRef.current) {
      window.clearTimeout(toolThinkingTimeoutRef.current);
      toolThinkingTimeoutRef.current = null;
    }
    setToolThinking(null);
  }

  function getMemoryPayloadFields() {
    const fields = {
      session_id: activeMemorySessionId,
      use_memory: provider.memoryEnabled !== false,
    };

    if (provider.useSeparateMemoryProvider) {
      fields.memory_provider = provider.memoryProvider || '';
      fields.memory_model = provider.memoryModel || '';
      if (provider.memoryApiKey) {
        fields.memory_api_key = provider.memoryApiKey;
      }
    }

    return fields;
  }

  function sendMessage(submittedContent) {
    const content = (submittedContent || '').trim();
    if (!content || isStreaming || !activeSession || !isOnline || showBackendOfflineBanner) {
      return false;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    };
    const assistantMessage = {
      id: `assistant-${assistantMessageIdRef.current + 1}`,
      role: 'assistant',
      content: '',
    };
    assistantMessageIdRef.current += 1;
    activeAssistantMessageIdRef.current = assistantMessage.id;
    interruptedMessageIdRef.current = null;

    const nextDisplayMessages = [...displayMessages, userMessage]; // <-- NEW
    const nextContextMessages = [...contextMessages, userMessage]; // <-- NEW
    const shouldSetTitle = !activeSession.hasUserTitle;
    const nextTitle = shouldSetTitle
      ? createSessionTitleFromContent(content)
      : activeSession.title;

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === activeSession.id
          ? {
              ...session,
              title: nextTitle,
              hasUserTitle: true,
              displayMessages: [...nextDisplayMessages, assistantMessage], // <-- NEW
              contextMessages: [...nextContextMessages, assistantMessage], // <-- NEW
            }
          : session,
      ),
    );
    setIsStreaming(true);
    setErrorMessage('');
    clearToolThinking();

    const streamController = new AbortController();
    streamAbortControllerRef.current = streamController;

    // Set compression rules and build rolling limits dynamically
    const memoryParams = getActiveMemoryConfig();
    const TRIGGER_THRESHOLD = memoryParams.t;
    const RAW_BUFFER_SIZE = memoryParams.r;
    const ROLLING_LIMIT = memoryParams.t;

    const shouldCompress = nextContextMessages.length >= TRIGGER_THRESHOLD;
    const compressionChunk = shouldCompress
      ? nextContextMessages.slice(0, nextContextMessages.length - RAW_BUFFER_SIZE)
      : [];

    const rawBufferMessages = shouldCompress
      ? nextContextMessages.slice(-RAW_BUFFER_SIZE)
      : nextContextMessages.slice(-ROLLING_LIMIT);

    void (async () => {
      try {
        const response = await fetch(CHAT_ENDPOINT, {
          method: 'POST',
          signal: streamController.signal,
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            provider: provider.provider,
            api_key: provider.apiKey,
            model_name: provider.modelName,
            ...getMemoryPayloadFields(), // Maintain memory configuration values
            memory_preset: memoryParams.preset,
            memory_trigger_threshold: memoryParams.t,
            memory_raw_buffer: memoryParams.r,
            memory_summary_cap_tokens: memoryParams.cap,
            memory_grounding_interval: memoryParams.interval,
            rolling_summary: activeSession.rolling_summary || "", // <-- NEW: snake_case only
            compression_epoch: activeSession.compression_epoch || 0,
            summary_history: activeSession.summary_history || [],
            messages: rawBufferMessages.map(({ role, content: messageContent }) => ({
              role,
              content: messageContent,
            })),
            should_compress: shouldCompress,
            compression_chunk: compressionChunk.map(({ role, content: messageContent }) => ({
              role,
              content: messageContent,
            })),
          }),
        });

        if (!response.ok || !response.body) {
          throw new Error('Unable to start chat stream.');
        }

        if (backendConnectionState === 'lost') {
          setBackendConnectionState('reconnected');
          setShowBackendOfflineBanner(false);
          window.setTimeout(() => {
            setBackendConnectionState((current) =>
              current === 'reconnected' ? 'connected' : current,
            );
          }, 2000);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let isDone = false;

        while (!isDone) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const { completeFrames, remainder } = parseSseFrames(buffer);
          buffer = remainder;

          for (const frame of completeFrames) {
            const dataLines = frame
              .split('\n')
              .filter((line) => line.startsWith('data: '))
              .map((line) => line.slice(6));

            for (const data of dataLines) {
              if (data === '[DONE]') {
                isDone = true;
                break;
              }

              try {
                const parsed = JSON.parse(data);
                if (parsed.error) {
                  throw new Error(parsed.error);
                }
                if (parsed.type === 'error') {
                  setErrorMessage(parsed.content || 'Response was interrupted. Please try again.');
                  continue;
                }
                if (parsed.type === 'tool_thinking') {
                  setToolThinking({
                    tool: parsed.tool || 'tool',
                    messageId: assistantMessage.id,
                  });
                  if (toolThinkingTimeoutRef.current) {
                    window.clearTimeout(toolThinkingTimeoutRef.current);
                  }
                  toolThinkingTimeoutRef.current = window.setTimeout(() => {
                    setToolThinking(null);
                    setErrorMessage('Tool unavailable');
                    toolTimeoutAbortRef.current = true;
                    streamController.abort();
                  }, 10000);
                  continue;
                }
                // Handle memory compression control frame
                // Handle memory compression control frame
                if (parsed.control === "memory_compact") {
                  setSessions((currentSessions) =>
                    currentSessions.map((session) => {
                      if (session.id !== activeSession.id) return session;

                      const newHistory = [
                        ...(session.summary_history || []).slice(-2),
                        session.rolling_summary,
                      ].filter(Boolean);

                      return {
                        ...session,
                        rolling_summary: parsed.rolling_summary, // keep snake_case only — remove rollingSummary
                        contextMessages: session.contextMessages.slice(parsed.truncated_count), // <-- NEW: Prune context window only
                        // displayMessages is left completely untouched so user history is never lost!
                        compression_epoch: parsed.compression_epoch ?? ((session.compression_epoch || 0) + 1),
                        summary_history: newHistory,
                      };
                    }),
                  );
                  setMemoryBadgeSessionId(activeMemorySessionId);
                  continue;
                }
                if (parsed.memory_compressed) {
                  setMemoryBadgeSessionId(activeMemorySessionId);
                  continue;
                }
                if (parsed.chunk) {
                  clearToolThinking();
                  updateAssistantMessage(assistantMessage.id, parsed.chunk);
                }
              } catch (error) {
                if (error instanceof SyntaxError) {
                  updateAssistantMessage(assistantMessage.id, data);
                  continue;
                }
                throw error;
              }
            }
          }
        }
      } catch (error) {
        if (error?.name === 'AbortError' && toolTimeoutAbortRef.current) {
          return;
        }

        if (error?.name === 'AbortError' && !isOnlineRef.current) {
          return;
        }

        if (isNetworkError(error)) {
          markBackendLost();
          return;
        }

        setErrorMessage(error?.message || 'Chat stream failed.');
      } finally {
        setIsStreaming(false);
        streamAbortControllerRef.current = null;
        activeAssistantMessageIdRef.current = null;
        toolTimeoutAbortRef.current = false;
        clearToolThinking();
      }
    })();

    return true;
  }

  function renderSessionRows(rows) {
    return rows.map((session) => (
      <SidebarSessionRow
        key={session.id}
        session={session}
        active={session.id === activeSessionId}
        menuOpen={openMenuId === session.id}
        pendingDelete={deleteConfirmId === session.id}
        renaming={renamingSessionId === session.id}
        renameDraft={renameDraft}
        onArchive={archiveSession}
        onCancelRename={cancelSidebarRename}
        onCommitRename={commitSidebarRename}
        onDelete={requestDeleteSession}
        onMenuToggle={(sessionId) => {
          setOpenMenuId((currentId) => (currentId === sessionId ? null : sessionId));
          setDeleteConfirmId(null);
        }}
        onPin={pinSession}
        onRename={startSidebarRename}
        onRenameDraftChange={setRenameDraft}
        onSelect={selectSession}
      />
    ));
  }

  function toggleSidebar() {
    setIsSidebarCollapsed((current) => !current);
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[#0D0D0D] font-sans text-[#E8E8E8]">
      <aside
        className={`drag-region flex shrink-0 overflow-hidden bg-[#080808] transition-[width] duration-[250ms] ease-[cubic-bezier(0.4,0,0.2,1)] ${
          isSidebarCollapsed
            ? 'w-0 border-r-0'
            : 'w-[280px] border-r border-[#1F1F1F]'
        }`}
      >
        <div
          className={`flex w-[280px] min-w-[280px] flex-col bg-[#080808] transition-opacity duration-150 ${
            isSidebarCollapsed
              ? 'pointer-events-none opacity-0 delay-0'
              : 'pointer-events-auto opacity-100 delay-[200ms]'
          }`}
        >
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#1F1F1F] bg-[#080808] px-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#E8E8E8] text-xs font-semibold text-[#0D0D0D]">
                A
              </div>
              <p className="min-w-0 truncate text-[14px] font-medium text-[#E8E8E8]">Agent</p>
            </div>
            <SidebarToggleButton collapsed={false} onClick={toggleSidebar} />
          </div>

          <nav className="no-drag space-y-1 px-3 pt-4">
            {NAV_ITEMS.map((item) => (
              <SidebarNavItem key={item.label} item={item} onClick={startNewChat} />
            ))}
          </nav>

          <div className="no-drag mt-5 min-h-0 flex-1 overflow-y-auto px-3">
            <p className="px-2 text-[11px] font-medium uppercase tracking-wide text-[#555555]">
              Projects
            </p>

            <div className="mt-2 rounded-[7px] px-2 py-2">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <p className="truncate text-[14px] text-[#D6D6D6]">{PROJECT_NAME}</p>
                <p className="shrink-0 text-xs text-[#666666]">{USER_NAME}</p>
              </div>

              <div className="mt-2 space-y-1 border-l border-[#1F1F1F] pl-3">
                {pinnedSessions.length > 0 ? (
                  <>
                    <SidebarSectionHeader>Pinned</SidebarSectionHeader>
                    {renderSessionRows(pinnedSessions)}
                  </>
                ) : null}

                {regularSessions.length > 0 ? renderSessionRows(regularSessions) : null}

                {archivedSessions.length > 0 ? (
                  <div className="pt-3">
                    <button
                      type="button"
                      onClick={() => setArchivedExpanded((current) => !current)}
                      className="flex h-7 w-full items-center gap-2 rounded-[5px] px-2 text-left text-[11px] font-medium uppercase tracking-wide text-[#555555] transition duration-150 hover:bg-[#141414] hover:text-[#A0A0A0]"
                    >
                      <Icon
                        name="chevron"
                        className={`h-3.5 w-3.5 transition duration-150 ${archivedExpanded ? 'rotate-90' : ''}`}
                      />
                      Archived
                    </button>
                    {archivedExpanded ? (
                      <div className="mt-1 space-y-1">{renderSessionRows(archivedSessions)}</div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="no-drag border-t border-[#1F1F1F] p-3">
            <button
              type="button"
              aria-label="Settings"
              title="Settings"
              onClick={() => setViewMode('settings')}
              className={`flex h-8 w-full items-center gap-3 rounded-[6px] px-2 text-left text-[14px] transition duration-150 ${
                viewMode === 'settings'
                  ? 'bg-[#181818] text-[#E8E8E8]'
                  : 'text-[#A0A0A0] hover:bg-[#141414] hover:text-[#E8E8E8]'
              }`}
            >
              <Icon name="gear" className="h-4 w-4 shrink-0 text-[#666666]" />
              <span>Settings</span>
            </button>
          </div>
        </div>
      </aside>

      <section className="relative flex min-w-0 flex-1 flex-col bg-[#0D0D0D]">
        <ConnectionToast state={isOnline ? backendConnectionState : 'connected'} />
        {viewMode === 'settings' ? (
          <SettingsPage
            onBack={() => setViewMode('chat')}
            onConfigSaved={onProviderUpdate}
            onMemoryConfigSaved={onProviderUpdate}
            isOnline={isOnline}
            onBackendConnectionLost={markBackendLost}
          />
        ) : (
          <div className="app-route-fade flex min-h-0 flex-1 flex-col">
            <header className="drag-region flex h-12 shrink-0 items-center justify-between border-b border-[#1F1F1F] bg-[#111111] px-4">
              <div className="flex min-w-0 items-center gap-2">
                {isSidebarCollapsed ? (
                  <SidebarToggleButton collapsed onClick={toggleSidebar} />
                ) : null}
                <HeaderTitle
                  editing={headerEditing}
                  title={currentChatTitle}
                  value={headerDraft}
                  onCancel={cancelHeaderRename}
                  onChange={setHeaderDraft}
                  onCommit={commitHeaderRename}
                  onStart={startHeaderRename}
                />
              </div>

              <div className="flex shrink-0 items-center gap-1">
                <IconButton label="Open in VS Code" icon="code" />
                <IconButton label="Toggle layout" icon="layout" />
                <IconButton label="Split layout" icon="split" />
                <div className="mx-1 h-4 w-px bg-[#1F1F1F]" />
                <IconButton
                  label="Minimize"
                  icon="minimize"
                  onClick={() => window.desktop?.minimizeWindow?.()}
                />
                <IconButton
                  label="Maximize or restore"
                  icon="maximize"
                  onClick={() => window.desktop?.toggleMaximizeWindow?.()}
                />
                <IconButton
                  label="Close"
                  icon="close"
                  tone="danger"
                  onClick={() => window.desktop?.closeWindow?.()}
                />
              </div>
            </header>

            <div className="min-h-0 flex-1 bg-[#0D0D0D]">
              {!hasMessages ? (
                <div className="flex h-full flex-col items-center justify-center px-6 transition duration-300 ease-out max-[599px]:px-4">
                  <div className="mx-auto w-full max-w-[760px] text-center transition duration-300 ease-out">
                    <h1 className="text-[28px] font-semibold leading-tight text-[#E8E8E8]">
                      What should we build in {PROJECT_NAME}?
                    </h1>
                    <p className="mt-3 text-[14px] text-[#666666]">
                      Ask anything. Your agent is ready.
                    </p>
                    <div className="mt-8">
                      {showBackendOfflineBanner && isOnline ? (
                        <BackendOfflineBanner onRetry={checkBackendConnection} />
                      ) : (
                        <ComposerInput
                          resetKey={`${activeSessionId}:${composerResetKey}`}
                          onSubmit={sendMessage}
                          disabled={shouldDisableComposer}
                          disabledReason={composerDisabledReason}
                          contextPills={CONTEXT_PILLS}
                          className="mx-auto"
                        />
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex h-full flex-col">
                  <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-8 max-[599px]:px-4">
                    <div className={`mx-auto flex w-full ${MESSAGE_COLUMN_WIDTH} flex-col gap-8`}>
                      {displayMessages.map((message) => { // <-- NEW: map over displayMessages
                        const isUser = message.role === 'user';
                        const isStreamingAssistant =
                          isStreaming &&
                          message.role === 'assistant' &&
                          message.id === `assistant-${assistantMessageIdRef.current}`;

                        if (isUser) {
                          return (
                            <div key={message.id} className={`${CONTENT_OFFSET} flex max-w-[760px]} justify-end`}>
                              <div className="max-w-[75%] rounded-[18px_18px_4px_18px] bg-[#6366F1] px-4 py-3 text-[15px] leading-6 text-white">
                                {message.content}
                              </div>
                            </div>
                          );
                        }

                        return (
                          <div
                            key={message.id}
                            className="grid w-full grid-cols-[32px_minmax(0,760px)] gap-3"
                          >
                            <div className="flex w-8 justify-center">
                              <div className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full border border-[#2A2A2A] bg-[#1A1A1A] text-[10px] font-semibold text-[#A0A0A0]">
                                {providerInitial}
                              </div>
                            </div>
                            <div className="min-w-0 max-w-[760px]">
                              <MessageFormatter
                                content={message.content}
                                isStreaming={isStreamingAssistant}
                              />
                              {memoryBadgeSessionId === activeMemorySessionId &&
                              message.id === displayMessages[displayMessages.length - 1]?.id ? ( // <-- NEW: Use displayMessages here too
                                <MemoryCompressionBadge visible />
                              ) : null}
                              {toolThinking?.messageId === message.id ? (
                                <ToolThinkingBadge tool={toolThinking.tool} />
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                      <div ref={messageEndRef} aria-hidden="true" />
                    </div>
                  </div>

                  {errorMessage ? (
                    <div className={`mx-auto w-full ${MESSAGE_COLUMN_WIDTH} px-6 pb-3 text-sm text-red-300 max-[599px]:px-4`}>
                      <div className={`${CONTENT_OFFSET} max-w-[760px]`}>{errorMessage}</div>
                    </div>
                  ) : null}

                  <div className="sticky bottom-0 shrink-0 bg-[#0D0D0D] px-6 pb-6 pt-6 transition duration-300 ease-out max-[599px]:px-4">
                    <div className={`mx-auto w-full ${MESSAGE_COLUMN_WIDTH}`}>
                      <div className={`${CONTENT_OFFSET} max-w-[760px]`}>
                        {showBackendOfflineBanner && isOnline ? (
                          <BackendOfflineBanner onRetry={checkBackendConnection} />
                        ) : (
                          <ComposerInput
                            resetKey={`${activeSessionId}:${composerResetKey}`}
                            onSubmit={sendMessage}
                            disabled={shouldDisableComposer}
                            disabledReason={composerDisabledReason}
                            contextPills={CONTEXT_PILLS}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
