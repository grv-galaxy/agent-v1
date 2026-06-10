import { useEffect, useMemo, useRef, useState } from 'react';
import {
  FieldIcon,
  FieldLabel,
  ProviderSelect,
  Spinner,
  findProvider,
  isNetworkError,
} from './LLMConfigCard.jsx';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const CONFIG_ENDPOINT = `${API_BASE_URL}/api/config`;
const MEMORY_CONFIG_ENDPOINT = `${API_BASE_URL}/api/memory-config`;
const MEMORY_STATS_ENDPOINT = `${API_BASE_URL}/api/memory-stats`;
const MONITOR_UI_URL = 'http://127.0.0.1:5174';
const MONITOR_CONTROL_ENDPOINT = `${API_BASE_URL}/api/monitor-control`;
const MEMORY_MONITORING_STORAGE_KEY = 'agent.memoryMonitoringEnabled';
const VERIFY_ENDPOINT =
  import.meta.env.VITE_VERIFY_PROVIDER_URL || `${API_BASE_URL}/api/verify-provider`;

function SectionTitle({ children }) {
  return (
    <h2 className="mb-6 border-b border-[#1F1F1F] pb-3 text-[16px] font-medium text-[#E8E8E8]">
      {children}
    </h2>
  );
}

function ToggleSwitch({ checked, disabled = false }) {
  return (
    <span
      aria-hidden="true"
      className={`relative block h-6 w-11 rounded-[12px] transition-[background-color] duration-200 ${
        checked ? 'bg-[#6366F1]' : 'bg-[#2A2A2A]'
      } ${disabled ? 'opacity-40' : ''}`}
    >
      <span
        className={`absolute top-[3px] h-[18px] w-[18px] rounded-full bg-white transition-transform duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] ${
          checked ? 'translate-x-[23px]' : 'translate-x-[3px]'
        }`}
      />
    </span>
  );
}

function ToggleRow({ checked, disabled = false, label, description, onChange }) {
  function handleToggle() {
    if (!disabled) {
      onChange(!checked);
    }
  }

  return (
    <div
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={handleToggle}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleToggle();
        }
      }}
      className={`flex w-full cursor-pointer flex-row items-start justify-between gap-4 ${
        disabled ? 'cursor-not-allowed opacity-40' : ''
      }`}
    >
      <div className="flex flex-1 flex-col gap-1">
        <p className="text-[15px] font-medium text-[#E8E8E8]">{label}</p>
        {description ? (
          <p className="max-w-[480px] text-[13px] leading-[1.5] text-[#666666]">
            {description}
          </p>
        ) : null}
      </div>
      <span className="mt-0.5 shrink-0 self-start">
        <ToggleSwitch checked={checked} disabled={disabled} />
      </span>
    </div>
  );
}

function InfoStatLine({ children }) {
  return (
    <p className="flex items-center gap-2 text-[13px] text-[#666666]">
      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#6366F1]" />
      <span>{children}</span>
    </p>
  );
}

function StatLine({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 text-[13px]">
      <span className="text-[#666666]">{label}</span>
      <span className="font-medium text-[#E8E8E8]">{value}</span>
    </div>
  );
}

function MemoryMonitorCard() {
  function readStoredMonitoringEnabled() {
    try {
      return window.localStorage.getItem(MEMORY_MONITORING_STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  }

  function storeMonitoringEnabled(nextValue) {
    try {
      window.localStorage.setItem(MEMORY_MONITORING_STORAGE_KEY, nextValue ? 'true' : 'false');
    } catch {
      // Ignore storage failures; the current UI state still updates for this session.
    }
  }

  const [memoryMonitoringEnabled, setMemoryMonitoringEnabled] = useState(() => {
    return readStoredMonitoringEnabled();
  });
  const [monitorStatus, setMonitorStatus] = useState('idle');
  const [controlStatus, setControlStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const pollTimerRef = useRef(null);
  const pollStartedAtRef = useRef(0);

  function clearMonitorPoll() {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

  async function fetchControlStatus() {
    const response = await fetch(`${MONITOR_CONTROL_ENDPOINT}/status`);
    const data = await response.json();
    if (!response.ok || data?.success === false) {
      throw new Error(data?.message || 'Unable to read monitor status.');
    }
    setControlStatus(data.status || null);
    return data.status || null;
  }

  function updateStatusFromControl(nextStatus) {
    if (nextStatus?.force_disabled) {
      clearMonitorPoll();
      setMemoryMonitoringEnabled(false);
      storeMonitoringEnabled(false);
      setMonitorStatus('force_disabled');
      setStatusMessage('Memory monitoring is disabled by DISABLE_MEMORY_MONITOR=true');
      return true;
    }

    if (nextStatus?.collector_running && nextStatus?.frontend_running) {
      clearMonitorPoll();
      setMonitorStatus('running');
      setStatusMessage('');
      return true;
    }

    return false;
  }

  function startStatusPolling() {
    clearMonitorPoll();
    pollStartedAtRef.current = Date.now();
    pollTimerRef.current = window.setInterval(async () => {
      try {
        const nextStatus = await fetchControlStatus();
        if (updateStatusFromControl(nextStatus)) {
          return;
        }
        if (Date.now() - pollStartedAtRef.current > 20000) {
          clearMonitorPoll();
          setMonitorStatus('failed');
          setStatusMessage('Monitor failed to start');
        }
      } catch (error) {
        if (Date.now() - pollStartedAtRef.current > 20000) {
          clearMonitorPoll();
          setMonitorStatus('failed');
          setStatusMessage(error?.message || 'Monitor failed to start');
        }
      }
    }, 1500);
  }

  async function startMonitor({ persist = true } = {}) {
    clearMonitorPoll();
    setMemoryMonitoringEnabled(true);
    if (persist) {
      storeMonitoringEnabled(true);
    }
    setMonitorStatus('starting');
    setStatusMessage('Starting monitor...');

    try {
      const response = await fetch(`${MONITOR_CONTROL_ENDPOINT}/start`, { method: 'POST' });
      const data = await response.json();
      const nextStatus = data.status || null;
      setControlStatus(nextStatus);

      if (!response.ok || data?.success === false) {
        throw new Error(data?.message || 'Monitor failed to start');
      }

      if (!updateStatusFromControl(nextStatus)) {
        startStatusPolling();
      }
    } catch (error) {
      clearMonitorPoll();
      setMonitorStatus('failed');
      setStatusMessage(error?.message || 'Monitor failed to start');
    }
  }

  async function stopMonitor() {
    clearMonitorPoll();
    setMonitorStatus('stopping');
    setStatusMessage('Stopping monitor...');
    storeMonitoringEnabled(false);

    try {
      const response = await fetch(`${MONITOR_CONTROL_ENDPOINT}/stop`, { method: 'POST' });
      const data = await response.json();
      setControlStatus(data.status || null);
    } catch {
      setControlStatus(null);
    } finally {
      setMemoryMonitoringEnabled(false);
      setMonitorStatus('idle');
      setStatusMessage('');
    }
  }

  useEffect(() => {
    let ignore = false;

    async function initializeMonitorControl() {
      try {
        const nextStatus = await fetchControlStatus();
        if (ignore) {
          return;
        }
        if (nextStatus?.force_disabled) {
          updateStatusFromControl(nextStatus);
          return;
        }
        if (readStoredMonitoringEnabled()) {
          await startMonitor({ persist: false });
        } else {
          setMonitorStatus('idle');
        }
      } catch (error) {
        if (!ignore && readStoredMonitoringEnabled()) {
          setMemoryMonitoringEnabled(true);
          setMonitorStatus('failed');
          setStatusMessage(error?.message || 'Monitor failed to start');
        }
      }
    }

    initializeMonitorControl();
    return () => {
      ignore = true;
      clearMonitorPoll();
    };
  }, []);

  function handleMonitoringToggle(nextValue) {
    if (controlStatus?.force_disabled) {
      return;
    }
    if (nextValue) {
      startMonitor();
    } else {
      stopMonitor();
    }
  }

  async function openMonitor() {
    const opened = await window.desktop?.openExternal?.(MONITOR_UI_URL);
    if (!opened) {
      window.open(MONITOR_UI_URL, '_blank', 'noopener,noreferrer');
    }
  }

  const isRunning = Boolean(
    memoryMonitoringEnabled &&
      !controlStatus?.force_disabled &&
      controlStatus?.collector_running &&
      controlStatus?.frontend_running &&
      monitorStatus === 'running',
  );
  const isBusy = monitorStatus === 'starting' || monitorStatus === 'stopping';
  const showStatus = memoryMonitoringEnabled || controlStatus?.force_disabled || isBusy;
  const statusLabel = controlStatus?.force_disabled
    ? 'Memory monitoring disabled'
    : monitorStatus === 'running'
      ? 'Monitor running'
      : monitorStatus === 'starting'
        ? 'Starting monitor...'
        : monitorStatus === 'stopping'
          ? 'Stopping monitor...'
          : monitorStatus === 'failed'
            ? 'Monitor failed to start'
            : '';
  const statusColor = monitorStatus === 'running' ? 'text-[#22C55E]' : 'text-[#EF4444]';
  const dotColor = monitorStatus === 'running' ? 'bg-[#22C55E]' : 'bg-[#EF4444]';

  return (
    <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
      <div className="flex flex-col gap-5">
        <div>
          <p className="text-[15px] font-medium text-[#E8E8E8]">Memory Monitoring</p>
          <p className="mt-1 max-w-[560px] text-[13px] leading-[1.5] text-[#666666]">
            Enable live inspection of working memory events, compression output, prompt context,
            facts, and metrics.
          </p>
        </div>

        <ToggleRow
          checked={memoryMonitoringEnabled}
          disabled={Boolean(controlStatus?.force_disabled) || isBusy}
          label="Enable memory monitoring"
          description="Starts monitor services and enables live memory event inspection"
          onChange={handleMonitoringToggle}
        />

        {showStatus && statusLabel ? (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span
              className={`flex items-center gap-2 text-[13px] ${statusColor}`}
            >
              <span className={`h-2 w-2 rounded-full ${dotColor}`} />
              {statusLabel}
            </span>
            {statusMessage ? (
              <span className="text-[13px] text-[#666666]">
                {statusMessage}
              </span>
            ) : null}
          </div>
        ) : null}

        {memoryMonitoringEnabled && !controlStatus?.force_disabled ? (
          <button
            type="button"
            onClick={openMonitor}
            disabled={!isRunning}
            title={!isRunning ? 'Monitor is not running' : 'Open Memory Monitor'}
            className="h-9 w-fit rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] px-4 text-[13px] text-[#E8E8E8] transition duration-150 hover:border-[#6366F1] hover:text-[#C7D2FE] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Open Memory Monitor
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default function MemorySettingsCard({
  isOnline = true,
  onBackendConnectionLost,
  onMemoryConfigSaved,
  configFetchGuardRef,
  statsFetchGuardRef,
}) {
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [useSeparate, setUseSeparate] = useState(false);
  const [memoryProvider, setMemoryProvider] = useState('');
  const [memoryApiKey, setMemoryApiKey] = useState('');
  const [memoryModel, setMemoryModel] = useState('');
  const [memoryApiKeyExists, setMemoryApiKeyExists] = useState(false);
  const [memoryApiKeyLocked, setMemoryApiKeyLocked] = useState(true);
  const [memoryHasChanged, setMemoryHasChanged] = useState(false);
  const [editedFields, setEditedFields] = useState({
    memoryEnabled: false,
    useSeparate: false,
    provider: false,
    model: false,
    apiKey: false,
  });
  const memoryInitialValues = useRef({
    memoryEnabled: true,
    useSeparate: false,
    provider: '',
    model: '',
    apiKeyExists: false,
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const [stats, setStats] = useState({
    active_sessions: 0,
    total_compressions: 0,
    total_messages_compressed: 0,
    estimated_tokens_saved: 0,
  });
  const [statsStatus, setStatsStatus] = useState(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const localConfigFetchedRef = useRef(false);
  const localStatsFetchedRef = useRef(false);
  const configFetchedRef = configFetchGuardRef || localConfigFetchedRef;
  const statsFetchedRef = statsFetchGuardRef || localStatsFetchedRef;

  const selectedProvider = useMemo(
    () => findProvider(memoryProvider) || findProvider('openai'),
    [memoryProvider],
  );
  const providerFieldsDisabled = !useSeparate;
  const apiInputValue = memoryApiKeyLocked &&
    memoryApiKeyExists &&
    !editedFields.apiKey
      ? '................'
      : memoryApiKey;
  const canTestConnection =
    useSeparate &&
    Boolean(memoryProvider) &&
    Boolean(memoryModel.trim()) &&
    (memoryApiKeyExists || editedFields.apiKey) &&
    !isTesting &&
    !isLoadingConfig;

  useEffect(() => {
    setMemoryHasChanged(Object.values(editedFields).some(Boolean));
  }, [editedFields]);

  async function loadStats({ force = false } = {}) {
    if (!force && statsFetchedRef.current) {
      return;
    }
    statsFetchedRef.current = true;
    setIsLoadingStats(true);
    setStatsStatus(null);
    try {
      const response = await fetch(MEMORY_STATS_ENDPOINT);
      const data = await response.json();
      if (!response.ok || data?.success === false) {
        throw new Error(data?.message || 'Unable to load memory stats.');
      }
      setStats(data);
    } catch (error) {
      setStatsStatus({
        type: 'error',
        message: error?.message || 'Unable to load memory stats.',
      });
    } finally {
      setIsLoadingStats(false);
    }
  }

  useEffect(() => {
    if (configFetchedRef.current) {
      setIsLoadingConfig(false);
      return undefined;
    }
    configFetchedRef.current = true;
    let ignore = false;

    async function loadConfig() {
      setIsLoadingConfig(true);
      try {
        const response = await fetch(CONFIG_ENDPOINT);
        const data = await response.json();
        if (!response.ok || data?.success === false) {
          throw new Error(data?.message || 'Unable to load memory configuration.');
        }

        if (!ignore) {
          const nextMemoryEnabled = data.memory_enabled !== false;
          const nextUseSeparate = Boolean(data.use_separate_memory_provider);
          const nextProvider = data.memory_provider || '';
          const nextModel = data.memory_model || '';
          const nextHasApiKey = Boolean(data.has_memory_api_key);

          memoryInitialValues.current = {
            memoryEnabled: nextMemoryEnabled,
            useSeparate: nextUseSeparate,
            provider: nextProvider,
            model: nextModel,
            apiKeyExists: nextHasApiKey,
          };
          setMemoryEnabled(nextMemoryEnabled);
          setUseSeparate(nextUseSeparate);
          setMemoryProvider(nextProvider);
          setMemoryModel(nextModel);
          setMemoryApiKeyExists(nextHasApiKey);
          setMemoryApiKey('');
          setMemoryApiKeyLocked(true);
          setEditedFields({
            memoryEnabled: false,
            useSeparate: false,
            provider: false,
            model: false,
            apiKey: false,
          });
        }
      } catch (error) {
        if (!ignore) {
          setSaveStatus({
            type: 'error',
            message: error?.message || 'Unable to load memory configuration.',
          });
        }
      } finally {
        if (!ignore) {
          setIsLoadingConfig(false);
        }
      }
    }

    loadConfig();
    loadStats();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (testStatus?.type !== 'success') {
      return undefined;
    }

    const timeout = window.setTimeout(() => setTestStatus(null), 3000);
    return () => window.clearTimeout(timeout);
  }, [testStatus]);

  useEffect(() => {
    if (saveStatus?.type !== 'success') {
      return undefined;
    }

    const timeout = window.setTimeout(() => setSaveStatus(null), 2000);
    return () => window.clearTimeout(timeout);
  }, [saveStatus]);

  function clearStatuses() {
    setTestStatus(null);
    setSaveStatus(null);
  }

  function createVerifyPayload() {
    return {
      provider: memoryProvider,
      api_key: editedFields.apiKey ? memoryApiKey : '',
      model_name: memoryModel.trim(),
    };
  }

  function createSavePayload() {
    const payload = {
      memory_enabled: memoryEnabled,
      use_separate_provider: useSeparate,
      provider: useSeparate ? memoryProvider : null,
      model_name: useSeparate ? memoryModel.trim() : null,
    };

    if (useSeparate && editedFields.apiKey) {
      payload.api_key = memoryApiKey.trim();
    }

    return payload;
  }

  async function testConnection() {
    if (!canTestConnection) {
      return;
    }

    setIsTesting(true);
    setTestStatus(null);
    try {
      const response = await fetch(VERIFY_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createVerifyPayload()),
      });
      const data = await response.json();

      if (!response.ok || !data?.success) {
        throw new Error(data?.message || 'Connection failed.');
      }

      setTestStatus({ type: 'success', message: 'Connected successfully' });
    } catch (error) {
      if (isOnline && isNetworkError(error)) {
        onBackendConnectionLost?.();
      }
      setTestStatus({
        type: 'error',
        message: error?.message || 'Connection failed.',
      });
    } finally {
      setIsTesting(false);
    }
  }

  async function saveMemoryConfig() {
    if (isSaving) {
      return;
    }

    if (!isOnline) {
      setSaveStatus({
        type: 'error',
        message: 'No internet connection. Changes not saved.',
      });
      return;
    }

    setIsSaving(true);
    setSaveStatus(null);
    try {
      const payload = createSavePayload();
      const response = await fetch(MEMORY_CONFIG_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (!response.ok || !data?.success) {
        throw new Error(data?.message || 'Unable to save memory settings.');
      }

      const nextHasApiKey = useSeparate && (editedFields.apiKey ? Boolean(memoryApiKey.trim()) : memoryApiKeyExists);
      memoryInitialValues.current = {
        memoryEnabled,
        useSeparate,
        provider: memoryProvider,
        model: memoryModel.trim(),
        apiKeyExists: nextHasApiKey,
      };
      setMemoryApiKeyExists(nextHasApiKey);
      setMemoryApiKey('');
      setMemoryApiKeyLocked(true);
      setEditedFields({
        memoryEnabled: false,
        useSeparate: false,
        provider: false,
        model: false,
        apiKey: false,
      });
      setSaveStatus({ type: 'success', message: 'Saved' });
      onMemoryConfigSaved?.({
        memoryEnabled,
        useSeparateMemoryProvider: useSeparate,
        memoryProvider: useSeparate ? memoryProvider : '',
        memoryModel: useSeparate ? memoryModel.trim() : '',
        hasMemoryApiKey: useSeparate ? nextHasApiKey : false,
        memoryApiKey: '',
      });
    } catch (error) {
      if (isOnline && isNetworkError(error)) {
        onBackendConnectionLost?.();
      }
      setSaveStatus({
        type: 'error',
        message: error?.message || 'Unable to save memory settings.',
      });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="max-w-[860px]">
      <h1 className="mb-8 text-[24px] font-semibold text-[#E8E8E8]">Memory</h1>

      <section>
        <SectionTitle>Working Memory</SectionTitle>
        <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
          <ToggleRow
            checked={memoryEnabled}
            label="Enable working memory"
            description="Compresses older messages to maintain context efficiently"
            onChange={(nextValue) => {
              setMemoryEnabled(nextValue);
              setEditedFields((current) => ({ ...current, memoryEnabled: true }));
              clearStatuses();
            }}
          />

          <div className="mt-5 flex flex-col gap-2 rounded-[8px] border border-[#1F1F1F] bg-[#0D0D0D] px-4 py-[14px]">
            <InfoStatLine>Raw message limit: 8 messages</InfoStatLine>
            <InfoStatLine>Compression trigger: every 8 messages</InfoStatLine>
            <InfoStatLine>Current active sessions: {stats.active_sessions}</InfoStatLine>
          </div>
        </div>
      </section>

      <section className="mt-10">
        <SectionTitle>Memory Provider</SectionTitle>
        <p className="mb-5 text-[13px] text-[#666666]">
          By default working memory compression uses your main chat provider. Configure a separate
          provider below for memory operations to reduce main chat costs.
        </p>

        <div
          className={`rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6 transition-opacity duration-200 ${
            isLoadingConfig ? 'opacity-50' : 'opacity-100'
          }`}
        >
          <div className="flex flex-col gap-5">
            <ToggleRow
              checked={useSeparate}
              label="Use separate provider for memory"
              description="Use a dedicated provider for memory compression instead of the main chat provider"
              onChange={(nextValue) => {
                setUseSeparate(nextValue);
                setEditedFields((current) => ({ ...current, useSeparate: true }));
                clearStatuses();
              }}
            />

            {useSeparate ? (
            <div className="flex flex-col gap-5 transition-opacity duration-200">
            <div>
              <FieldLabel>Provider</FieldLabel>
              <ProviderSelect
                value={memoryProvider}
                disabled={providerFieldsDisabled}
                onChange={(nextProvider) => {
                  setMemoryProvider(nextProvider);
                  setEditedFields((current) => ({ ...current, provider: true }));
                  clearStatuses();
                }}
              />
            </div>

            <div>
              <FieldLabel>API Key</FieldLabel>
              <div className="flex items-center gap-2">
                <div className="relative min-w-0 flex-1">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiInputValue}
                    readOnly={memoryApiKeyLocked}
                    disabled={providerFieldsDisabled}
                    onChange={(event) => {
                      setMemoryApiKey(event.target.value);
                      setEditedFields((current) => ({ ...current, apiKey: true }));
                      clearStatuses();
                    }}
                    placeholder="Enter memory provider API key"
                    autoComplete="off"
                    className={`h-11 w-full rounded-[8px] px-3 pr-10 text-sm outline-none transition duration-150 placeholder:text-[#555555] disabled:cursor-not-allowed ${
                      memoryApiKeyLocked
                        ? 'border border-[#1F1F1F] bg-[#0D0D0D] text-[#666666]'
                        : 'border border-[#6366F1] bg-[#1A1A1A] text-[#E8E8E8]'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey((current) => !current)}
                    className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-[6px] text-[#666666] transition duration-150 hover:bg-[#242424] hover:text-[#E8E8E8]"
                    aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
                  >
                    <FieldIcon name={showApiKey ? 'eyeOff' : 'eye'} />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setMemoryApiKeyLocked(false);
                    setMemoryApiKey('');
                    setEditedFields((current) => ({ ...current, apiKey: true }));
                    clearStatuses();
                  }}
                  disabled={providerFieldsDisabled}
                  className="grid h-9 w-9 shrink-0 place-items-center rounded-[8px] border border-[#2A2A2A] text-[#888888] transition duration-150 hover:border-[#6366F1] hover:text-[#6366F1]"
                  aria-label="Edit memory API key"
                  title="Edit memory API key"
                >
                  <FieldIcon name="pencil" />
                </button>
              </div>
            </div>

            <div>
              <FieldLabel>Model name</FieldLabel>
              <input
                type="text"
                value={memoryModel}
                disabled={providerFieldsDisabled}
                onChange={(event) => {
                  setMemoryModel(event.target.value);
                  setEditedFields((current) => ({ ...current, model: true }));
                  clearStatuses();
                }}
                placeholder={selectedProvider?.placeholder || 'gpt-4o-mini'}
                className="h-11 w-full rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] px-3 text-sm text-[#E8E8E8] outline-none transition duration-150 placeholder:text-[#555555] hover:border-[#3A3A3A] focus:border-[#6366F1] disabled:cursor-not-allowed"
              />
              <p className="mt-2 text-[12px] text-[#555555]">
                Use a fast cheap model like gpt-4o-mini or gemini-1.5-flash for memory
                compression to minimize costs.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={testConnection}
                disabled={!canTestConnection}
                className="flex h-9 items-center gap-2 rounded-[8px] border border-[#2A2A2A] bg-transparent px-4 text-[13px] text-[#E8E8E8] transition duration-150 hover:border-[#6366F1] hover:text-[#6366F1] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isTesting ? <Spinner /> : null}
                Test Connection
              </button>

              {testStatus ? (
                <div
                  className={`flex items-center gap-1.5 text-[13px] ${
                    testStatus.type === 'success' ? 'text-[#22C55E]' : 'text-[#EF4444]'
                  }`}
                >
                  <FieldIcon name={testStatus.type === 'success' ? 'check' : 'x'} />
                  <span>{testStatus.message}</span>
                </div>
              ) : null}
            </div>
            </div>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={saveMemoryConfig}
            disabled={isSaving || isLoadingConfig}
            className="h-9 rounded-[8px] bg-[#6366F1] px-5 text-[14px] text-white transition duration-150 hover:bg-[#4F46E5] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isSaving ? 'Saving' : 'Save changes'}
          </button>
          {saveStatus ? (
            <span
              className={`text-[13px] ${
                saveStatus.type === 'success' ? 'text-[#22C55E]' : 'text-[#EF4444]'
              }`}
            >
              {saveStatus.message}
            </span>
          ) : null}
        </div>
      </section>

      <section className="mt-10">
        <SectionTitle>Memory Monitoring</SectionTitle>
        <MemoryMonitorCard />
      </section>

      <section className="mt-10">
        <SectionTitle>Memory Stats</SectionTitle>
        <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
          <div className="mb-5 flex items-center justify-between gap-4">
            <p className="text-[14px] font-medium text-[#E8E8E8]">This session</p>
            <button
              type="button"
              onClick={() => loadStats({ force: true })}
              disabled={isLoadingStats}
              className="flex h-8 items-center gap-2 rounded-[8px] border border-[#2A2A2A] px-3 text-[13px] text-[#E8E8E8] transition duration-150 hover:border-[#6366F1] hover:text-[#6366F1] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isLoadingStats ? <Spinner /> : null}
              Refresh
            </button>
          </div>
          <div className="grid gap-3">
            <StatLine label="Total compressions this session:" value={stats.total_compressions} />
            <StatLine label="Messages compressed:" value={stats.total_messages_compressed} />
            <StatLine label="Estimated tokens saved:" value={stats.estimated_tokens_saved} />
            <StatLine label="Active sessions in memory:" value={stats.active_sessions} />
          </div>
          {statsStatus ? (
            <p className="mt-4 text-[13px] text-[#EF4444]">{statsStatus.message}</p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
